from graphene import Field, NonNull, ObjectType, String
from app.graphql.schema.auth_token import AuthToken
from app.graphql.schema.who_am_i import WhoAmI


class Query(ObjectType):
    auth_token = Field(AuthToken,
                       description='Request an authentication token.',
                       username=NonNull(String, description='username'),
                       password=NonNull(String, description='Password'))

    who_am_i = Field(lambda: WhoAmI,
                     description='A description of the user making the query.')

    def resolve_auth_token(self, info, username, password):
        return dict(username=username, password=password)

    def resolve_who_am_i(self, info):
        return {}
