from collections import namedtuple
import pandas as pd
from sqlalchemy import text
from flask import g, request
from graphene import (
    Boolean,
    Enum,
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
from graphene.types import Date, DateTime
from graphene_file_upload.scalars import Upload
from graphql import GraphQLError
from app import db
from app.auth import encode
from app import loaders


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


# proposal


class Proposal(ObjectType):
    proposal_code = NonNull(
        String, description="The proposal code, such as 2018-2-SCI-042."
    )

    title = NonNull(String, description="The proposal title.")

    blocks = List(NonNull(lambda: Block), description="The blocks in the proposal.")

    observations = List(
        NonNull(lambda: ProposalObservation),
        description="The observations for the proposal",
    )

    def resolve_proposal_code(self, info):
        return self.proposal_code

    def resolve_title(self, info):
        return self.title

    def resolve_blocks(self, info):
        return loaders["block_loader"].load_many(self.blocks)

    def resolve_observations(self, info):
        return loaders["observation_loader"].load_many(self.observations)


# block


class BlockStatus(Enum):
    ACTIVE = "active"

    COMPLETED = "completed"

    DELETED = "deleted"

    EXPIRED = "expired"

    ON_HOLD = "on hold"

    SUPERSEDED = "superseded"

    @property
    def description(self):
        if self == BlockStatus.ACTIVE:
            return "The block is active and can be observed."
        elif self == BlockStatus.COMPLETED:
            return "All observations for the block have been completed."
        elif self == BlockStatus.DELETED:
            return "The block has been deleted."
        elif self == BlockStatus.EXPIRED:
            return "The block is expired and will not be observed any longer."
        elif self == BlockStatus.ON_HOLD:
            return "The block has been put on hold and will not be observed."
        elif self == BlockStatus.SUPERSEDED:
            return "There exists a newer version of the block."

        return "This is an undocumented block status."


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

    @property
    def description(self):
        return "THe smallest schedulable unit in a proposal."

    def resolve_id(self, info):
        return self.id

    def resolve_proposal(self, info):
        return loaders["proposal_loader"].load(self.proposal)

    def resolve_status(self, info):
        status = self.status.lower()
        if status == "active":
            return BlockStatus.ACTIVE
        elif status == "completed":
            return BlockStatus.COMPLETED
        elif status == "deleted":
            return BlockStatus.DELETED
        elif status == "expired":
            return BlockStatus.EXPIRED
        elif status == "on hold":
            return BlockStatus.ON_HOLD
        elif status == "superseded":
            return BlockStatus.SUPERSEDED

        raise GraphQLError("Unknown block status: {status}".format(status=self.status))


# observation


class ObservationStatus(Enum):
    ACCEPTED = "accepted"

    REJECTED = "rejected"

    QUEUED = "in queue"

    DELETED = "deleted"

    @property
    def description(self):
        if self == ObservationStatus.ACCEPTED:
            return "The observation has been accepted."
        elif self == ObservationStatus.REJECTED:
            return "The observation has been rejected."
        elif self == ObservationStatus.QUEUED:
            return "The observation has been put in the queue."
        elif self == ObservationStatus.DELETED:
            return "The observation has been deleted."

        return "This is an undocumented observation status."


class Observation(Interface):
    night = NonNull(Date, description="The night when the observation was taken.")

    start = NonNull(
        DateTime, description="The datetime when the observation was started."
    )

    status = NonNull(
        lambda: ObservationStatus, description="The status of the observation."
    )

    rejection_reason = String(
        description="Reason why the observation has been rejected."
    )

    def resolve_status(self, info):
        status = self.status.lower()
        if status == "accepted":
            return ObservationStatus.ACCEPTED
        elif status == "rejected":
            return ObservationStatus.REJECTED
        elif status == "in queue":
            return ObservationStatus.QUEUED
        elif status == "deleted":
            return ObservationStatus.DELETED

        raise GraphQLError(
            "Unknown observation status: {status}".format(status=self.status)
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
