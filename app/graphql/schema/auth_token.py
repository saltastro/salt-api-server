from graphene import ObjectType, String


class AuthToken(ObjectType):
    @property
    def description(self):
        return """A JWT authentication token. If an API query requires authentication, 
include an Authorization HTTP header with your request. The header value must be of the 
form "Token {token}", where {token} is the JWT token."""  # noqa

    token = String(description="Authentication token")

    def resolve_token(self, info):
        return self.token
