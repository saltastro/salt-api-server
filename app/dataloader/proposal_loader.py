from collections import namedtuple
import pandas as pd
from promise import Promise
from promise.dataloader import DataLoader
from app import db


ProposalContent = namedtuple("ProposalContent", ["proposal_code", "title"])


class ProposalLoader(DataLoader):
    def batch_load_fn(self, proposal_codes):
        return Promise.resolve(self.get_proposals(proposal_codes))

    def get_proposals(self, proposal_codes):
        sql = """
SELECT Proposal_Code, Title
       FROM Proposal AS p
       JOIN ProposalCode AS pc ON p.ProposalCode_Id = pc.ProposalCode_Id
       JOIN ProposalText AS pt ON p.ProposalCode_Id = pt.ProposalCode_Id
       WHERE p.Current=1 AND Proposal_Code IN %(proposal_codes)s
       """
        print(sql)
        df = pd.read_sql(sql, con=db.engine, params=dict(proposal_codes=proposal_codes))

        return [
            ProposalContent(proposal_code=df["Proposal_Code"][i], title=df["Title"][i])
            for i in range(len(df))
        ]
