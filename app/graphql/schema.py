from collections import namedtuple
import re
import pandas as pd
from sqlalchemy import text
from flask import g, request
from graphene import (
    Boolean,
    Field,
    ID,
    Int,
    Interface,
    List,
    Mutation,
    NonNull,
    ObjectType,
    String,
    Float,
)
from graphene.types import Date, DateTime, Scalar
from graphene_file_upload.scalars import Upload
from graphql import GraphQLError
from graphql.language import ast
from app import db
from app.auth import encode
from app import loaders
from app.util import (
    BlockStatus,
    ObservationStatus,
    ObservingWindowType,
    PartnerCode,
    ProposalInactiveReason,
    ProposalStatus,
    ProposalType,
    _SemesterContent,
)


# semester

class Semester(Scalar):
    """A proposal semester, such as \"2018-2\" or \"2019-1\"."""

    SEMESTER_REGEX = re.compile(r"^\d{4}-[12]$")

    @staticmethod
    def serialize(s):
        assert isinstance(
            s, _SemesterContent
        ), "Received incompatible semester: {semester}".format(semester=repr(s))
        return "{year}-{semester}".format(year=s.year, semester=s.semester)

    @classmethod
    def parse_literal(cls, node):
        if isinstance(node, ast.StringValue):
            return cls.parse_value(node.value)
        raise GraphQLError(
            'A semester must be a string of the form "yyyy-s" (e.g., "2018-2"'
        )

    @classmethod
    def parse_value(cls, value):
        # sanity check: the value is of the form yyyy-s
        if not cls.SEMESTER_REGEX.match(value):
            raise GraphQLError(
                'A semester must be of the form "yyyy-s" (e.g., "2018-2")'
            )

        year, semester = value.split("-")
        return _SemesterContent(year=year, semester=semester)


# root query

_TokenContent = namedtuple("TokenContent", ["token"])

_PartnerTimeShareContent = namedtuple(
    "PartnerTimeShareContent", ["partner_code", "share_percent", "semester"]
)

_PartnerStatObservationContent = namedtuple(
    "PartnerStatObservationContent", ["observation_time", "status"]
)

_TimeBreakdownContent = namedtuple(
    "TimeBreakdownContent", ["science", "engineering", "lost_to_weather", "lost_to_problems", "idle"]
)


def _check_auth_token():
    if "Authorization" not in request.headers or not g.user:
        raise GraphQLError("A valid authentication token is required.")


def find_proposals_with_time_allocation(params, filters):
    """
    All of the proposal that are allocated time.

    Parameters
    ----------
    params : Dict
        The dictionary of SQL parameter
    filters : Iterable[str]
        The filters for the SQL.

    Returns
    -------
    Proposal Code : DataFrame
        Whether the user is an investigator on the proposal.

    """
    allocated_time_sql = """
SELECT DISTINCT Proposal_Code
FROM MultiPartner
    JOIN PriorityAlloc USING (MultiPartner_Id)
    JOIN Semester USING (Semester_Id)
    JOIN Partner USING (Partner_Id)
    JOIN ProposalCode USING (ProposalCode_Id)
{where}
    """.format(where=" WHERE " + "(" + ") AND (".join(filters) + ")" if len(filters) > 0 else "")
    results = pd.read_sql(allocated_time_sql, con=db.engine, params=params)
    return results


def find_proposals_with_time_requests(params, filters):
    """
    All of the proposal that are requesting time.

    Parameters
    ----------
    params : Dict
        The dictionary of SQL parameter
    filters : Iterable[str]
        The filters for the SQL.

    Returns
    -------
    Proposal Code : DataFrame
        Whether the user is an investigator on the proposal.

    """
    filters.append('Current = 1 AND Status NOT IN ("Deleted")')
    submitted_sql = """
SELECT DISTINCT Proposal_Code
FROM Proposal
    JOIN ProposalCode USING(ProposalCode_Id)
    JOIN ProposalGeneralInfo USING (ProposalCode_Id)
    JOIN ProposalStatus USING (ProposalStatus_Id)
    JOIN MultiPartner USING(ProposalCode_Id)
    JOIN Semester ON MultiPartner.Semester_Id=Semester.Semester_Id
    JOIN Partner ON (MultiPartner.Partner_Id = Partner.Partner_Id)
WHERE {where}
    """.format(where="(" + ") AND (".join(filters) + ")")
    results = pd.read_sql(submitted_sql, con=db.engine, params=params)

    return results


