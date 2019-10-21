from collections import namedtuple
from graphene.types import Enum


_SemesterContent = namedtuple("SemesterContent", ["year", "semester"])


# partner


class PartnerCode(Enum):
    AMNH = "AMNH"
    CMU = "CMU"
    COM = "COM"
    DC = "DC"
    DDT = "DDT"
    DUR = "DUR"
    ENG = "ENG"
    GU = "GU"
    HET = "HET"
    IUCAA = "IUCAA"
    KEY = "KEY"
    OTH = "OTH"
    POL = "POL"
    RSA = "RSA"
    RU = "RU"
    SVP = "SVP"
    UC = "UC"
    UKSC = "UKSC"
    UNC = "UNC"
    UW = "UW"

    @property
    def description(self):
        if self == PartnerCode.AMNH:
            return "American Museum of Natural History"
        if self == PartnerCode.CMU:
            return "Carnegie Mellon University"
        if self == PartnerCode.COM:
            return "Commissioning Proposals"
        if self == PartnerCode.DC:
            return "Dartmouth College"
        if self == PartnerCode.DDT:
            return "Director Discretionary Time Proposals"
        if self == PartnerCode.DUR:
            return "Durham University"
        if self == PartnerCode.ENG:
            return "Engineering Proposals"
        if self == PartnerCode.GU:
            return "Georg-August-Universität Göttingen"
        if self == PartnerCode.HET:
            return "Hobby Eberly Telescope Board"
        if self == PartnerCode.IUCAA:
            return "Inter-University Centre for Astronomy & Astrophysics"
        if self == PartnerCode.KEY:
            return "Partnership Proposals for Key Science"
        if self == PartnerCode.OTH:
            return "Other"
        if self == PartnerCode.POL:
            return "Poland"
        if self == PartnerCode.RSA:
            return "South Africa"
        if self == PartnerCode.RU:
            return "Rutgers University"
        if self == PartnerCode.SVP:
            return "Science Verification Proposals"
        if self == PartnerCode.UC:
            return "University of Canterbury"
        if self == PartnerCode.UKSC:
            return "UK SALT Consortium"
        if self == PartnerCode.UNC:
            return "University of North Carolina - Chapel Hill"
        if self == PartnerCode.UW:
            return "University of Wisconsin-Madison"

        return "This is an undocumented partner code"


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

    @property
    def description(self):
        if self == ProposalStatus.ACCEPTED:
            return "The proposal has been accepted."
        if self == ProposalStatus.ACTIVE:
            return "The proposal is active and can be observed."
        if self == ProposalStatus.COMPLETED:
            return "The proposal has been completed."
        if self == ProposalStatus.DELETED:
            return "The proposal has been deleted."
        if self == ProposalStatus.EXPIRED:
            return "The proposal belongs to a past semester."
        if self == ProposalStatus.IN_PREPARATION:
            return "The proposal is still in preparation."
        if self == ProposalStatus.INACTIVE:
            return "The proposal is inactive abnd will not be observed."
        if self == ProposalStatus.REJECTED:
            return "The proposal has been rejected by the TACs."
        if self == ProposalStatus.SUPERSEDED:
            return "There exists a more recent version of the proposal."
        if self == ProposalStatus.UNDER_SCIENTIFIC_REVIEW:
            return "The proposal is under scientific review."
        if self == ProposalStatus.UNDER_TECHNICAL_REVIEW:
            return "The proposal is under technical review."

        return "This is an undocumented proposal status."


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

    @property
    def description(self):
        if self == ProposalType.COMMISSIONING:
            return "A proposal for helping with commissioning work."
        if self == ProposalType.DIRECTOR_DISCRETIONARY_TIME:
            return "A proposal using Director's Discretionary Time."
        if self == ProposalType.ENGINEERING:
            return "A proposal for helping with ewngineering work."
        if self == ProposalType.GRAVITATIONAL_WAVE_EVENT:
            return (
                "A proposal for observing the optical counterpart of a "
                "gravitational wave event."
            )
        if self == ProposalType.KEY_SCIENCE_PROGRAM:
            return "A proposal for a key science program."
        if self == ProposalType.LARGE_SCIENCE_PROPOSAL:
            return "A proposal for a large science program."
        if self == ProposalType.SCIENCE:
            return "A science proposal."
        if self == ProposalType.SCIENCE_LONG_TERM:
            return "A proposal spanning multiple semesters."
        if self == ProposalType.SCIENCE_VERIFICATION:
            return "A proposalm for helipng with science verification."

        return "This is an undocumented proposal type."


