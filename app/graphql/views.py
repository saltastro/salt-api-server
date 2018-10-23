from flask_graphql import GraphQLView
from graphene import Schema
from app import log_exception
from app.graphql.schema.query import Query
from . import graphql


class LoggingMiddleware:
    def on_error(self, e):
        log_exception(e)
        raise e

    def resolve(self, next, root, info, **args):
        return next(root, info, **args).catch(self.on_error)


schema = Schema(query=Query)

view_func = GraphQLView.as_view(
    "graphql", schema=schema, middleware=[LoggingMiddleware()], graphiql=True
)
graphql.add_url_rule("/graphql", view_func=view_func)
