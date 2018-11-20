from collections import namedtuple
import pandas as pd
from promise import Promise
from promise.dataloader import DataLoader
from graphql import GraphQLError
from app import db


ObservationContent = namedtuple(
    "ObservationContent", ["block", "night", "status", "rejection_reason"]
)


class ObservationLoader(DataLoader):
    """
    Data loader for observations.

    Observations in the GraphQL schema are called BlockVisit in the database.
    """

    def __init__(self):
        DataLoader.__init__(self, cache=False)

    def batch_load_fn(self, observation_ids):
        return Promise.resolve(self.get_observations(observation_ids))

    def get_observations(self, observation_ids):
        sql = """
SELECT BlockVisit_Id, Block_Id, Date, BlockVisitStatus, RejectedReason
       FROM BlockVisit AS bv
       JOIN NightInfo AS ni ON bv.NightInfo_Id = ni.NightInfo_Id
       JOIN BlockVisitStatus AS bvs ON bv.BlockVisitStatus_Id = bvs.BlockVisitStatus_Id
       LEFT JOIN BlockRejectedReason AS brr
            ON bv.BlockRejectedReason_Id = brr.BlockRejectedReason_Id
       WHERE BlockVisit_Id IN %(block_visit_ids)s
        """
        df = pd.read_sql(
            sql, con=db.engine, params=dict(block_visit_ids=observation_ids)
        )

        def get_observation_content(observation_id):
            row = df[df["BlockVisit_Id"] == observation_id]
            if len(row) == 0:
                raise GraphQLError(
                    "There is no observation with id {observation_id}".format(
                        observation_id=observation_id
                    )
                )
            return ObservationContent(
                block=int(row["Block_Id"].tolist()[0]),
                night=row["Date"].tolist()[0],
                status=row["BlockVisitStatus"].tolist()[0],
                rejection_reason=row["RejectedReason"].tolist()[0],
            )

        return [
            get_observation_content(observation_id)
            for observation_id in observation_ids
        ]
