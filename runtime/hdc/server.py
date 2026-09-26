"""OpenAI-compatible HTTP endpoint in front of the simulated chips.

Routes (the subset of the OpenAI API a completion client needs):

* ``GET  /v1/models``            the loaded targets, one model id each
* ``POST /v1/completions``       ``prompt`` as text or token ids
* ``POST /v1/chat/completions``  ``messages`` rendered with the model's chat template
* ``GET  /v1/counters``          the chips' counters (OpenTallas extension)

``stream: true`` answers as server-sent events (``data: {chunk}`` lines, then
``data: [DONE]``); each chunk carries the text of one token the chip wrote to
its completion ring.  The chips decode greedily and bit-exactly, so a request
asking for sampling (``temperature`` > 0, ``top_p`` < 1, ``n`` > 1) is
refused rather than silently served greedily.  Every response carries an
``opentallas`` object: the target, token ids, chip cycles and the modelled
time and tokens/s at the target's clock.

Model ids are ``<model>@<target>`` (``qwen3-reduced-v1@qwen3-rom``); the
bare target name and, when only one target is loaded, any name also select.
"""

from __future__ import annotations

import json
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from runtime.hdc.runtime import HdcRuntime
from runtime.hdc.tokenizer import ModelTokenizer


class Backend:
    def __init__(self, runtime: HdcRuntime):
        self.rt = runtime
        self.tok = ModelTokenizer(runtime.target)
        self.model_id = f"{runtime.target.model_id}@{runtime.target.name}"


class Api:
    def __init__(self, backends: list[Backend], default_max_tokens: int = 16):
        self.backends = backends
        self.default_max_tokens = default_max_tokens

    def pick(self, name: str | None) -> Backend:
        for b in self.backends:
            if name in (b.model_id, b.rt.target.name, b.rt.target.model_id):
                return b
        if len(self.backends) == 1:
            return self.backends[0]
        raise LookupError(f"unknown model {name!r}; loaded: {[b.model_id for b in self.backends]}")


def _error(status: int, message: str, kind: str = "invalid_request_error") -> tuple[int, dict]:
    return status, {"error": {"message": message, "type": kind}}


