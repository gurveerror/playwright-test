"""
API tests for JSONPlaceholder POST /posts — boundary and invalid-input handling.

Target:    https://jsonplaceholder.typicode.com/posts
Objective: Confirm the API never fails server-side (5xx) on malformed or
           boundary input, and document what it actually does with each case.

Important context: JSONPlaceholder is a *fake* REST API for prototyping —
it does not persist data or enforce real validation rules. It will echo
back almost any payload with a generated id and a 201, even when fields
are missing, oversized, or the wrong type. These tests assert against
that real, documented behavior (no crash, response is well-formed) rather
than assuming 4xx responses that the service was never built to produce.

One genuine defect was found during testing: malformed JSON is not
rejected cleanly. It throws an unhandled body-parser exception that
surfaces as a raw 500 with a stack trace in the response body. That
case is marked xfail(strict=True) below so it's documented rather than
silently passed or silently broken.
"""
import logging
import pytest
from playwright.sync_api import sync_playwright, APIRequestContext

BASE_URL = "https://jsonplaceholder.typicode.com"
ENDPOINT = "/posts"

logger = logging.getLogger(__name__)


@pytest.fixture(scope="session")
def api_context():
    with sync_playwright() as p:
        ctx = p.request.new_context(base_url=BASE_URL)
        yield ctx
        ctx.dispose()


def assert_no_server_failure(response):
    assert response.status < 500, (
        f"Server-side failure: got {response.status} — {response.text()}"
    )


def log_response(test_name, payload, response):
    # There's no browser here to screenshot, so the log is the evidence
    # for this suite: request payload, status, and response body per case.
    logger.info(
        "%s | payload=%s | status=%s | response=%s",
        test_name, payload, response.status, response.text()[:500],
    )


class TestPostBoundaryAndInvalidData:

    def test_excessively_long_title(self, api_context: APIRequestContext):
        long_title = "A" * 100_000  # 100k chars — well beyond any realistic title
        payload = {"title": long_title, "body": "boundary test", "userId": 1}
        response = api_context.post(ENDPOINT, data=payload)
        log_response("test_excessively_long_title", {**payload, "title": f"<{len(long_title)} chars>"}, response)
        assert_no_server_failure(response)

        # Actual behavior: accepted and echoed back in full, uncapped.
        assert response.status == 201
        body = response.json()
        assert body.get("id") is not None
        assert len(body["title"]) == len(long_title)

    def test_unsupported_special_characters(self, api_context: APIRequestContext):
        weird_title = (
            "😀 emoji, SQLi: '; DROP TABLE posts;-- , "
            "XSS: <script>alert(1)</script>, null:\u0000, zero-width:\u200b"
        )
        payload = {"title": weird_title, "body": "special characters test", "userId": 1}
        response = api_context.post(ENDPOINT, data=payload)
        log_response("test_unsupported_special_characters", payload, response)
        assert_no_server_failure(response)

        # Actual behavior: accepted verbatim, no sanitization or rejection.
        assert response.status == 201
        body = response.json()
        assert body.get("id") is not None
        assert body.get("title") == weird_title

    def test_missing_required_field_userid(self, api_context: APIRequestContext):
        payload = {"title": "missing userId", "body": "boundary test"}
        response = api_context.post(ENDPOINT, data=payload)
        log_response("test_missing_required_field_userid", payload, response)
        assert_no_server_failure(response)

        # Actual behavior: no required-field enforcement — still 201.
        assert response.status == 201
        body = response.json()
        assert body.get("id") is not None
        assert "userId" not in body

    def test_missing_all_fields(self, api_context: APIRequestContext):
        response = api_context.post(ENDPOINT, data={})
        log_response("test_missing_all_fields", {}, response)
        assert_no_server_failure(response)

        assert response.status == 201
        body = response.json()
        assert body.get("id") is not None

    def test_wrong_data_types(self, api_context: APIRequestContext):
        payload = {
            "title": 12345,                # int instead of string
            "body": ["not", "a", "string"],  # array instead of string
            "userId": "not-an-int",        # string instead of int
        }
        response = api_context.post(ENDPOINT, data=payload)
        log_response("test_wrong_data_types", payload, response)
        assert_no_server_failure(response)

        # Actual behavior: no type coercion or rejection — passed straight through.
        assert response.status == 201

    @pytest.mark.xfail(
        reason=(
            "Discovered defect: malformed JSON is not caught by validation — "
            "it throws an unhandled body-parser SyntaxError that surfaces as a "
            "raw 500 with a stack trace in the response body, instead of a clean "
            "4xx. This is a real server-side failure, not a test bug."
        ),
        strict=True,
    )
    def test_malformed_json_body(self, api_context: APIRequestContext):
        # Genuinely broken JSON. Per the API's stated contract this should be a
        # clean 4xx before it ever reaches app logic — see xfail reason above
        # for what actually happens.
        response = api_context.post(
            ENDPOINT,
            data="{ this is not valid json",
            headers={"Content-Type": "application/json"},
        )
        log_response("test_malformed_json_body", "{ this is not valid json", response)
        assert_no_server_failure(response)
        assert 400 <= response.status < 500, (
            f"Expected a 4xx for unparsable JSON, got {response.status}"
        )
