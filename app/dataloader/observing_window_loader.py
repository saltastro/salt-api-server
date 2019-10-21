import time
from collections import namedtuple
import pandas as pd
from promise import Promise
from promise.dataloader import DataLoader
from graphql import GraphQLError
from app import db
from datetime import datetime

ObservingWindowContent = namedtuple(
  "ObservingWindowContent", ["visibility_start", "visibility_end", "duration", "window_type"]
)

BlockObservingWindowContent = namedtuple(
  "BlockObservingWindowContent", ["past_windows", "tonights_windows", "future_windows"]
)


class ObservingWindowLoader(DataLoader):
    """
    Data loader for observing windows.

    """

    START_OF_DAY_HOURS = 6  # 6:00 UT = 8:00 SAST

    def __init__(self):
        DataLoader.__init__(self, cache=False)

    def start_of_day(self, timestamp, day_start_hour):
        seconds_until_start_hour = day_start_hour * 3600
        seconds_per_day = 24 * 3600
        seconds_since_midnight = timestamp % seconds_per_day
        if seconds_since_midnight >= seconds_until_start_hour:
            # The day has started, and we may use today's start time.
            return (timestamp - seconds_since_midnight) + seconds_until_start_hour
        else:
            # The day has not started yet, and we have to use yesterday's start time
            return (timestamp - seconds_since_midnight) - seconds_per_day + seconds_until_start_hour

    def batch_load_fn(self, block_ids_window_types):
        return Promise.resolve(self.get_observing_windows(block_ids_window_types))

    def get_observing_windows(self, block_ids_window_types):
        block_ids = set()
        window_types = set()
        for block_id, window_type in block_ids_window_types:
            block_ids.add(block_id)
            window_types.add(window_type)

        # block observing windows query
        sql_observing_windows = """
        SELECT Block_Id, UNIX_TIMESTAMP(VisibilityStart) AS VisibilityStart, 
        UNIX_TIMESTAMP(VisibilityEnd) AS VisibilityEnd, BlockVisibilityWindowType 
        FROM BlockVisibilityWindow AS bvw
        JOIN BlockVisibilityWindowType AS bvwt ON bvw.BlockVisibilityWindowType_Id = bvwt.BlockVisibilityWindowType_Id
        WHERE Block_Id IN %(block_ids)s AND BlockVisibilityWindowType IN %(window_types)s
        ORDER BY VisibilityStart DESC
        """

        df_block_observing_windows = pd.read_sql(
            sql_observing_windows,
            con=db.engine,
            params=dict(block_ids=block_ids, window_types=window_types)
        )

        # now timestamp
        now = int(time.time())
        # the time today began
        today = self.start_of_day(now, self.START_OF_DAY_HOURS)

        # collect the values
        values = dict()
        for block_id_window_type in block_ids_window_types:
            past_windows = set()
            tonights_windows = set()
            future_windows = set()
            for _, row in df_block_observing_windows.iterrows():
                if block_id_window_type == (row["Block_Id"], row["BlockVisibilityWindowType"]):
                    visibility_start = row["VisibilityStart"]
                    visibility_end = row["VisibilityEnd"]
                    window_type = row["BlockVisibilityWindowType"]
                    # the start time for the date to which this observing window belongs
                    start_of_night = self.start_of_day(visibility_start, self.START_OF_DAY_HOURS)
                    # observing window details
                    observing_window_details = ObservingWindowContent(
                        visibility_start=datetime.fromtimestamp(visibility_start).isoformat(),
                        visibility_end=datetime.fromtimestamp(visibility_end).isoformat(),
                        duration=visibility_end - visibility_start,
                        window_type=window_type
                    )
                    if start_of_night < today:
                        past_windows.add(observing_window_details)
                    elif start_of_night == today:
                        tonights_windows.add(observing_window_details)
                    elif start_of_night > today:
                        future_windows.add(observing_window_details)

            # collect details of the block
            values[block_id_window_type] = dict(
                past_windows=sorted(
                    past_windows,
                    key=lambda x: x[0]
                ),
                tonights_windows=sorted(
                    tonights_windows,
                    key=lambda x: x[0]
                ),
                future_windows=sorted(
                    future_windows,
                    key=lambda x: x[0]
                ),
            )

        def get_observing_window_content(observing_window_id):
            observing_window = values.get(observing_window_id)
            if not observing_window:
                raise GraphQLError(
                    """There is no observing window for the block with id {block_id} 
                    and observing window type {window_type}""".format(
                        block_id=observing_window_id[0],
                        window_type=observing_window_id[1]
                    )
                )

            return BlockObservingWindowContent(**observing_window)

        return [
            get_observing_window_content(block_id_window_type)
            for block_id_window_type in block_ids_window_types
        ]