class Query(ObjectType):
    auth_token = Field(
        lambda: AuthToken,
        description="Request an authentication token.",
        username=NonNull(String, description="Username"),
        password=NonNull(String, description="Password"),
    )

    proposals = Field(
        lambda: List(Proposal),
        description="A list of SALT proposals.",
        partner_code=PartnerCode(
            description="The partner whose proposals are returned.",
            required=False,
        ),
        semester=Semester(
            description="The semester whose proposals are returned.",
            required=False,
        ),
    )

    proposal = Field(
        lambda: Proposal,
        description="A SALT proposal.",
        proposal_code=NonNull(String, description="The proposal code."),
    )

    partner_share_times = Field(
        lambda: List(PartnerTimeShare),
        description="Partner time shares.",
        partner_code=PartnerCode(
            description="The partner whose time shares are returned.",
            required=False,
        ),
        semester=Semester(
            description="The semester whose time shares are returned.",
            required=False,
        ),
    )

    partner_stat_observations = Field(
        lambda: List(PartnerStatObservation),
        description="A list of observation times, in seconds",
        semester=Semester(
            description="The semester whose observation times are returned.",
            required=True,
        ),
    )

    time_breakdown = Field(
        lambda: TimeBreakdown,
        description="The weather down time",
        semester=Semester(
            description="The semester whose time breakdown are returned.",
            required=True,
        ),
    )

    def resolve_auth_token(self, info, username, password):
        # query for the user with the given credentials
        sql = """SELECT PiptUser_Id
                        FROM PiptUser
                        WHERE Username=%(username)s AND Password=MD5(%(password)s)"""
        df = pd.read_sql(
            sql, con=db.engine, params=dict(username=username, password=password)
        )

        # check whether a user was found
        if len(df) == 0:
            raise GraphQLError("username or password wrong")

        # encode and return the user id
        token = encode({"user_id": df["PiptUser_Id"][0].item()})
        return _TokenContent(token=token)

    def resolve_proposals(self, info, partner_code=None, semester=None):
        # get the filter conditions
        params = dict()
        filters = []
        if partner_code:
            filters.append("Partner.Partner_Code=%(partner_code)s")
            params["partner_code"] = partner_code
        if semester:
            filters.append("(Semester.Year=%(year)s AND Semester.Semester=%(semester)s)")
            params["year"] = semester.year
            params["semester"] = semester.semester

        df_proposals_allocated_time = find_proposals_with_time_allocation(params, filters)
        df_proposals_submitted = find_proposals_with_time_requests(params, filters)
        df = pd.concat([df_proposals_allocated_time, df_proposals_submitted], ignore_index=True).drop_duplicates()

        all_proposal_codes = df["Proposal_Code"].tolist()

        # only retain proposals the user actually may view
        proposal_codes = [
            proposal_code
            for proposal_code in all_proposal_codes
            if g.user.may_view_proposal(proposal_code)
        ]

        return loaders["proposal_loader"].load_many(proposal_codes)

    def resolve_proposal(self, info, proposal_code):
        # sanity check: may the user view the proposal?
        _check_auth_token()
        if not g.user.may_view_proposal(proposal_code=proposal_code):
            raise GraphQLError(
                "You are not allowed to view the proposal {proposal_code}".format(
                    proposal_code=proposal_code
                )
            )

        return loaders["proposal_loader"].load(proposal_code)

    def resolve_partner_share_times(self, info, partner_code=None, semester=None):
        # get the filter conditions
        params = dict()
        filters = []
        if partner_code:
            filters.append("partner.Partner_Code=%(partner_code)s")
            params["partner_code"] = partner_code

        if semester:
            filters.append("(s.Year=%(year)s AND s.Semester=%(semester)s)")
            params["year"] = semester.year
            params["semester"] = semester.semester

        if len(filters):
            # query for the partner time shares according to the semester or partner code
            sql = """SELECT Partner_Code, SharePercent, Year, Semester
           FROM PartnerShareTimeDist AS pst
           JOIN Semester AS s ON pst.Semester_Id = s.Semester_Id
           JOIN Partner AS partner ON pst.Partner_Id = partner.Partner_Id
           WHERE {where}
           """.format(
                where=" AND ".join(filters)
            )
        else:
            sql = """SELECT Partner_Code, SharePercent, Year, Semester
           FROM PartnerShareTimeDist
           JOIN Semester using(Semester_Id)
           JOIN Partner using(Partner_Id)
           """

        df = pd.read_sql(sql, con=db.engine, params=params)

        partner_time_shares = []
        for _, row in df.iterrows():
            partner_time_shares.append(_PartnerTimeShareContent(
                semester=_SemesterContent(year=row["Year"], semester=row["Semester"]),
                partner_code=row["Partner_Code"],
                share_percent=row["SharePercent"],
            ))

        return partner_time_shares

    def resolve_partner_stat_observations(self, info, semester):
        # get the filter conditions
        params = dict()
        filters = ["(s.Year=%(year)s AND s.Semester=%(semester)s)"]
        params["year"] = semester.year
        params["semester"] = semester.semester

        # query for the observation times
        sql = """SELECT ObsTime, BlockVisitStatus FROM Proposal AS p
        JOIN Block AS b ON b.Proposal_Id = p.Proposal_Id
        JOIN BlockVisit AS bv ON bv.Block_Id = b.Block_Id
        JOIN Semester AS s ON s.Semester_Id = p.Semester_Id
        JOIN BlockVisitStatus AS bvs ON bvs.BlockVisitStatus_Id = bv.BlockVisitStatus_Id
        WHERE {where}
        """.format(
            where=" AND ".join(filters)
        )

        df = pd.read_sql(sql, con=db.engine, params=params)

        partner_stat_observations = []
        for _, row in df.iterrows():
            partner_stat_observations.append(_PartnerStatObservationContent(
                observation_time=row["ObsTime"],
                status=row["BlockVisitStatus"]
            ))

        return partner_stat_observations

    def resolve_time_breakdown(self, info, semester):
        # get the filter conditions
        params = dict()
        filters = ["(s.Year=%(year)s AND s.Semester=%(semester)s)"]
        params["year"] = semester.year
        params["semester"] = semester.semester

        # query for the time breakdown
        sql = """SELECT SUM(ScienceTime) AS ScienceTime, SUM(EngineeringTime) AS EngineeringTime, 
        SUM(TimeLostToWeather) AS TimeLostToWeather, SUM(TimeLostToProblems) AS TimeLostToProblems, 
        SUM(IdleTime) AS IdleTime   
        FROM NightInfo AS ni
        JOIN Semester AS s ON (ni.Date >= s.StartSemester AND ni.Date <= s.EndSemester)
        WHERE {where}
        """.format(
            where=" AND ".join(filters)
        )

        df = pd.read_sql(sql, con=db.engine, params=params)

        time_breakdown = _TimeBreakdownContent(
            science=0 if pd.isnull(df["ScienceTime"][0]) else df["ScienceTime"][0],
            engineering=0 if pd.isnull(df["EngineeringTime"][0]) else df["EngineeringTime"][0],
            lost_to_weather=0 if pd.isnull(df["TimeLostToWeather"][0]) else df["TimeLostToWeather"][0],
            lost_to_problems=0 if pd.isnull(df["TimeLostToProblems"][0]) else df["TimeLostToProblems"][0],
            idle=0 if pd.isnull(df["IdleTime"][0]) else df["IdleTime"][0],
        )

        return time_breakdown


