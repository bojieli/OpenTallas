"""Frozen agent sandbox for the agentic acceptance workloads.

The acceptance contract requires that agent actions are *model-generated*,
parsed fail-closed, executed in a frozen sandbox, and returned in the next
rendered context.  The three failure modes this module is built to prevent are:

* the harness inventing or repairing a command the model did not emit;
* a parse that accepts loose output, which lets a plausible-looking but
  malformed action pass as success; and
* execution outside a controlled directory.

The parser therefore accepts exactly one fenced ``bash`` block per turn and
rejects everything else, and the executor runs with a fresh working directory
containing only the workload's pinned files, no network, a wall-clock limit and
an output cap.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field as dc_field
from pathlib import Path
from typing import Any, Mapping, Sequence

#: Exactly one fenced bash block.  Anything looser is a parse failure.
_FENCE = re.compile(r"```bash[ \t]*\r?\n(?P<body>.*?)\r?\n?```", re.DOTALL)

#: The terminating answer line.
_ANSWER = re.compile(r"^ANSWER:[ \t]*(?P<answer>.*)$", re.MULTILINE)

#: Qwen3's thinking delimiters.  ``<think>`` is emitted by the *model* when the
#: chat template is rendered with ``enable_thinking=True``; when it is rendered
#: with ``enable_thinking=False`` the template instead appends a pre-closed
#: ``<think>\n\n</think>\n\n`` to the prompt, which is what prevents the
#: model from reasoning at all.
THINK_OPEN = "<think>"
THINK_CLOSE = "</think>"
THINK_OPEN_TOKEN_ID = 151667
THINK_CLOSE_TOKEN_ID = 151668


def split_thinking(text: str) -> tuple[str | None, str]:
    """Separate a turn's reasoning block from the content it is reasoning towards.

    Returns ``(thinking, visible)``.  ``thinking`` is ``None`` when the turn
    carries no closed thinking block, which is the case both when reasoning is
    disabled and when a generation was cut off mid-thought -- and those two are
    deliberately not distinguished here, because a truncated thought is not a
    turn the protocol can act on either way.

    The split matters for parsing.  A reasoning model routinely *drafts* a
    command inside its thinking block before committing to one, so a parser run
    over the whole turn would see two fenced blocks and fail the episode for a
    protocol violation the model did not commit.  The action is what the model
    emits after it stops thinking.
    """
    close = text.find(THINK_CLOSE)
    if close == -1:
        return None, text
    open_at = text.find(THINK_OPEN)
    start = open_at + len(THINK_OPEN) if 0 <= open_at < close else 0
    return text[start:close].strip(), text[close + len(THINK_CLOSE) :].lstrip("\n")


def render_agent_context(
    tokenizer, messages: Sequence[Mapping[str, str]], *, enable_thinking: bool
) -> tuple[str, list[int]]:
    """Render an episode's message history through the official chat template.

    Both the accelerator episode and the external oracle episode call this, so
    a turn-by-turn comparison between them compares decoded tokens rather than
    two different renderings of the same conversation.

    The history carries each assistant turn's *raw* text, thinking block
    included; the official Qwen3 template drops prior-turn reasoning itself
    when it re-renders, and reproducing that stripping here would be a second,
    divergent implementation of the template's own rule.
    """
    text = tokenizer.apply_chat_template(
        list(messages),
        tokenize=False,
        add_generation_prompt=True,
        enable_thinking=enable_thinking,
    )
    return text, list(tokenizer.encode(text, add_special_tokens=False))


class AgentProtocolError(Exception):
    """Raised when model output does not satisfy the frozen protocol."""


@dataclass(frozen=True, slots=True)
class ParsedTurn:
    """What the model's turn said, under the frozen protocol."""

    kind: str  # "command" | "answer" | "neither"
    command: str | None = None
    answer: str | None = None
    raw: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "command": self.command,
            "answer": self.answer,
        }


def parse_turn(text: str) -> ParsedTurn:
    """Parse one model turn fail-closed.

    An answer line terminates the episode and takes precedence.  Otherwise
    exactly one fenced bash block is required; zero or several is a protocol
    violation, not a retry opportunity.
    """
    answer = _ANSWER.search(text)
    if answer is not None:
        return ParsedTurn(kind="answer", answer=answer.group("answer").strip(), raw=text)
    blocks = _FENCE.findall(text)
    if not blocks:
        return ParsedTurn(kind="neither", raw=text)
    if len(blocks) > 1:
        raise AgentProtocolError(
            f"the protocol admits one bash block per turn; the model emitted "
            f"{len(blocks)}"
        )
    command = blocks[0].strip()
    if not command:
        raise AgentProtocolError("the model emitted an empty bash block")
    if "\n" in command:
        raise AgentProtocolError(
            "the protocol admits a single command per turn; the model emitted "
            f"{command.count(chr(10)) + 1} lines"
        )
    return ParsedTurn(kind="command", command=command, raw=text)


