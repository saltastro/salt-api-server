from collections import namedtuple
import pandas as pd
from promise import Promise
from promise.dataloader import DataLoader
from graphql import GraphQLError
from app import db
from app.util import _SemesterContent, BlockStatus

BlockContent = namedtuple(
    "BlockContent",
    [
        "id",
        "block_code",
        "proposal",
        "name",
        "status",
        "status_reason",
        "semester",
        "length",
        "priority",
        "visits",
        "observing_windows"
    ],
)


class BlockLoader(DataLoader):
    def __init__(self):
        DataLoader.__init__(self, cache=False)

    def batch_load_fn(self, block_ids):
        return Promise.resolve(self.get_blocks(block_ids))

    def get_blocks(self, block_ids):
        # block details
        sql = """
SELECT Block_Id, BlockCode, Proposal_Code, Block_Name, BlockStatus, BlockStatusReason,
       Year, Semester, ObsTime, Priority
       FROM Block AS b
       JOIN BlockCode AS bc ON b.BlockCode_Id = bc.BlockCode_Id
       JOIN BlockStatus AS bs ON b.BlockStatus_Id = bs.BlockStatus_Id
       JOIN ProposalCode ON b.ProposalCode_Id = ProposalCode.ProposalCode_Id
       JOIN Proposal AS p ON b.Proposal_Id = p.Proposal_Id
       JOIN Semester AS s ON p.Semester_Id = s.Semester_Id
       WHERE Block_Id IN %(block_ids)s
"""
        df_blocks = pd.read_sql(sql, con=db.engine, params=dict(block_ids=block_ids))

        # block visits
        sql = """
SELECT Block_Id, BlockVisit_Id
       FROM BlockVisit AS bv
       WHERE Block_Id IN %(block_ids)s
"""
        df_visits = pd.read_sql(sql, con=db.engine, params=dict(block_ids=block_ids))

        # collect details of observing windows and group them according to past, tonight's and remaining
        values = dict()
        for _, row in df_blocks.iterrows():
            # collect details of the block
            values[row["Block_Id"]] = dict(
                id=row["Block_Id"],
                block_code=row["BlockCode"],
                proposal=row["Proposal_Code"],
                name=row["Block_Name"],
                status=BlockStatus.get(row["BlockStatus"]),
                status_reason=row["BlockStatusReason"],
                semester=_SemesterContent(year=row["Year"], semester=row["Semester"]),
                length=row["ObsTime"],
                priority=row["Priority"],
                visits=set(),
                # The observing windows depend on the block id as well as the window type.
                # The latter is passed as argument when requesting observing windows.
                # We use the block id as the observing windows value so that
                # it can be picked up by the resolver function for observing windows later on.
                observing_windows=row["Block_Id"]
            )

        for _, row in df_visits.iterrows():
            values[row["Block_Id"]]["visits"].add(row["BlockVisit_Id"].item())

        def get_block_content(block_id):
            block = values.get(block_id)
            if not block:
                raise GraphQLError(
                    "There is no block with id {block_id}".format(block_id=block_id)
                )
            return BlockContent(**block)

        return [get_block_content(block_id) for block_id in block_ids]