# authentication token

class AuthToken(ObjectType):
    @property
    def description(self):
        return """A JWT authentication token. If an API query requires authentication, 
include an Authorization HTTP header with your request. The header value must be of the 
form "Token {token}", where {token} is the JWT token."""  # noqa

    token = String(description="Authentication token")

    def resolve_token(self, info):
        return self.token


# person

class Person(ObjectType):
    given_name = NonNull(String, description="The given name(s).")

    family_name = NonNull(String, description="The family name.")

    email = String(description="The email address.")


# proposal

class Proposal(ObjectType):
    proposal_code = NonNull(
        String, description="The proposal code, such as 2018-2-SCI-042."
    )

    title = NonNull(String, description="The proposal title.")

    proposal_type = NonNull(lambda: ProposalType, description="The proposal type.")

    status = NonNull(lambda: ProposalStatus, description="The proposal status.")

    status_comment = String(description="A comment explaining the proposal status.")

    inactive_reason = ProposalInactiveReason(
        description="The reason why the proposal is inactive."
    )

    completion_comments = List(
        lambda: CompletionComment,
        description="The comments regarding proposal completion.",
    )

    principal_investigator = NonNull(
        lambda: Person, description="The Principal Investigator."
    )

    principal_contact = NonNull(lambda: Person, description="The Principal Contact.")

    liaison_astronomer = Field(lambda: Person, description="The Principal Contact.")

    blocks = List(NonNull(lambda: Block), description="The blocks in the proposal.")

    observations = List(
        NonNull(lambda: ProposalObservation),
        description="The observations for the proposal",
    )

    time_allocations = List(
        NonNull(lambda: TimeAllocation), description="The time allocations."
    )

    def resolve_proposal_code(self, info):
        return self.proposal_code

    def resolve_title(self, info):
        return self.title

    def resolve_principal_investigator(self, info):
        return loaders["investigator_loader"].load(self.principal_investigator)

    def resolve_principal_contact(self, info):
        return loaders["investigator_loader"].load(self.principal_contact)

    def resolve_liaison_astronomer(self, info):
        if self.liaison_astronomer is None:
            return None
        return loaders["investigator_loader"].load(self.liaison_astronomer)

    def resolve_blocks(self, info):
        return loaders["block_loader"].load_many(self.blocks)

    def resolve_observations(self, info):
        return loaders["observation_loader"].load_many(self.observations)