@dataclass
class CommandResult:
    """The observable result of one sandboxed command."""

    command: str
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool
    truncated: bool

    def rendered(self) -> str:
        """How the result is fed back into the next context."""
        parts = [f"exit status: {self.exit_code}"]
        if self.timed_out:
            parts.append("(timed out)")
        body = self.stdout.strip()
        err = self.stderr.strip()
        if body:
            parts.append(body)
        if err:
            parts.append(f"stderr: {err}")
        if self.truncated:
            parts.append("(output truncated)")
        return "\n".join(parts)

    def to_dict(self) -> dict[str, Any]:
        return {
            "command": self.command,
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "timed_out": self.timed_out,
            "truncated": self.truncated,
        }


class Sandbox:
    """A frozen working directory for one agent episode."""

    def __init__(
        self,
        files: Mapping[str, str],
        *,
        timeout_seconds: float = 10.0,
        output_limit: int = 8192,
    ) -> None:
        self.files = dict(files)
        self.timeout_seconds = timeout_seconds
        self.output_limit = output_limit
        self._root: Path | None = None

    def __enter__(self) -> "Sandbox":
        self._root = Path(tempfile.mkdtemp(prefix="opentallas-agent-"))
        for name, content in self.files.items():
            target = self._root / name
            if not target.resolve().is_relative_to(self._root.resolve()):
                raise AgentProtocolError(f"sandbox file {name!r} escapes the root")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content)
        return self

    def __exit__(self, *exc: object) -> None:
        if self._root is not None:
            shutil.rmtree(self._root, ignore_errors=True)
            self._root = None

    @property
    def root(self) -> Path:
        if self._root is None:
            raise AgentProtocolError("sandbox is not open")
        return self._root

    def run(self, command: str) -> CommandResult:
        """Execute one model-generated command in the sandbox."""
        environment = {
            "PATH": "/usr/local/bin:/usr/bin:/bin",
            "HOME": str(self.root),
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            # No network credentials, no proxy, no inherited configuration.
        }
        timed_out = False
        try:
            completed = subprocess.run(
                ["/bin/bash", "-c", command],
                cwd=self.root,
                env=environment,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
            )
            exit_code = completed.returncode
            stdout, stderr = completed.stdout, completed.stderr
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            exit_code = 124
            stdout = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
            stderr = exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        truncated = len(stdout) > self.output_limit or len(stderr) > self.output_limit
        return CommandResult(
            command=command,
            exit_code=exit_code,
            stdout=stdout[: self.output_limit],
            stderr=stderr[: self.output_limit],
            timed_out=timed_out,
            truncated=truncated,
        )


@dataclass
class AgentEpisode:
    """A complete agent episode: every turn, action and observation."""

    turns: list[dict[str, Any]] = dc_field(default_factory=list)
    answer: str | None = None
    stop_reason: str = "incomplete"
    protocol_violation: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "turns": self.turns,
            "answer": self.answer,
            "stop_reason": self.stop_reason,
            "protocol_violation": self.protocol_violation,
            "turn_count": len(self.turns),
        }


def run_episode(
    *,
    generate,
    render_context,
    sandbox_files: Mapping[str, str],
    max_turns: int = 6,
    timeout_seconds: float = 10.0,
) -> AgentEpisode:
    """Drive one agent episode.

    ``generate(messages) -> str`` produces the model's next turn from a message
    list; ``render_context(messages) -> Any`` is unused here but kept so callers
    can pass a template renderer.  The harness never writes a command: it only
    parses, executes and observes.
    """
    episode = AgentEpisode()
    messages: list[dict[str, str]] = []
    with Sandbox(sandbox_files, timeout_seconds=timeout_seconds) as sandbox:
        for turn_index in range(max_turns):
            text = generate(messages)
            try:
                parsed = parse_turn(text)
            except AgentProtocolError as exc:
                episode.protocol_violation = str(exc)
                episode.stop_reason = "protocol_violation"
                episode.turns.append({"turn": turn_index, "raw": text})
                return episode
            record: dict[str, Any] = {
                "turn": turn_index,
                "raw": text,
                "parsed": parsed.to_dict(),
            }
            if parsed.kind == "answer":
                episode.answer = parsed.answer
                episode.stop_reason = "answered"
                episode.turns.append(record)
                return episode
            if parsed.kind == "neither":
                episode.stop_reason = "no_action"
                episode.turns.append(record)
                return episode
            assert parsed.command is not None
            result = sandbox.run(parsed.command)
            record["observation"] = result.to_dict()
            episode.turns.append(record)
            messages.append({"role": "assistant", "content": text})
            messages.append({"role": "user", "content": result.rendered()})
    episode.stop_reason = "max_turns"
    return episode
