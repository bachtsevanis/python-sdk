"""Session shutdown must not start a second HTTP response to a POST."""

import pytest
from starlette.types import Message

from mcp.server.streamable_http import StreamableHTTPServerTransport
from tests.server.test_streamable_http_router import _AsgiPost


@pytest.mark.anyio
@pytest.mark.parametrize(
    "body",
    [
        b'{"jsonrpc":"2.0","method":"notifications/initialized"}',
        b'{"jsonrpc":"2.0","id":1,"result":{}}',
        b'{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}',
    ],
)
@pytest.mark.parametrize("json_response", [True, False])
async def test_closed_writer_does_not_double_respond(body, json_response):
    transport = StreamableHTTPServerTransport(None, is_json_response_enabled=json_response)
    post = _AsgiPost(
        body, [(b"accept", b"application/json, text/event-stream"), (b"content-type", b"application/json")]
    )

    async def strict_send(message: Message):
        if message["type"] == "http.response.start":
            assert not any(m["type"] == "http.response.start" for m in post.sent)
        await post.send(message)

    async with transport.connect():
        await transport._read_stream_writer.aclose()
        await transport.handle_request(post.scope, post.receive, strict_send)
    starts = [m for m in post.sent if m["type"] == "http.response.start"]
    assert len(starts) == 1
