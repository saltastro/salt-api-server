from app.auth import encode


def test_valid_token_for_valid_credentials(client):
    """A valid token is returned if a token is requested with valid credentials."""

    query = """query {
    authToken(username: "joe", password: "joe") {
        token
    }
}"""

    expected_token = encode({"user_id": -42})
    res = client.post("/graphql", json={"query": query})

    token = res.get_json()["data"]["authToken"]["token"]
    assert token == expected_token


def test_error_for_invalid_credentials(client):
    """An error is returned if a token is requested with invalid credentials."""

    query = """query {
    authToken(username: "joe", password: "john") {
        token
    }
}"""

    res = client.post("/graphql", json={"query": query})
    assert len(res.get_json()["errors"]) > 0
