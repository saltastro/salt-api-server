from graphene import Field, NonNull, ObjectType, String
from app.graphql.schema.auth_token import AuthToken


class Query(ObjectType):
    auth_token = Field(AuthToken,
                       description='Request an authentication token.',
                       username=NonNull(String, description='username'),
                       password=NonNull(String, description='Password'))

    def resolve_auth_token(self, info, username, password):
        return dict(username=username, password=password)
