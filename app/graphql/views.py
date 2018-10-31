from graphene_file_upload.flask import FileUploadGraphQLView
from graphene import Schema
from app import log_exception
from app.graphql.schema import Mutation, Query
from . import graphql


class LoggingMiddleware:
    """
    Graphene middleware for logging errors.

    """

    def on_error(self, e):
        log_exception(e)
        raise e

    def resolve(self, next, root, info, **args):
        return next(root, info, **args).catch(self.on_error)


schema = Schema(query=Query, mutation=Mutation)

view_func = FileUploadGraphQLView.as_view(
    "graphql", schema=schema, middleware=[LoggingMiddleware()], graphiql=True
)
graphql.add_url_rule("/graphql-api", view_func=view_func)
