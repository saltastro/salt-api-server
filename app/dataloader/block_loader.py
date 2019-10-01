from collections import namedtuple
import pandas as pd
from promise import Promise
from promise.dataloader import DataLoader
from graphql import GraphQLError
from app import db
import time
from datetime import datetime
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

ObservingWindowContent = namedtuple(
    "ObservingWindowContent", ["night_start", "observing_window", "duration", "window_type"]
)


BlockObservingWindowContent = namedtuple(
    "BlockObservingWindowContent", ["past_windows", "todays_windows", "remaining_windows"]
)


class BlockLoader(DataLoader):
    START_OF_DAY_HOURS = 6  # 6:00 UT = 8:00 SAST

    def __init__(self):
        DataLoader.__init__(self, cache=False)

    def batch_load_fn(self, block_ids):
        return Promise.resolve(self.get_blocks(block_ids))

    def start_of_day(self, timestamp, day_start_hour):
        seconds_until_start_hour = day_start_hour * 3600
        seconds_per_day = 24 * 3600
        seconds_since_midnight = timestamp % seconds_per_day
        if seconds_since_midnight >= seconds_until_start_hour:
            # time start offset and midnight
            return (timestamp - seconds_since_midnight) + seconds_until_start_hour
        else:
            # time between midnight and start offset
            return (timestamp - seconds_since_midnight) - seconds_per_day + seconds_until_start_hour

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

        # block observing windows
        sql = """
        SELECT Block_Id, UNIX_TIMESTAMP(VisibilityStart) AS VisibilityStart, 
        UNIX_TIMESTAMP(VisibilityEnd) AS VisibilityEnd, BlockVisibilityWindowType 
        FROM BlockVisibilityWindow AS bvw
        JOIN BlockVisibilityWindowType AS bvwt ON bvw.BlockVisibilityWindowType_Id = bvwt.BlockVisibilityWindowType_Id
        WHERE Block_Id IN %(block_ids)s
        ORDER BY VisibilityStart DESC
        """

        df_block_observing_windows = pd.read_sql(sql, con=db.engine, params=dict(block_ids=block_ids))

        # collect the values
        values = dict()
        for _, row in df_blocks.iterrows():
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
                observing_windows=BlockObservingWindowContent(
                    past_windows=set(),
                    todays_windows=set(),
                    remaining_windows=set(),
                ),
            )

        for _, row in df_visits.iterrows():
            values[row["Block_Id"]]["visits"].add(row["BlockVisit_Id"].item())

        now = int(time.time())
        today = self.start_of_day(now, self.START_OF_DAY_HOURS)

        for _, row in df_block_observing_windows.iterrows():
            visibility_start = row["VisibilityStart"]
            visibility_end = row["VisibilityEnd"]
            window_type = row["BlockVisibilityWindowType"]
            start_of_night = self.start_of_day(visibility_start, self.START_OF_DAY_HOURS)

            observing_window = ObservingWindowContent(
                night_start=datetime.fromtimestamp(start_of_night).strftime("%d %B %Y"),
                observing_window="{} - {}".format(
                    datetime.fromtimestamp(visibility_start).strftime("%H:%M:%S"),
                    datetime.fromtimestamp(visibility_end).strftime("%H:%M:%S")
                ),
                duration=visibility_end - visibility_start,
                window_type=window_type
            )
            if start_of_night < today:
                values[row["Block_Id"]]["observing_windows"][0].add(
                    observing_window
                )
            elif start_of_night == today:
                values[row["Block_Id"]]["observing_windows"][1].add(
                    observing_window
                )
            elif start_of_night > today:
                values[row["Block_Id"]]["observing_windows"][2].add(
                    observing_window
                )

        def get_block_content(block_id):
            block = values.get(block_id)
            if not block:
                raise GraphQLError(
                    "There is no block with id {block_id}".format(block_id=block_id)
                )
            return BlockContent(**block)

        return [get_block_content(block_id) for block_id in block_ids]
