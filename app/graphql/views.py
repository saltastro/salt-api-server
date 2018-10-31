from functools import wraps
from flask import g, jsonify, request
from flask_graphql import GraphQLView
from graphene import Schema
from app import log_exception
from app.graphql.schema import Mutation, Query
from app.main.errors import error
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

view_func = GraphQLView.as_view(
    "graphql", schema=schema, middleware=[LoggingMiddleware()], graphiql=True
)
graphql.add_url_rule("/graphql-api", view_func=view_func)