def make_handler(api: Api):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, fmt, *args):      # quiet
            pass

        def _json(self, status: int, body: dict) -> None:
            data = json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if self.path.rstrip("/") == "/v1/models":
                return self._json(200, {"object": "list", "data": [
                    {"id": b.model_id, "object": "model", "owned_by": "opentallas",
                     "architecture": b.rt.target.architecture, "target": b.rt.target.name}
                    for b in api.backends]})
            if self.path.rstrip("/") == "/v1/counters":
                return self._json(200, {b.model_id: b.rt.counters() for b in api.backends})
            if self.path.rstrip("/") in ("", "/health"):
                return self._json(200, {"status": "ok"})
            self._json(*_error(404, f"no route {self.path}"))

        def do_POST(self):
            try:
                n = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(n) or b"{}")
            except (ValueError, json.JSONDecodeError):
                return self._json(*_error(400, "body is not JSON"))
            route = self.path.rstrip("/")
            if route not in ("/v1/completions", "/v1/chat/completions"):
                return self._json(*_error(404, f"no route {self.path}"))
            chat = route.endswith("chat/completions")
            try:
                b = api.pick(body.get("model"))
            except LookupError as e:
                return self._json(*_error(404, str(e), "model_not_found"))
            temp, top_p, n_choices = body.get("temperature"), body.get("top_p"), body.get("n", 1)
            if (temp not in (None, 0, 0.0)) or (top_p not in (None, 1, 1.0)) or n_choices != 1:
                return self._json(*_error(400, "the chip decodes greedily (bit-exact argmax): "
                                               "temperature must be 0, top_p 1 and n 1"))
            try:
                if chat:
                    msgs = body.get("messages") or []
                    ids = b.tok.encode_chat([{"role": m["role"], "content": _text(m.get("content"))} for m in msgs])
                else:
                    p = body.get("prompt", "")
                    if isinstance(p, list) and len(p) == 1 and isinstance(p[0], (str, list)):
                        p = p[0]
                    ids = [int(x) % b.rt.target.vocab for x in p] if isinstance(p, list) else b.tok.encode(p)
                max_new = int(body.get("max_completion_tokens") or body.get("max_tokens") or api.default_max_tokens)
                req = b.rt.submit(ids, max_new, stop_eos=not body.get("ignore_eos", False))
            except (ValueError, KeyError, TypeError) as e:
                return self._json(*_error(400, str(e)))
            rid = ("chatcmpl-" if chat else "cmpl-") + uuid.uuid4().hex[:24]
            created = int(time.time())
            if body.get("stream"):
                return self._stream(b, req, rid, created, chat, body)
            req.result()
            text = b.tok.decode(req.tokens_out)
            finish = _finish(req)
            choice = ({"index": 0, "message": {"role": "assistant", "content": text}, "finish_reason": finish}
                      if chat else {"index": 0, "text": text, "logprobs": None, "finish_reason": finish})
            self._json(200, {"id": rid, "object": "chat.completion" if chat else "text_completion",
                             "created": created, "model": b.model_id, "choices": [choice],
                             "usage": _usage(req), "opentallas": b.rt.request_stats(req)})

        def _stream(self, b: Backend, req, rid, created, chat, body):
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "close")
            self.end_headers()
            obj = "chat.completion.chunk" if chat else "text_completion"

            def send(payload):
                self.wfile.write(b"data: " + json.dumps(payload).encode() + b"\n\n")
                self.wfile.flush()

            def chunk(delta_text, finish=None, first=False, extra=None):
                if chat:
                    delta = {"role": "assistant", "content": delta_text} if first else (
                        {"content": delta_text} if delta_text else {})
                    c = {"index": 0, "delta": delta, "finish_reason": finish}
                else:
                    c = {"index": 0, "text": delta_text, "logprobs": None, "finish_reason": finish}
                p = {"id": rid, "object": obj, "created": created, "model": b.model_id, "choices": [c]}
                if extra:
                    p.update(extra)
                return p

            ids, sent = [], ""
            if chat:
                send(chunk("", first=True))
            for t in req.tokens():
                ids.append(t)
                text = b.tok.decode(ids)
                if text.endswith("�"):           # an incomplete UTF-8 sequence: wait for the next token
                    continue
                delta, sent = text[len(sent):], text
                send(chunk(delta, extra={"opentallas": {"token_id": t}}))
            req.result()
            extra = {"usage": _usage(req), "opentallas": b.rt.request_stats(req)}
            send(chunk("", finish=_finish(req), extra=extra))
            self.wfile.write(b"data: [DONE]\n\n")
            self.wfile.flush()
            self.close_connection = True

    return Handler


def _text(content) -> str:
    if isinstance(content, list):                     # [{"type": "text", "text": ...}]
        return "".join(p.get("text", "") for p in content if isinstance(p, dict))
    return content or ""


def _finish(req) -> str:
    return "stop" if req.status == "eos" else "length" if req.status == "length" else f"error:{req.status}"


def _usage(req) -> dict:
    return {"prompt_tokens": len(req.prompt), "completion_tokens": len(req.tokens_out),
            "total_tokens": len(req.prompt) + len(req.tokens_out)}


def serve(runtimes: list[HdcRuntime], host: str = "127.0.0.1", port: int = 8000,
          default_max_tokens: int = 16) -> ThreadingHTTPServer:
    """Start the endpoint in a background thread; returns the server (``.shutdown()`` stops it)."""
    api = Api([Backend(r) for r in runtimes], default_max_tokens)
    httpd = ThreadingHTTPServer((host, port), make_handler(api))
    httpd.daemon_threads = True
    threading.Thread(target=httpd.serve_forever, name="hdc-http", daemon=True).start()
    return httpd
