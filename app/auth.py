import jwt
import os
from flask import g, request


class User:
    """
    A user.

    Parameters
    ----------
    user_id : int
        The user id.

    """

    def __init__(self, user_id):
        self.user_id = user_id


def load_user(user_id):
    """
    Get the user for an id.

    Parameters
    ----------
    user_id : int or str
        The user id.

    Returns
    -------
    User :
        The user.

    """

    return User(int(user_id))


def verify_token():
    """
    Verify the token sent in the Authorization header.

    If the request has an Authorization header, it is checked whether it is of the
    form 'Token abcdef', with 'abcdef` denoting an encrypted JWT token. In case it is
    indeed of this form, the token is decrypted and the :func:`load_user` function is
    called to create a user object. The user object thus created is assigned as
    property `user` to Flask's `g` object.

    """
    g.user = None
    if "Authorization" in request.headers:
        parts = request.headers["Authorization"].split(None, 1)
        if len(parts) > 1:
            scheme, token = parts
            if scheme == "Token":
                try:
                    user = decode(token)
                except jwt.exceptions.DecodeError:
                    user = {}

                if "user_id" in user:
                    g.user = User(user["user_id"])


def encode(content):
    """
    Encode content into an encrypted JWT token in the format expected by the
    :func:`decode` method.

    Parameters
    ----------
    content : dict
        The content to encode.

    Returns
    -------
    str :
        The encrypted token.

    """

    token = jwt.encode(content, os.environ["JWT_SECRET_KEY"], algorithm="HS256")

    return token.decode("UTF-8")


def decode(token):
    """
    Decrypt and decode a JWT token.

    Parameters
    ----------
    token : str
        The token to decode.

    Returns
    -------
    dict :
        The content encoded in the token.

    """

    token_bytes = token.encode("UTF-8")

    return jwt.decode(token_bytes, os.environ["JWT_SECRET_KEY"], algorithm="HS256")
