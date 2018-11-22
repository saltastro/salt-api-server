from collections import namedtuple
import pandas as pd
from promise import Promise
from promise.dataloader import DataLoader
from graphql import GraphQLError
from app import db
from app.util import _SemesterContent


ProposalContent = namedtuple(
    "ProposalContent",
    ["proposal_code", "title", "blocks", "observations", "time_allocations"],
)

TimeAllocationContent = namedtuple(
    "TimeAllocation", ["priority", "semester", "partner_code", "amount"]
)


class ProposalLoader(DataLoader):
    def __init__(self):
        DataLoader.__init__(self, cache=False)

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
        values = dict()
        for _, row in df_general_info.iterrows():
            values[row["Proposal_Code"]] = dict(
                proposal_code=row["Proposal_Code"],
                title=row["Title"],
                blocks=set(),
                observations=set(),
                time_allocations=set(),
            )

        # blocks
        sql = """
SELECT Proposal_Code, Block_Id
       FROM Block AS b
       JOIN ProposalCode AS pc ON b.ProposalCode_Id = pc.ProposalCode_Id
       JOIN BlockStatus AS bs ON b.BlockStatus_Id = bs.BlockStatus_Id
       WHERE Proposal_Code IN %(proposal_codes)s
             AND BlockStatus IN ('Active', 'Completed', 'On Hold')
        """
        df_blocks = pd.read_sql(
            sql, con=db.engine, params=dict(proposal_codes=proposal_codes)
        )
        for _, row in df_blocks.iterrows():
            values[row["Proposal_Code"]]["blocks"].add(row["Block_Id"])

        # observations (i.e. block visits)
        sql = """
SELECT Proposal_Code, BlockVisit_Id
       FROM BlockVisit AS bv
       JOIN Block AS b ON bv.Block_Id = b.Block_Id
       JOIN ProposalCode AS pc ON b.ProposalCode_Id = pc.ProposalCode_Id
       WHERE Proposal_Code IN %(proposal_codes)s
        """
        df_block_visits = pd.read_sql(
            sql, con=db.engine, params=dict(proposal_codes=proposal_codes)
        )
        for _, row in df_block_visits.iterrows():
            values[row["Proposal_Code"]]["observations"].add(row["BlockVisit_Id"])

        # time allocations
        sql = """
SELECT Proposal_Code, Priority, Year, Semester, Partner_Code, TimeAlloc
       FROM PriorityAlloc AS pa
       JOIN MultiPartner AS mp ON pa.MultiPartner_Id = mp.MultiPartner_Id
       JOIN Partner AS p ON mp.Partner_Id = p.Partner_Id
       JOIN Semester ON mp.Semester_Id = Semester.Semester_Id
       JOIN ProposalCode ON mp.ProposalCode_Id = ProposalCode.ProposalCode_Id
       WHERE Proposal_Code IN ('2018-2-MLT-005') AND TimeAlloc>0
"""
        df_time_alloc = pd.read_sql(
            sql, con=db.engine, params=dict(proposal_codes=proposal_codes)
        )
        for _, row in df_time_alloc.iterrows():
            semester = _SemesterContent(year=row["Year"], semester=row["Semester"])
            values[row["Proposal_Code"]]["time_allocations"].add(
                TimeAllocationContent(
                    priority=row["Priority"],
                    semester=semester,
                    partner_code=row["Partner_Code"],
                    amount=row["TimeAlloc"],
                )
            )

        def proposal_content(proposal_code):
            proposal = values.get(proposal_code)
            if not proposal:
                raise GraphQLError(
                    "There exists no proposal with proposal code {code}".format(
                        code=proposal_code
                    )
                )

            return ProposalContent(**proposal)

        # collect results
        proposals = [
            proposal_content(proposal_code) for proposal_code in proposal_codes
        ]

        return Promise.resolve(proposals)
