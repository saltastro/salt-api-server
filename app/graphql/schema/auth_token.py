from graphene import ObjectType, String
from graphql import GraphQLError
from app.auth import encode


class AuthToken(ObjectType):
    @property
    def description(self):
        return '''A JWT authentication token. If an API query requires authentication, 
include an Authorization HTTP header with your request. The header value must be of the 
form "Token {token}", where {token} is the JWT token.'''  # noqa

    token = String(description='Authentication token')

    def resolve_token(self, info):
        username = self['username']
        password = self['password']
        if username != password:
            raise GraphQLError('username or password wrong')

        # CHANGE THIS LINE
        return encode(dict(user_id=-42))
