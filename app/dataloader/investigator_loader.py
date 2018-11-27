from collections import namedtuple
import pandas as pd
from promise import Promise
from promise.dataloader import DataLoader
from graphql import GraphQLError
from app import db


InvestigatorContent = namedtuple(
    "InvestigatorContent", ["id", "given_name", "family_name", "email"]
)


class InvestigatorLoader(DataLoader):
    def __init__(self):
        DataLoader.__init__(self, cache=False)

    def batch_load_fn(self, investigator_ids):
        return Promise.resolve(self.get_investigators(investigator_ids))

    def get_investigators(self, investigator_ids):
        sql = """
SELECT Investigator_Id, FirstName, Surname, Email
       FROM Investigator
       WHERE Investigator_Id IN %(investigator_ids)s
        """
        df = pd.read_sql(
            sql, con=db.engine, params=dict(investigator_ids=investigator_ids)
        )

        # collect the values
        data = dict()
        for _, row in df.iterrows():
            data[row["Investigator_Id"]] = dict(
                id=row["Investigator_Id"],
                given_name=row["FirstName"],
                family_name=row["Surname"],
                email=row["Email"],
            )

        def get_investigator(investigator_id):
            investigator = data.get(investigator_id)
            if not investigator:
                raise GraphQLError(
                    "There is no investigator with id {investigator_id}".format(
                        investigator_id=investigator_id
                    )
                )
            return InvestigatorContent(**investigator)

        return [
            get_investigator(investigator_id) for investigator_id in investigator_ids
        ]
