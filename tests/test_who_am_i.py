def test_returns_user_id(graphql, snapshot):
    """The user id is returned for the user making the request."""

    query = '''query {
    whoAmI {
        userId
    }
}'''
    res = graphql(query, 42)
    snapshot.assert_match(res)
