# TODO: view() is now a historical session -- "request.session"
# TODO: auth headers a **url_parms?? -- may wat to be separate test, since is based on a lib for just us
#    ? will put JWT in header
###from socom_simplejwt.test import APITokenTestCase # then make this a part of class that ALL tests belong to
#    ? will use diff graphql import (graphiql_headers) -- by GraphQLView.as_view(graphiql_headers=True) in urls ??
#    -- also in settings.py INSTALLED_APPS
#
# ?? want to run just a specifed test -- test_graphiql_is_enabled()
# ?? this (need to make tests() seesion aware??):
#    E               AttributeError: 'WSGIRequest' object has no attribute 'session'
# ? is session in MIDDLEWARE ??

import json
import pytest
try:
    from urllib import urlencode
except ImportError:
    from urllib.parse import urlencode


def url_string(string="/graphql", **url_params):
    if url_params:
        string += "?" + urlencode(url_params)

    return string


def batch_url_string(**url_params):
    return url_string("/graphql/batch", **url_params)


j = lambda **kwargs: json.dumps(kwargs)
jl = lambda **kwargs: json.dumps([kwargs])


@pytest.mark.django_db
def test_graphiql_is_enabled(client):
    from django.conf import settings

    response = client.get(url_string(), HTTP_ACCEPT="text/html")

    assert response.status_code == 200
    assert response["Content-Type"].split(";")[0] == "text/html"


@pytest.mark.django_db
def test_qfactor_graphiql(client):
    response = client.get(
        url_string(
            query="{test}",
            HTTP_ACCEPT="text/html",
        )
    )

    assert response.status_code == 200
    assert response["Content-Type"].split(";")[0] == "text/html"


@pytest.mark.django_db
def test_qfactor_json(client):
    response = client.get(
        url_string(
            query="{test}",
            HTTP_ACCEPT="application/json",
        )
    ).json()

    # returns just json as __dict__
    expected_dict = {"data": {"test": "Hello World"}}
    # directly compare all key,value for __dict__
    assert response == expected_dict


@pytest.mark.django_db
def test_allows_get_with_query_param(client):
    response = client.get(url_string(query="{test}"))

    assert response.status_code == 200
    # returns just json as __dict__
    expected_dict = {"data": {"test": "Hello World"}}
    # directly compare all key,value for __dict__
    assert response.json() == expected_dict


@pytest.mark.django_db
def test_allows_get_with_variable_values(client):
    response = client.get(
        url_string(
            query="query helloWho($who: String){ test(who: $who) }",
            variables=json.dumps({"who": "Dolly"}),
            HTTP_ACCEPT="application/json",
        )
    )

    assert response.status_code == 200
    expected_dict = {"data": {"test": "Hello Dolly"}}
    # directly compare all key,value for __dict__
    assert response.json() == expected_dict


@pytest.mark.django_db
def test_allows_get_with_operation_name(client):
    response = client.get(
        url_string(
            query="""
        query helloYou { test(who: "You"), ...shared }
        query helloWorld { test(who: "World"), ...shared }
        query helloDolly { test(who: "Dolly"), ...shared }
        fragment shared on QueryRoot {
          shared: test(who: "Everyone")
        }
        """,
            operationName="helloWorld",
        )
    )

    assert response.status_code == 200
    expected_dict = {"data": {"test": "Hello World", "shared": "Hello Everyone"}}
    # directly compare all key,value for __dict__
    assert response.json() == expected_dict


@pytest.mark.django_db
def test_reports_validation_errors(client):
    response = client.get(url_string(query="{ test, unknownOne, unknownTwo }"))

    assert response.status_code == 400
    expected_dict = {
        "errors": [
            {
                "message": 'Cannot query field "unknownOne" on type "QueryRoot".',
                "locations": [{"line": 1, "column": 9}],
            },
            {
                "message": 'Cannot query field "unknownTwo" on type "QueryRoot".',
                "locations": [{"line": 1, "column": 21}],
            },
        ]
    }
    # directly compare all key,value for __dict__
    assert response.json() == expected_dict


@pytest.mark.django_db
def test_errors_when_missing_operation_name(client):
    response = client.get(
        url_string(
            query="""
        query TestQuery { test }
        mutation TestMutation { writeTest { test } }
        """
        )
    )

    assert response.status_code == 400
    expected_dict = {
        "errors": [
            {
                "message": "Must provide operation name if query contains multiple operations."
            }
        ]
    }
    # directly compare all key,value for __dict__
    assert response.json() == expected_dict


@pytest.mark.django_db
def test_errors_when_sending_a_mutation_via_get(client):
    response = client.get(
        url_string(
            query="""
        mutation TestMutation { writeTest { test } }
        """
        )
    )
    assert response.status_code == 405
    expected_dict = {
        "errors": [
            {"message": "Can only perform a mutation operation from a POST request."}
        ]
    }
    # directly compare all key,value for __dict__
    assert response.json() == expected_dict