# proposal inactive reason


class ProposalInactiveReason(Enum):
    AWAITING_PI_INITIATION = "ToO, awaiting PI initiation"
    OTHER = "Other"
    TARGET_NOT_VISIBLE = "Target not visible"
    UNDOABLE = "Undoable"
    WAITING_FOR_FEEDBACK = "Waiting for feedback"
    WAITING_FOR_INSTRUMENT_AVAILABILITY = "Waiting for instrument availability"

    @property
    def description(self):
        if self == ProposalInactiveReason.AWAITING_PI_INITIATION:
            return (
                "The proposal is a target of opportunity proposal and has not "
                "been triggered by the Principal Investigator."
            )
        if self == ProposalInactiveReason.OTHER:
            return "There is another reason."
        if self == ProposalInactiveReason.TARGET_NOT_VISIBLE:
            return "The targets in the proposal cannot be with SALT at the moment."
        if self == ProposalInactiveReason.UNDOABLE:
            return "The observations requested in the proposal are unfeasible."
        if self == ProposalInactiveReason.WAITING_FOR_FEEDBACK:
            return "Feedback is required from the Principal Investigator."
        if self == ProposalInactiveReason.WAITING_FOR_INSTRUMENT_AVAILABILITY:
            return (
                "The instruments requested by the proposal are unavailable at "
                "the moment."
            )

        return "This is an undocumented reason for the proposal being inactive."


# block status


class BlockStatus(Enum):
    ACTIVE = "Active"
    COMPLETED = "Completed"
    DELETED = "Deleted"
    EXPIRED = "Expired"
    NOT_SET = "Not set"
    ON_HOLD = "On Hold"
    SUPERSEDED = "Superseded"

    @property
    def description(self):
        if self == BlockStatus.ACTIVE:
            return "The block is active and can be observed."
        elif self == BlockStatus.COMPLETED:
            return "All observations for the block have been completed."
        elif self == BlockStatus.DELETED:
            return "The block has been deleted."
        elif self == BlockStatus.EXPIRED:
            return "The block is expired and will not be observed any longer."
        elif self == BlockStatus.NOT_SET:
            return "The block status is undefined."
        elif self == BlockStatus.ON_HOLD:
            return "The block has been put on hold and will not be observed."
        elif self == BlockStatus.SUPERSEDED:
            return "There exists a newer version of the block."

        return "This is an undocumented block status."


# observation status


class ObservationStatus(Enum):
    ACCEPTED = "Accepted"
    DELETED = "Deleted"
    IN_QUEUE = "In queue"
    REJECTED = "Rejected"

    @property
    def description(self):
        if self == ObservationStatus.ACCEPTED:
            return "The observation has been accepted."
        elif self == ObservationStatus.REJECTED:
            return "The observation has been rejected."
        elif self == ObservationStatus.IN_QUEUE:
            return "The observation has been put in the queue."
        elif self == ObservationStatus.DELETED:
            return "The observation has been deleted."

        return "This is an undocumented observation status."


# observing window type

class ObservingWindowType(Enum):
    STRICT = "Strict"
    EXTENDED = "Extended"
    STRICT_EXTENDED = "Strict+Extended"

    @property
    def description(self):
        if self == ObservingWindowType.STRICT:
            return "A strict observing window. The Moon has the requested brightness during the window."
        if self == ObservingWindowType.EXTENDED:
            return "An extended observing window. The Moon brightness is greater than requested during the window."
        if self == ObservingWindowType.STRICT_EXTENDED:
            return "A strict and extended observing window. The Moon has the requested brightness in part of the " \
                   "window, but is brighter in another part. "
