from collections import namedtuple
import pandas as pd
from graphene import Field, NonNull, ObjectType, String
from graphql import GraphQLError
from app import db
from app.auth import encode
from app.graphql.schema.auth_token import AuthToken


Token = namedtuple('Token', ['token'])


class Query(ObjectType):
    auth_token = Field(lambda: AuthToken,
                       description='Request an authentication token.',
                       username=NonNull(String, description='username'),
                       password=NonNull(String, description='Password'))

    def resolve_auth_token(self, info, username, password):
        # query for the user with the given credentials
        sql = '''SELECT PiptUser_Id
                        FROM PiptUser
                        WHERE Username=%(username)s AND Password=MD5(%(password)s)'''
        df = pd.read_sql(sql,
                         con=db.engine,
                         params=dict(username=username, password=password))

        # check whether a user was found
        if len(df) == 0:
            raise GraphQLError('username or password wrong')

        # encode and return the user id
        token = encode({'user_id': df['PiptUser_Id'][0].item()})
        return Token(token=token)
