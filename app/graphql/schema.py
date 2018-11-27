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


def _check_auth_token():
    if "Authorization" not in request.headers or not g.user:
        raise GraphQLError("A valid authentication token is required.")


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
            description="The partner whose proposals should be returned.",
            required=False,
        ),
        semester=Semester(
            description="The semester whose proposals should be returned.",
            required=False,
        ),
    )

    proposal = Field(
        lambda: Proposal,
        description="A SALT proposal.",
        proposal_code=NonNull(String, description="The proposal code."),
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
        filters = ["p.Current=1"]
        if partner_code:
            filters.append("partner.Partner_Code=%(partner_code)s")
            params["partner_code"] = partner_code
        if semester:
            filters.append("(s.Year=%(year)s AND s.Semester=%(semester)s)")
            params["year"] = semester.year
            params["semester"] = semester.semester

        # get all proposals (irrespective of user permissions)
        sql = """
SELECT DISTINCT Proposal_Code
       FROM ProposalCode AS pc
       JOIN Proposal AS p ON pc.ProposalCode_Id = p.ProposalCode_Id
       JOIN Semester AS s ON p.Semester_Id = s.Semester_Id
       JOIN ProposalInvestigator AS pi ON pc.ProposalCode_Id = pi.ProposalCode_Id
       JOIN Investigator AS i ON pi.Investigator_Id = i.Investigator_Id
       JOIN Institute AS institute ON i.Institute_Id = institute.Institute_Id
       JOIN Partner AS partner ON institute.Partner_Id = partner.Partner_Id
       WHERE {where}
""".format(
            where=" AND ".join(filters)
        )
        df = pd.read_sql(sql, con=db.engine, params=params)

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

    @property
    def description(self):
        return "THe smallest schedulable unit in a proposal."

    def resolve_id(self, info):
        return self.id

    def resolve_proposal(self, info):
        return loaders["proposal_loader"].load(self.proposal)

    def resolve_visits(self, info):
        return loaders["observation_loader"].load_many(self.visits)


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
        lambda: PartnerCode, description="The partber who has made the time allocation."
    )

    amount = NonNull(Int, description="The amount of allocatedv time, in seconds.")


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
