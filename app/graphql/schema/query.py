from collections import namedtuple
import pandas as pd
from graphene import Field, NonNull, ObjectType, String
from graphql import GraphQLError
from app import db
from app.auth import encode
from app.graphql.schema.auth_token import AuthToken
from app.graphql.schema.proposal import Proposal
from app import loaders


_TokenContent = namedtuple('TokenContent', ['token'])


class Query(ObjectType):
    auth_token = Field(lambda: AuthToken,
                       description='Request an authentication token.',
                       username=NonNull(String, description='username'),
                       password=NonNull(String, description='Password'))

    proposal = Field(lambda: Proposal,
                     description='A SALT proposal.',
                     proposal_code=NonNull(String, description='The proposal code.'))

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
        return _TokenContent(token=token)

    def resolve_proposal(self, info, proposal_code):
        return loaders['proposal_loader'].load(proposal_code)
