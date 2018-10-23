import pytest
from app import create_app
from app.auth import encode


@pytest.fixture()
def app():
    """
    Fixture for creating the Flask app.

    This fixture is used by the `client` fixture provided by `pytest-flask`, and you
    normally should not have to use it yourself. The Flask app is created in test mode.

    Yields
    ------
    Flask app :
        The created Flask app.

    """

    app = create_app("testing")

    yield app


@pytest.fixture()
def graphql(client):
    """
    Fixture for making GraphQL queries.

    This fixture yields a function facilitating making GraphQL queries. The function
    takes a user id and a GraphQL as its arguments. The GraphQL query is sent to the
    Flask server along with an authentication token with the user id. The server
    response is parsed as a JSON objecty, and the corresponding `dict` object is
    returned.

    """

    def graphql_query(query, user_id):
        # get the authentication token.
        token = encode({"user_id": user_id})

        # send the GraphQL to the server.
        res = client.post(
            "/graphql",
            json={"query": query},
            headers={"Authorization": "Token {token}".format(token=token)},
        )

        # return the server response as a JSON dict
        return res.get_json()

    yield graphql_query
