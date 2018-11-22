from collections import namedtuple
from graphene.types import Enum


_SemesterContent = namedtuple("SemesterContent", ["year", "semester"])


# proposal status


class ProposalStatus(Enum):
    ACCEPTED = "Accepted"
    ACTIVE = "Active"
    COMPLETED = "Completed"
    DELETED = "Deleted"
    EXPIRED = "Expired"
    IN_PREPARATION = "In preparation"
    INACTIVE = "Inactive"
    REJECTED = "Rejected"
    SUPERSEDED = "Superseded"
    UNDER_SCIENTIFIC_REVIEW = "Under scientific review"
    UNDER_TECHNICAL_REVIEW = "Under technical review"


# proposal type


class ProposalType(Enum):
    COMMISSIONING = "Commissioning"
    DIRECTOR_DISCRETIONARY_TIME = "Director Discretionary Time (DDT)"
    ENGINEERING = "Engineering"
    GRAVITATIONAL_WAVE_EVENT = "Gravitational Wave Event"
    KEY_SCIENCE_PROGRAM = "Key Science Program"
    LARGE_SCIENCE_PROPOSAL = "Large Science Proposal"
    SCIENCE = "Science"
    SCIENCE_LONG_TERM = "Science - Long Term"
    SCIENCE_VERIFICATION = "Science Verification"


# proposal inactive reason


class ProposalInactiveReason(Enum):
    OTHER = "Other"
    TARGET_NOT_VISIBLE = "Target not visible"
    AWAITING_PI_INITIATION = "ToO, awaiting PI initiation"
    UNDOABLE = "Undoable"
    WAITING_FOR_FEEDBACK = "Waiting for feedback"
    WAITING_FOR_INSTRUMENT_AVAILABILITY = "Waiting for instrument availability"
