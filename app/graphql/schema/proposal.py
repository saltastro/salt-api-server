from graphene import ObjectType, String


class Proposal(ObjectType):
    proposal_code = String(description='The proposal code, such as 2018-2-SCI-042.')

    title = String(description='The proposal title.')

    def resolve_proposal_code(self, info):
        return self.proposal_code

    def resolve_title(self, info):
        return self.title
