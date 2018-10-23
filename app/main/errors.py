from flask import jsonify
from app import log_exception
from . import main


def error(message):
    """
    Create a dictionary for an error message.

    The format of the dictionary is chosen to be consistent with GraphQL errors:

    .. code-block:: python
       {
         "errors": [
           {
             "message": message
           }
         ]
       }

    `message` is the message passed as the argument of this function.

    Parameters
    ----------
    message : str
        The error message.

    Returns
    -------
    dict :
        The dictionary with the error message.

    """

    return {"errors": [{"message": message}]}


@main.app_errorhandler(404)
def not_found(e):
    return jsonify(error("Not found")), 404


@main.app_errorhandler(500)
def internal_server_error(e):
    log_exception(e)
    return jsonify(error("Internal server error")), 500


@main.app_errorhandler(Exception)
def exception_raised(e):
    log_exception(e)
    return jsonify(error("Internal server error")), 500
