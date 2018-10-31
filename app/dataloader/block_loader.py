from collections import namedtuple
import pandas as pd
from promise import Promise
from promise.dataloader import DataLoader
from app import db


BlockContent = namedtuple(
    "BlockContent",
    ["id", "block_code", "proposal", "name", "status", "status_reason"],
)


class BlockLoader(DataLoader):
    def batch_load_fn(self, block_ids):
        return Promise.resolve(self.get_blocks(block_ids))

    def get_blocks(self, block_ids):
        sql = """
SELECT Block_Id, BlockCode, Proposal_Code, Block_Name, BlockStatus, BlockStatusReason
       FROM Block AS b
       JOIN BlockCode AS bc ON b.BlockCode_Id = bc.BlockCode_Id
       JOIN BlockStatus AS bs ON b.BlockStatus_Id = bs.BlockStatus_Id
       JOIN ProposalCode ON b.ProposalCode_Id = ProposalCode.ProposalCode_Id
       WHERE Block_Id IN %(block_ids)s
        """
        df = pd.read_sql(sql, con=db.engine, params=dict(block_ids=block_ids))

        def get_block_content(block_id):
            row = df[df["Block_Id"] == block_id]

            status = row["BlockStatus"].tolist()[0]
            if status.lower() == "not set":
                status = None
            return BlockContent(
                id=row["Block_Id"].tolist()[0],
                block_code=row["BlockCode"].tolist()[0],
                proposal=row["Proposal_Code"].tolist()[0],
                name=df["Block_Name"].tolist()[0],
                status=status,
                status_reason=df["BlockStatusReason"].tolist()[0],
            )

        return [get_block_content(block_id) for block_id in block_ids]
