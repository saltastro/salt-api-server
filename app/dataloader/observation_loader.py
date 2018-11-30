from collections import namedtuple
import pandas as pd
import pytz
from promise import Promise
from promise.dataloader import DataLoader
from graphql import GraphQLError
from app import db
from app.util import ObservationStatus


ObservationContent = namedtuple(
    "ObservationContent", ["block", "night", "start", "status", "rejection_reason"]
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
        sql_visit = """
SELECT BlockVisit_Id, Block_Id, Date, BlockVisitStatus, RejectedReason
       FROM BlockVisit AS bv
       JOIN NightInfo AS ni ON bv.NightInfo_Id = ni.NightInfo_Id
       JOIN BlockVisitStatus AS bvs ON bv.BlockVisitStatus_Id = bvs.BlockVisitStatus_Id
       LEFT JOIN BlockRejectedReason AS brr
            ON bv.BlockRejectedReason_Id = brr.BlockRejectedReason_Id
       WHERE BlockVisit_Id IN %(block_visit_ids)s
        """
        df_visit = pd.read_sql(
            sql_visit, con=db.engine, params=dict(block_visit_ids=observation_ids)
        )

        sql_start = """
SELECT BlockVisit_Id, MIN(UTStart) AS Start
       FROM FileData
       WHERE BlockVisit_Id IN %(block_visit_ids)s
       GROUP BY BlockVisit_Id
"""
        df_start = pd.read_sql(
            sql_start, con=db.engine, params=dict(block_visit_ids=observation_ids)
        )

        # collect the values
        values = dict()
        for _, row in df_visit.iterrows():
            values[row["BlockVisit_Id"]] = dict(
                block=int(row["Block_Id"]),
                night=row["Date"],
                status=ObservationStatus.get(row["BlockVisitStatus"]),
                rejection_reason=row["RejectedReason"],
                start=None,
            )
        for _, row in df_start.iterrows():
            values[row["BlockVisit_Id"]]["start"] = row["Start"].replace(
                tzinfo=pytz.UTC
            )

        def get_observation_content(observation_id):
            visit = values.get(observation_id)
            if not visit:
                raise GraphQLError(
                    "There is no observation with id {observation_id}".format(
                        observation_id=observation_id
                    )
                )

            return ObservationContent(**visit)

        return [
            get_observation_content(observation_id)
            for observation_id in observation_ids
        ]