@pytest.mark.django_db
def test_errors_when_selecting_a_mutation_within_a_get(client):
    response = client.get(
        url_string(
            query="""
        query TestQuery { test }
        mutation TestMutation { writeTest { test } }
        """,
            operationName="TestMutation",
        )
    )

    assert response.status_code == 405
    expected_dict = {
        "errors": [
            {"message": "Can only perform a mutation operation from a POST request."}
        ]
    }
    # directly compare all key,value for __dict__
    assert response.json() == expected_dict


@pytest.mark.django_db
def test_allows_mutation_to_exist_within_a_get(client):
    response = client.get(
        url_string(
            query="""
        query TestQuery { test }
        mutation TestMutation { writeTest { test } }
        """,
            operationName="TestQuery",
        )
    )

    assert response.status_code == 200
    # returns just json as __dict__
    expected_dict = {"data": {"test": "Hello World"}}
    # directly compare all key,value for __dict__
    assert response.json() == expected_dict


@pytest.mark.django_db
def test_allows_post_with_json_encoding(client):
    response = client.post(url_string(), j(query="{test}"), "application/json")

    assert response.status_code == 200
    # returns just json as __dict__
    expected_dict = {"data": {"test": "Hello World"}}
    # directly compare all key,value for __dict__
    assert response.json() == expected_dict


@pytest.mark.django_db
def test_batch_allows_post_with_json_encoding(client):
    response = client.post(
        batch_url_string(), jl(id=1, query="{test}"), "application/json"
    )

    assert response.status_code == 200
    # returns just json as __dict__
    expected_dict = [{"id": 1, "data": {"test": "Hello World"}, 'status': 200}]
    # directly compare all key,value for __dict__ -- NOTE responce is list of stuff!
    assert response.json() == expected_dict


@pytest.mark.django_db
def test_batch_fails_if_is_empty(client):
    response = client.post(batch_url_string(), "[]", "application/json")

    assert response.status_code == 400
    expected_dict = {
        "errors": [{"message": "Received an empty list in the batch request."}]
    }
    # directly compare all key,value for __dict__
    assert response.json() == expected_dict


@pytest.mark.django_db
def test_allows_sending_a_mutation_via_post(client):
    response = client.post(
        url_string(),
        j(query="mutation TestMutation { writeTest { test } }"),
        "application/json",
    )

    assert response.status_code == 200
    expected_dict = {"data": {"writeTest": {"test": "Hello World"}}}
    # directly compare all key,value for __dict__
    assert response.json() == expected_dict


'''
@pytest.mark.django_db
def test_allows_post_with_url_encoding(client):
    response = client.post(
        url_string(),
        urlencode(dict(query="{test}")),
        "application/x-www-form-urlencoded",
    )

    assert response.status_code == 200
    # returns just json as __dict__
    expected_dict = {"data": {"test": "Hello World"}}
    # directly compare all key,value for __dict__
    assert response.json() == expected_dict
'''


@pytest.mark.django_db
def test_supports_post_json_query_with_string_variables(client):
    response = client.post(
        url_string(),
        j(
            query="query helloWho($who: String){ test(who: $who) }",
            variables=json.dumps({"who": "Dolly"}),
        ),
        "application/json",
    )

    assert response.status_code == 200
    # returns just json as __dict__
    expected_dict = {"data": {"test": "Hello Dolly"}}
    # directly compare all key,value for __dict__
    assert response.json() == expected_dict


@pytest.mark.django_db
def test_batch_supports_post_json_query_with_string_variables(client):
    response = client.post(
        batch_url_string(),
        jl(
            id=1,
            query="query helloWho($who: String){ test(who: $who) }",
            variables=json.dumps({"who": "Dolly"}),
        ),
        "application/json",
    )

    assert response.status_code == 200
    # returns just json as __dict__
    expected_dict = {"id": 1, "data": {"test": "Hello Dolly"}, 'status': 200}
    # directly compare all key,value for __dict__ -- NOTE responce is list of stuff!
    assert response.json()[0] == expected_dict


@pytest.mark.django_db
def test_supports_post_json_query_with_json_variables(client):
    response = client.post(
        url_string(),
        j(
            query="query helloWho($who: String){ test(who: $who) }",
            variables={"who": "Dolly"},
        ),
        "application/json",
    )

    assert response.status_code == 200
    # returns just json as __dict__
    expected_dict = {"data": {"test": "Hello Dolly"}}
    # directly compare all key,value for __dict__
    assert response.json() == expected_dict