# block

class Block(ObjectType):
    id = NonNull(ID, description="The unique block id.")

    block_code = NonNull(String, description="The block code.")

    proposal = NonNull(
        lambda: Proposal, description="The proposal to which this block belongs."
    )

    name = NonNull(String, description="The block name.")

    status = NonNull(
        lambda: BlockStatus, description='The block status, such "active".'
    )

    status_reason = String(
        description="The reason why the block has the status it has."
    )

    semester = NonNull(
        lambda: Semester, description="The semester to which this block belongs."
    )

    length = NonNull(Int, description="The length of the block, per visit, in seconds.")

    priority = NonNull(Int, description="The priority of the block.")

    visits = List(
        NonNull(lambda: BlockObservation), description="The visits of the block."
    )

    observing_windows = Field(
        lambda: BlockObservingWindow,
        description="The block observing windows.",
        window_type=NonNull(
            lambda: ObservingWindowType, description='The observation window type such as "strict".'
        )
    )

    @property
    def description(self):
        return "THe smallest schedulable unit in a proposal."

    def resolve_id(self, info):
        return self.id

    def resolve_proposal(self, info):
        return loaders["proposal_loader"].load(self.proposal)

    def resolve_visits(self, info):
        return loaders["observation_loader"].load_many(self.visits)

    def resolve_observing_windows(self, info, window_type):
        return loaders["observing_window_loader"].load((self.id, window_type))


# observation

