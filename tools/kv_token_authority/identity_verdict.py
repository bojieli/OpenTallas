"""Verification-only source identity ledger and application verdict checks.

Authority is supplied by the independently checked source/relay knowledge tags,
never by trace_on, A0, a deadline or a count of observed STATUS records.
This module does not establish source startup safety or change DUT semantics.
"""
from dataclasses import dataclass, field
import argparse
import json
import re
from pathlib import Path


@dataclass(frozen=True, order=True)
class Identity:
    epoch: int
    layer: int
    position: int
    token: int

    def __post_init__(self):
        if any(type(v) is not int or v < 0 for v in
               (self.epoch, self.layer, self.position, self.token)):
            raise ValueError("identity fields must be explicit nonnegative integers")


@dataclass
class Request:
    beats: int
    running: bool = False
    source_done: bool = False
    bitmap: set = field(default_factory=set)
    terminal: bool = False
    successful: bool = False


class Scoreboard:
    def __init__(self, programme, *, require_retire=True):
        entries = list(programme)
        if (not entries or any(not isinstance(i, Identity) for i in entries)
                or len(entries) != len(set(entries))):
            raise ValueError("programme must contain unique explicit identities")
        self.programme = set(entries)
        self.require_retire = require_retire
        self.requests = {}
        self.errors = []
        self.raw = []
        self.raw_status_count = 0
        self.successful_count = 0

    def error(self, message):
        self.errors.append(message)
        return False

    def accept(self, identity, result_beats, *, monitors_known):
        # Called only for actual source command acceptance, not scheduled A0.
        if monitors_known is not True:
            return self.error("admission before required monitor authority")
        if identity not in self.programme:
            return self.error("accepted identity absent from programme")
        if identity in self.requests:
            return self.error("duplicate acceptance")
        if type(result_beats) is not int or result_beats < 1:
            return self.error("invalid RESULT beat count")
        self.requests[identity] = Request(result_beats)
        return True

    def run(self, identity, *, run_ok):
        req = self.requests.get(identity)
        if req is None or req.running or req.terminal or run_ok is not True:
            return self.error("unowned, duplicate or failed source run")
        req.running = True
        return True

    def _active(self, identity):
        req = self.requests.get(identity)
        if req is None or not req.running or req.terminal:
            self.error("record has no active source-owned identity")
            return None
        return req

    def result(self, identity, beat):
        req = self._active(identity)
        if req is None:
            return False
        if type(beat) is not int or beat != len(req.bitmap) or beat >= req.beats:
            return self.error("wrong, duplicate or unordered RESULT beat")
        req.bitmap.add(beat)
        return True

    def source_complete(self, identity):
        req = self._active(identity)
        if req is None:
            return False
        if req.source_done:
            return self.error("duplicate source completion")
        req.source_done = True
        return True

    def status(self, identity, *, success=True, payload_valid=True):
        req = self._active(identity)
        if req is None:
            return False
        if payload_valid is not True or type(success) is not bool:
            return self.error("malformed STATUS payload")
        if success and (not req.source_done or len(req.bitmap) != req.beats):
            return self.error("STATUS before source completion and required RESULTs")
        # A valid error STATUS can terminate an owned request without successful
        # completion. No fallback to the next expected programme identity exists.
        req.terminal = True
        req.successful = success
        if success:
            self.successful_count += 1
        else:
            self.error("source-owned error STATUS")
        return True

    def observe_status(self, *, authoritative, valid, identity=None,
                       success=True, payload_valid=True, trace_on=False):
        self.raw.append(dict(kind="STATUS", authoritative=authoritative,
                             valid=valid, identity=identity, trace_on=trace_on))
        if valid is True:
            self.raw_status_count += 1
        if authoritative is not True:
            return False
        if type(valid) is not bool:
            return self.error("unknown STATUS valid after authority")
        if not valid:
            return False
        return self.status(identity, success=success, payload_valid=payload_valid)

    def finish(self):
        executed = (set(self.requests) == self.programme and
                    all(req.running for req in self.requests.values()))
        if not executed:
            self.error("PROGRAMME_EXECUTED missing actual acceptance/run")
        if self.require_retire and self.successful_count != len(self.programme):
            self.error("programme lacks exactly one successful retirement per identity")
        return not self.errors


def parse_verdict(text, returncode):
    """Require one unambiguous application PASS as well as process success."""
    tokens = re.findall(r"(?<![A-Za-z0-9_])SMOKE_(PASS|FAIL)(?![A-Za-z0-9_])", text)
    if returncode != 0:
        return False, "nonzero process return code"
    if tokens != ["PASS"]:
        return False, "expected exactly one SMOKE_PASS and no SMOKE_FAIL"
    return True, "SMOKE_PASS with process return code zero"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path)
    parser.add_argument("--returncode", required=True, type=int)
    args = parser.parse_args()
    passed, reason = parse_verdict(args.log.read_text(), args.returncode)
    print(json.dumps({"application_pass": passed, "reason": reason}))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