@pytest.mark.django_db
def test_batch_supports_post_json_query_with_json_variables(client):
    response = client.post(
        batch_url_string(),
        jl(
            id=1,
            query="query helloWho($who: String){ test(who: $who) }",
            variables={"who": "Dolly"},
        ),
        "application/json",
    )

    assert response.status_code == 200
    # returns just json as __dict__
    expected_dict = [
        {"id": 1, "data": {"test": "Hello Dolly"}, "status": 200}
    ]
    # directly compare all key,value for __dict__
    assert response.json() == expected_dict


'''
@pytest.mark.django_db
def test_supports_post_url_encoded_query_with_string_variables(client):
    response = client.post(
        url_string(),
        urlencode(
            dict(
                query="query helloWho($who: String){ test(who: $who) }",
                variables=json.dumps({"who": "Dolly"}),
            )
        ),
        "application/x-www-form-urlencoded",
    )

    assert response.status_code == 200
    # returns just json as __dict__
    expected_dict = {"data": {"test": "Hello Dolly"}}
    # directly compare all key,value for __dict__
    assert response.json() == expected_dict
'''


@pytest.mark.django_db
def test_supports_post_json_quey_with_get_variable_values(client):
    response = client.post(
        url_string(variables=json.dumps({"who": "Dolly"})),
        j(query="query helloWho($who: String){ test(who: $who) }"),
        "application/json",
    )

    assert response.status_code == 200
    # returns just json as __dict__
    expected_dict = {"data": {"test": "Hello Dolly"}}
    # directly compare all key,value for __dict__
    assert response.json() == expected_dict


'''
@pytest.mark.django_db
def test_post_url_encoded_query_with_get_variable_values(client):
    response = client.post(
        url_string(variables=json.dumps({"who": "Dolly"})),
        urlencode(dict(query="query helloWho($who: String){ test(who: $who) }")),
        "application/x-www-form-urlencoded",
    )

    assert response.status_code == 200
    # returns just json as __dict__
    expected_dict = {"data": {"test": "Hello Dolly"}}
    # directly compare all key,value for __dict__
    assert response.json() == expected_dict
'''


'''
@pytest.mark.django_db
def test_supports_post_raw_text_query_with_get_variable_values(client):
    response = client.post(
        url_string(variables=json.dumps({"who": "Dolly"})),
        "query helloWho($who: String){ test(who: $who) }",
        "application/graphql",
    )

    assert response.status_code == 200
    # returns just json as __dict__
    expected_dict = {"data": {"test": "Hello Dolly"}}
    # directly compare all key,value for __dict__
    assert response.json() == expected_dict
'''


@pytest.mark.django_db
def test_batch_allows_post_with_operation_name(client):
    response = client.post(
        batch_url_string(),
        jl(
            id=1,
            query="""
        query helloYou { test(who: "You"), ...shared }
        query helloWorld { test(who: "World"), ...shared }
        query helloDolly { test(who: "Dolly"), ...shared }
        fragment shared on QueryRoot {
          shared: test(who: "Everyone")
        }
        """,
            operationName="helloWorld",
        ),
        "application/json",
    )

    assert response.status_code == 200
    # returns just json as list of __dict__
    expected_dict = [
        {
            "id": 1,
            "data": {"test": "Hello World", "shared": "Hello Everyone"},
            "status": 200,
        }
    ]
    # directly compare all key,value for __dict__
    assert response.json() == expected_dict


'''
@pytest.mark.django_db
def test_allows_post_with_get_operation_name(client):
    response = client.post(
        url_string(operationName="helloWorld"),
        """
    query helloYou { test(who: "You"), ...shared }
    query helloWorld { test(who: "World"), ...shared }
    query helloDolly { test(who: "Dolly"), ...shared }
    fragment shared on QueryRoot {
      shared: test(who: "Everyone")
    }
    """,
        "application/graphql",
    )

    assert response.status_code == 200
    # returns just json as list of __dict__
    expected_dict = {
        "data": {"test": "Hello World", "shared": "Hello Everyone"}
    }
    # directly compare all key,value for __dict__
    assert response.json() == expected_dict
'''


'''
# inherited/ ???
@pytest.mark.django_db
@pytest.mark.urls("graphene_django.tests.urls_inherited")
def test_inherited_class_with_attributes_works(client):
    inherited_url = "/graphql/inherited/"
    # Check schema and pretty attributes work
    response = client.post(url_string(inherited_url, query="{test}"))
    assert response.status_code == 200
    # returns just json as list of __dict__
    expected_dict = (
        "{\n" '  "data": {\n' '    "test": "Hello World"\n' "  }\n" "}"
    )
    # directly compare all key,value for __dict__
    assert response.json() == expected_dict

    # Check graphiql works
    response = client.get(url_string(inherited_url), HTTP_ACCEPT="text/html")
    assert response.status_code == 200
'''