class Observation(Interface):
    night = NonNull(Date, description="The night when the observation was taken.")

    start = DateTime(description="The datetime when the observation was started.")

    status = NonNull(
        lambda: ObservationStatus, description="The status of the observation."
    )

    rejection_reason = String(
        description="Reason why the observation has been rejected."
    )


class BlockObservation(ObjectType):
    class Meta:
        interfaces = (Observation,)

    @property
    def description(self):
        return "An observation of a block."


class ObservingWindow(ObjectType):
    visibility_start = NonNull(String, description="The start of the observing window.")

    visibility_end = NonNull(String, description="The end of the observing window.")

    duration = NonNull(Float, description="The observing window duration in seconds.")

    window_type = NonNull(
        lambda: ObservingWindowType, description="The observation window type such as \'strict\'."
    )


class BlockObservingWindow(ObjectType):
    past_windows = List(
        NonNull(lambda: ObservingWindow), description="Past observing windows."
    )

    tonights_windows = List(
        NonNull(lambda: ObservingWindow), description="Tonight\'s observing windows."
    )

    future_windows = List(
        NonNull(lambda: ObservingWindow),
        description="Future observing windows, excluding any observing windows for tonight."
    )


class ProposalObservation(ObjectType):
    class Meta:
        interfaces = (Observation,)

    @property
    def description(self):
        return "An observation of a proposal."

    block = NonNull(
        lambda: Block, description="The block for which the observation was taken."
    )

    def resolve_block(self, info):
        return loaders["block_loader"].load(self.block)


# time allocation


class TimeAllocation(ObjectType):
    priority = NonNull(Int, description="The priority.")

    semester = NonNull(
        lambda: Semester,
        description="The semester to which the time has been allocated.",
    )

    partner_code = NonNull(
        lambda: PartnerCode, description="The partner who has made the time allocation."
    )

    amount = NonNull(Int, description="The amount of allocated time, in seconds.")


# completion comment


class CompletionComment(ObjectType):
    semester = NonNull(
        lambda: Semester, description="The semester to which the comment refers."
    )

    comment = String(description="The comment regarding proposal completion.")


# partner time share


class PartnerTimeShare(ObjectType):
    partner_code = NonNull(String, description="The partner code.")

    share_percent = NonNull(Float, description="The time share, in percent.")

    semester = NonNull(
        lambda: Semester, description="The semester for the partner time share."
    )

    def resolve_partner_code(self, info):
        return self.partner_code

    def resolve_share_percent(self, info):
        return self.share_percent


# all observation for partner stat

class PartnerStatObservation(ObjectType):
    observation_time = NonNull(Float, description="Observation time, in seconds")
    status = NonNull(
        lambda: ObservationStatus, description="The status of the observation."
    )

    def resolve_observation(self, info):
        return self.observation_time


# time breakdown

class TimeBreakdown(ObjectType):
    science = NonNull(Float, description="The time used for science.")
    engineering = NonNull(Float, description="The time used for engineering.")
    lost_to_weather = NonNull(Float, description="The time lost due to weather.")
    lost_to_problems = NonNull(Float, description="The time lost due to problems.")
    idle = NonNull(Float, description="The time lost on doing nothing.")

    semester = NonNull(
        lambda: Semester, description="The semester for the partner time share."
    )

    def resolve_science(self, info):
        return self.science

    def resolve_engineering(self, info):
        return self.engineering

    def resolve_lost_to_weather(self, info):
        return self.lost_to_weather

    def resolve_lost_to_problems(self, info):
        return self.lost_to_problems

    def resolve_idle(self, info):
        return self.idle


# mutations

