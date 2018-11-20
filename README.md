# Welcome to SALT API Server

A server for the API of the Southern African Large Telescope (SALT). This is currently geared towards investigators who might want to check their proposal's progress, (re)submit proposal content, and put observing blocks on and off hold.

This is work in progress, and not all functionality is in place yet.

## Using the API

The following assumes that the API is available at `http://localhost:5000`. Replace this with the correct URL when using any of the queries below.

### GraphQL

API queries are made with [GraphQL](https://flaviocopes.com/graphql/).

### Viewing the API

GraphiQL is enabled on the server, allowing you to view the API by pointing your browsewr to `http://saltapi`.

### Authentication

Authentication is required for using (most of) the API. You authenticate by including an `Authorization` header with a valid authentication token with your HTTP request. For example:

```
Authorization: Token eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjo0fQ.Lst7gMf9G2j1FCBCMIDSq3TGF00JnjtAvGA6m-FsmRg
```

You can request a token with a GraphQL query.

```graphql
query {
  authToken(username: "frodo", password: "secret") {
    token
  }
}
```

As a curl request:

```bash
curl 'http://localhost:5000/graphql-api' -H 'Content-Type: application/json' -H 'Accept: application/json' --data-binary '{"query":"query {\n  authToken(username: \"frodo\", password: \"secret\") {\n    token\n  }\n}\n"}'
```

### Observations for a proposal

The following query returns the observations done for proposal 2018-1-SCI-042.

```graphql
query {
  proposal(proposalCode: "2018-1-SCI-008") {
    observations {
      night
      status
    }
  }
}
```

As a curl request:

```bash
curl 'http://localhost:5000/graphql-api' -H 'Content-Type: application/json' -H 'Accept: application/json' -H 'Authorization: Token eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjo0fQ.Lst7gMf9G2j1FCBCMIDSq3TGF00JnjtAvGA6m-FsmRg' --data-binary '{"query":"query {\n  proposal(proposalCode: \"2018-1-SCI-008\") {\n    observations {\n      night\n      status\n    }\n  }\n}\n"}'
```

### Putting a block on and off hold

An active block can be put on hold.

```graphql
mutation {
  putBlockOnHold(blockId: 1234) {
    ok
  }
}
```

As a curl request:

```bash
curl 'http://localhost:5000/graphql-api' -H 'Content-Type: application/json' -H 'Accept: application/json' -H 'Authorization: Token eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjo0fQ.Lst7gMf9G2j1FCBCMIDSq3TGF00JnjtAvGA6m-FsmRg' --data-binary '{"query":"mutation {\n  putBlockOnHold(blockId: 1234) {\n    ok\n  }\n}\n"}' --compressed
```

You may add a reason for putting the block on hold.

```graphql
mutation {
  putBlockOnHold(blockId: 1234, reason: "Wrong phase") {
    ok
  }
}
```

As a curl request:

```graphql
curl 'http://localhost:5000/graphql-api' -H 'Content-Type: application/json' -H 'Accept: application/json' -H 'Authorization: Token eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjo0fQ.Lst7gMf9G2j1FCBCMIDSq3TGF00JnjtAvGA6m-FsmRg' --data-binary '{"query":"mutation {\n  putBlockOnHold(blockId: 1234, reason: \"Wrong phase\") {\n    ok\n  }\n}\n"}'
```

An existing reason will be replaced or (if no reason is given) deleted.
 
A block on hold can be activated again.

```graphql
mutation {
  putBlockOffHold(blockId: 1234) {
    ok
  }
}
```

As a curl request:

```bash
curl 'http://localhost:5000/graphql-api' -H 'Content-Type: application/json' -H 'Accept: application/json' -H 'Authorization: Token eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjo0fQ.Lst7gMf9G2j1FCBCMIDSq3TGF00JnjtAvGA6m-FsmRg' --data-binary '{"query":"mutation {\n  putBlockOnHold(blockId: 1234) {\n    ok\n  }\n}\n"}' --compressed
```

You may add a reason for putting the block on hold.

```graphql
mutation {
  putBlockOffHold(blockId: 1234, reason: "Wrong phase") {
    ok
  }
}
```

As a curl request:

```graphql
curl 'http://localhost:5000/graphql-api' -H 'Content-Type: application/json' -H 'Accept: application/json' -H 'Authorization: Token eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjo0fQ.Lst7gMf9G2j1FCBCMIDSq3TGF00JnjtAvGA6m-FsmRg' --data-binary '{"query":"mutation {\n  putBlockOnHold(blockId: 1234, reason: \"Wrong phase\") {\n    ok\n  }\n}\n"}'
```

An existing reason will be replaced or (if no reason is given) deleted.

### Submitting a proposal

*This functionality is not implemented yet. It will be be implemented using the [GraphQL multipart request specification](https://github.com/jaydenseric/graphql-multipart-request-spec).*

A proposal can be (re)submitted.

```graphql
mutation($file: Upload!) {
  submitProposal(proposalCode: "2018-1-SCI-042", zip: $file) {
     proposal {
       proposalCode
     }
  }
}
```

The proposal code is optional. If it is included, the submission is considered to be the resubmission of an existing proposal. Otherwise the submitted proposal is considered a completely new proposal. `zip` is a zip file with the proposal XML and all required file attachments.

### Submitting a block

*This functionality is not implemented yet. It will be be implemented using the [GraphQL multipart request specification](https://github.com/jaydenseric/graphql-multipart-request-spec).*

A block can be (re)submitted.

```graphql
mutation($file: Upload!) {
  submitBlock(proposalCode: "2018-1-SCI-042", blockCode: "59caca6f-edbb-4d10-bb62-e439f2c55a5e", zip: $file) {
    block {
      name
    }
  }
}
```

The block code is optional. If it is included, the submission is considered to be the resubmission of an existing block. Otherwise the submitted block is considered a completely new block. `zip` is a zip file with the block XML and all required file attachments.
