from collections import namedtuple
import pandas as pd
from promise import Promise
from promise.dataloader import DataLoader
from graphql import GraphQLError
from app import db


PartnerTimeShareContent = namedtuple(
  "PartnerTimeShareContent", ["partner_code", "share_percent"]
)


class PartnerTimeShareLoader(DataLoader):
    def __init__(self):
        DataLoader.__init__(self, cache=False)

    def batch_load_fn(self, partner_codes):
        return Promise.resolve(self.get_partners_time_share(partner_codes))

    def get_partners_time_share(self, partner_codes):
        sql = """
SELECT Partner_Code, SharePercent
        FROM PartnerShareTimeDist AS pst
        JOIN Semester AS s ON pst.Semester_Id = s.Semester_Id
        JOIN Partner AS partner ON pst.Partner_Id = partner.Partner_Id
        WHERE partner.Partner_Code IN %(partner_codes)s"""

        df = pd.read_sql(
          sql, con=db.engine, params=dict(partner_codes=partner_codes)
        )

        # collect the values
        data = dict()
        for _, row in df.iterrows():
            data[row["Partner_Code"]] = dict(
                partner_code=row["Partner_Code"],
                share_percent=row["SharePercent"],
            )

        def get_partner_time_share_content(partner_code):
            partner = data.get(partner_code)
            if not partner:
                raise GraphQLError(
                  "There is no partner with partner code {partner_code}".format(
                    partner_code=partner_code
                  )
                )
            return PartnerTimeShareContent(**partner)

        return [
            get_partner_time_share_content(partner_code) for partner_code in partner_codes
        ]
