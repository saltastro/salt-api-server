from collections import namedtuple
import pandas as pd
from promise import Promise
from promise.dataloader import DataLoader
from app import db


ProposalContent = namedtuple(
    "ProposalContent", ["proposal_code", "title", "blocks", "observations"]
)


class ProposalLoader(DataLoader):
    def batch_load_fn(self, proposal_codes):
        return Promise.resolve(self.get_proposals(proposal_codes))

    def get_proposals(self, proposal_codes):
        # general proposal info
        sql = """
SELECT Proposal_Code, Title
       FROM Proposal AS p
       JOIN ProposalCode AS pc ON p.ProposalCode_Id = pc.ProposalCode_Id
       JOIN ProposalText AS pt ON p.ProposalCode_Id = pt.ProposalCode_Id
       WHERE Current=1 AND Proposal_Code IN %(proposal_codes)s
       """
        df_general_info = pd.read_sql(
            sql, con=db.engine, params=dict(proposal_codes=proposal_codes)
        )

        # blocks
        sql = """
SELECT Proposal_Code, GROUP_CONCAT(Block_Id) AS Block_Ids
       FROM Block AS b
       JOIN ProposalCode AS pc ON b.ProposalCode_Id = pc.ProposalCode_Id
       JOIN BlockStatus AS bs ON b.BlockStatus_Id = bs.BlockStatus_Id
       WHERE Proposal_Code IN %(proposal_codes)s
             AND BlockStatus IN ('Active', 'Completed', 'On Hold')
       GROUP BY pc.ProposalCode_Id
       """
        df_blocks = pd.read_sql(
            sql, con=db.engine, params=dict(proposal_codes=proposal_codes)
        )

        # observations (i.e. block visits)
        sql = """
SELECT Proposal_Code, GROUP_CONCAT(BlockVisit_Id) AS BlockVisit_Ids
       FROM BlockVisit AS bv
       JOIN Block AS b ON bv.Block_Id = b.Block_Id
       JOIN ProposalCode AS pc ON b.ProposalCode_Id = pc.ProposalCode_Id
       WHERE Proposal_Code IN %(proposal_codes)s
       GROUP BY pc.ProposalCode_Id
        """
        df_block_visits = pd.read_sql(
            sql, con=db.engine, params=dict(proposal_codes=proposal_codes)
        )

        def proposal_content(proposal_code):
            general_info = df_general_info[
                df_general_info["Proposal_Code"] == proposal_code
            ]
            block_data = df_blocks[df_blocks["Proposal_Code"] == proposal_code]
            blocks = [int(id) for id in block_data["Block_Ids"].tolist()[0].split(",")]
            block_visits = df_block_visits[
                df_block_visits["Proposal_Code"] == proposal_code
            ]
            observations = [
                int(id) for id in block_visits["BlockVisit_Ids"].tolist()[0].split(",")
            ]
            return ProposalContent(
                proposal_code=proposal_code,
                title=general_info["Title"].tolist()[0],
                blocks=blocks,
                observations=observations,
            )

        # collect results
        proposals = [
            proposal_content(proposal_code) for proposal_code in proposal_codes
        ]

        return Promise.resolve(proposals)