class PutBlockOnHold(Mutation):
    class Arguments:
        block_id = NonNull(Int, description="The unique block id.")

        reason = String(description="The reason for putting the block on hold.")

    ok = Boolean(description="Whether the block has been put on hold successfully.")

    def mutate(self, info, block_id, reason=None):
        # sanity check: is the user allowed to do this?
        _check_auth_token()
        if not g.user.may_edit_block(block_id=block_id):
            raise GraphQLError(
                "You are not allowed to modify the block with id {block_id}.".format(
                    block_id=block_id
                )
            )

        # get the block status
        sql = """
SELECT BlockStatus
       FROM Block AS b
       JOIN BlockStatus AS bs ON b.BlockStatus_Id = bs.BlockStatus_Id
       WHERE Block_Id=%(block_id)s
         """
        df = pd.read_sql(sql, con=db.engine, params=dict(block_id=block_id))

        # sanity check: does the block exist?
        if len(df) == 0:
            raise GraphQLError(
                "There exists no block with id {block_id}.".format(block_id=block_id)
            )

        # sanity check: is the block active?
        block_status = df["BlockStatus"][0]
        if block_status != "Active":
            raise GraphQLError("Only active blocks can be put on hold.")

        # update the block status
        sql = """
UPDATE Block SET BlockStatus_Id=
               (SELECT BlockStatus_Id FROM BlockStatus WHERE BlockStatus='On Hold'),
                 BlockStatusReason=:reason
       WHERE Block_Id=:block_id
        """
        db.engine.execute(text(sql), block_id=block_id, reason=reason)

        # success!
        ok = True

        return PutBlockOnHold(ok=ok)


class PutBlockOffHold(Mutation):
    class Arguments:
        block_id = NonNull(Int, description="The unique block id.")

        reason = String(description="The reason for putting the block off hold.")

    ok = Boolean(description="Whether the block has been put off hold successfully.")

    def mutate(self, info, block_id, reason=None):
        # sanity check: is the user allowed to do this?
        _check_auth_token()
        if not g.user.may_edit_block(block_id=block_id):
            raise GraphQLError(
                "You are not allowed to modify the block with id {block_id}.".format(
                    block_id=block_id
                )
            )

        # get the block status
        sql = """
SELECT BlockStatus
       FROM Block AS b
       JOIN BlockStatus AS bs ON b.BlockStatus_Id = bs.BlockStatus_Id
       WHERE Block_Id=%(block_id)s
        """
        df = pd.read_sql(sql, con=db.engine, params=dict(block_id=block_id))

        # sanity check: does the block exist?
        if len(df) == 0:
            raise GraphQLError(
                "There exists no block with id {block_id}.".format(block_id=block_id)
            )

        # sanity check: is the block on hold?
        block_status = df["BlockStatus"][0]
        if block_status != "On Hold":
            raise GraphQLError("Only blocks on hold can be put off hold.")

        # update the block status
        sql = """
UPDATE Block SET BlockStatus_Id=
               (SELECT BlockStatus_Id FROM BlockStatus WHERE BlockStatus='Active'),
                 BlockStatusReason=:reason
       WHERE Block_Id=:block_id
        """
        db.engine.execute(text(sql), block_id=block_id, reason=reason)

        # success!
        ok = True

        return PutBlockOnHold(ok=ok)


class SubmitProposal(Mutation):
    class Arguments:
        proposal_code = String(description="The proposal code for a resubmission.")

        zip = NonNull(Upload, description="A zip file with the proposal content.")

    proposal = NonNull(lambda: Proposal, description="The submitted proposal.")

    def mutate(self, info):
        raise NotImplementedError("Not implemented yet.")


class SubmitBlock(Mutation):
    class Arguments:
        proposal_code = NonNull(
            String, description="The proposal code for a resubmission."
        )

        block_code = String(description="The block code for a resubmission.")

        zip = NonNull(Upload, description="A zip file with the block content.")

    block = NonNull(lambda: Block, description="The submitted block.")

    def mutate(self, info):
        raise NotImplementedError("Not implemented yet.")


class Mutation(ObjectType):
    putBlockOnHold = PutBlockOnHold.Field(description="Put a block on hold.")

    putBlockOffHold = PutBlockOffHold.Field(description="Put a block off hold.")

    submitProposal = SubmitProposal.Field(description="Submit a proposal.")

    submitBlock = SubmitBlock.Field(description="Submit a block.")
