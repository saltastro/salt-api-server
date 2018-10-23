from flask import g
from graphene import Int, ObjectType


class WhoAmI(ObjectType):
    @property
    def description(self):
        return "Description of the user making the query."

    user_id = Int(description='User id.')

    def resolve_user_id(self, info):
        return g.user.user_id
