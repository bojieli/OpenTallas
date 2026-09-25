"""A small Liberty reader: the cell-level facts DFT needs.

It keeps, per cell, the area, each pin's direction and function, and the
``ff`` / ``latch`` group of a sequential cell (state variables, clock or
enable, next state or data, clear and preset).  Functions are parsed into
expression trees that the scan inserter, the ATPG model builder and the
gate-level model writer all share, so the three agree on what a cell computes
by construction.

Expression trees are tuples:

    ("var", name) | ("const", 0|1) | ("not", e) | ("and", [e...])
    | ("or", [e...]) | ("xor", a, b)
"""

from __future__ import annotations

import gzip
import hashlib
import json
import re
from pathlib import Path
from typing import Any

# --------------------------------------------------------------------------
# Boolean expressions
# --------------------------------------------------------------------------

_EXPR_TOKEN = re.compile(r"\s*(?:(?P<id>[A-Za-z_][A-Za-z0-9_\[\]\.]*)|(?P<num>[01])|(?P<op>[!'*&+|^()]))")


def parse_function(text: str) -> tuple:
    """Parse a Liberty function string.

    Precedence, highest first: postfix ``'`` and prefix ``!``, then ``^``,
    then AND (``*``, ``&`` or juxtaposition), then OR (``+`` or ``|``).
    """
    tokens: list[tuple[str, str]] = []
    pos = 0
    text = text.strip()
    while pos < len(text):
        m = _EXPR_TOKEN.match(text, pos)
        if not m or m.end() == pos:
            if text[pos:].strip() == "":
                break
            raise ValueError(f"cannot tokenise liberty function {text!r} at {pos}")
        pos = m.end()
        if m.group("id"):
            tokens.append(("id", m.group("id")))
        elif m.group("num"):
            tokens.append(("num", m.group("num")))
        else:
            tokens.append(("op", m.group("op")))
    index = 0

    def peek() -> tuple[str, str] | None:
        return tokens[index] if index < len(tokens) else None

    def take() -> tuple[str, str]:
        nonlocal index
        tok = tokens[index]
        index += 1
        return tok

    def parse_or() -> tuple:
        terms = [parse_and()]
        while peek() in (("op", "+"), ("op", "|")):
            take()
            terms.append(parse_and())
        return terms[0] if len(terms) == 1 else ("or", terms)

    def starts_primary(tok: tuple[str, str] | None) -> bool:
        return tok is not None and (tok[0] in ("id", "num") or tok in (("op", "("), ("op", "!")))

    def parse_and() -> tuple:
        terms = [parse_xor()]
        while True:
            tok = peek()
            if tok in (("op", "*"), ("op", "&")):
                take()
                terms.append(parse_xor())
            elif starts_primary(tok):  # juxtaposition
                terms.append(parse_xor())
            else:
                break
        return terms[0] if len(terms) == 1 else ("and", terms)

    def parse_xor() -> tuple:
        left = parse_unary()
        while peek() == ("op", "^"):
            take()
            left = ("xor", left, parse_unary())
        return left

    def parse_unary() -> tuple:
        tok = peek()
        if tok == ("op", "!"):
            take()
            node = ("not", parse_unary())
        else:
            node = parse_primary()
        while peek() == ("op", "'"):
            take()
            node = ("not", node)
        return node

    def parse_primary() -> tuple:
        tok = take()
        if tok == ("op", "("):
            node = parse_or()
            if take() != ("op", ")"):
                raise ValueError(f"unbalanced parentheses in {text!r}")
            return node
        if tok[0] == "num":
            return ("const", int(tok[1]))
        if tok[0] == "id":
            return ("var", tok[1])
        raise ValueError(f"unexpected token {tok} in {text!r}")

    result = parse_or()
    if index != len(tokens):
        raise ValueError(f"trailing tokens in liberty function {text!r}")
    return result


def expr_vars(expr: tuple) -> set[str]:
    kind = expr[0]
    if kind == "var":
        return {expr[1]}
    if kind == "const":
        return set()
    if kind == "not":
        return expr_vars(expr[1])
    if kind in ("and", "or"):
        out: set[str] = set()
        for term in expr[1]:
            out |= expr_vars(term)
        return out
    if kind == "xor":
        return expr_vars(expr[1]) | expr_vars(expr[2])
    raise ValueError(kind)


def evaluate(expr: tuple, env: dict[str, int]) -> int:
    kind = expr[0]
    if kind == "var":
        return env[expr[1]]
    if kind == "const":
        return expr[1]
    if kind == "not":
        return 1 - evaluate(expr[1], env)
    if kind == "and":
        return int(all(evaluate(t, env) for t in expr[1]))
    if kind == "or":
        return int(any(evaluate(t, env) for t in expr[1]))
    if kind == "xor":
        return evaluate(expr[1], env) ^ evaluate(expr[2], env)
    raise ValueError(kind)


def substitute(expr: tuple, values: dict[str, int]) -> tuple:
    """Replace named variables by constants (no simplification)."""
    kind = expr[0]
    if kind == "var":
        return ("const", values[expr[1]]) if expr[1] in values else expr
    if kind == "const":
        return expr
    if kind == "not":
        return ("not", substitute(expr[1], values))
    if kind in ("and", "or"):
        return (kind, [substitute(t, values) for t in expr[1]])
    if kind == "xor":
        return ("xor", substitute(expr[1], values), substitute(expr[2], values))
    raise ValueError(kind)


def to_verilog(expr: tuple, rename: dict[str, str] | None = None) -> str:
    rename = rename or {}
    kind = expr[0]
    if kind == "var":
        return rename.get(expr[1], expr[1])
    if kind == "const":
        return f"1'b{expr[1]}"
    if kind == "not":
        return f"(~{to_verilog(expr[1], rename)})"
    if kind == "and":
        return "(" + " & ".join(to_verilog(t, rename) for t in expr[1]) + ")"
    if kind == "or":
        return "(" + " | ".join(to_verilog(t, rename) for t in expr[1]) + ")"
    if kind == "xor":
        return f"({to_verilog(expr[1], rename)} ^ {to_verilog(expr[2], rename)})"
    raise ValueError(kind)


def truth_table(expr: tuple, names: list[str]) -> int:
    """The function as an integer bitmask over all assignments of ``names``."""
    mask = 0
    for row in range(1 << len(names)):
        env = {n: (row >> i) & 1 for i, n in enumerate(names)}
        if evaluate(expr, env):
            mask |= 1 << row
    return mask


# --------------------------------------------------------------------------
# Liberty files
# --------------------------------------------------------------------------

_LIB_TOKEN = re.compile(
    r'\n|[ \t\r]+|/\*.*?\*/|"(?:[^"\\]|\\.)*"|\\\r?\n|[{}();:,]|[^\s{}();:,"]+', re.S
)


def _tokens(text: str):
    for m in _LIB_TOKEN.finditer(text):
        tok = m.group(0)
        if tok == "\n":
            yield "\n"
            continue
        if tok.isspace() or tok.startswith("/*") or tok.startswith("\\"):
            continue
        yield tok


def _parse_groups(text: str) -> dict[str, Any]:
    """Parse into nested dicts: {"attrs": {...}, "groups": [(name, args, body)]}."""
    raw = list(_tokens(text))
    # Newlines matter only as the terminator of a simple attribute that has
    # no semicolon; keep them as markers attached to the preceding token.
    toks: list[str] = []
    ends_line: list[bool] = []
    for tok in raw:
        if tok == "\n":
            if ends_line:
                ends_line[-1] = True
            continue
        toks.append(tok)
        ends_line.append(False)
    i = 0

    def parse_body() -> dict[str, Any]:
        nonlocal i
        body: dict[str, Any] = {"attrs": {}, "groups": []}
        while i < len(toks):
            tok = toks[i]
            if tok == "}":
                i += 1
                return body
            name = tok
            i += 1
            if i < len(toks) and toks[i] == ":":
                i += 1
                value_parts = []
                while toks[i] not in (";", "}"):
                    value_parts.append(toks[i])
                    i += 1
                    if ends_line[i - 1]:
                        break
                if toks[i] == ";":
                    i += 1
                value = " ".join(value_parts)
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                body["attrs"][name] = value
            elif i < len(toks) and toks[i] == "(":
                i += 1
                args = []
                while toks[i] != ")":
                    if toks[i] != ",":
                        arg = toks[i]
                        if arg.startswith('"') and arg.endswith('"'):
                            arg = arg[1:-1]
                        args.append(arg)
                    i += 1
                i += 1
                if i < len(toks) and toks[i] == "{":
                    i += 1
                    sub = parse_body()
                    body["groups"].append((name, args, sub))
                elif i < len(toks) and toks[i] == ";":
                    i += 1
                    body["attrs"].setdefault(name, args)
            else:
                # stray token (e.g. a bare ';')
                continue
        return body

    root = parse_body()
    return root


def _read_text(path: Path) -> str:
    data = path.read_bytes()
    if path.suffix == ".gz":
        data = gzip.decompress(data)
    return data.decode("utf-8", errors="replace")


# Groups under a cell that can be skipped wholesale: timing and power tables
# are most of the file and none of them matters to logic.
_SKIP_CELL_GROUPS = {"timing", "internal_power", "leakage_power", "pg_pin"}


def _strip_heavy(text: str) -> str:
    """Remove timing/power groups textually before tokenising (speed)."""
    out = []
    depth_skip = 0
    pos = 0
    pattern = re.compile(r"\b(timing|internal_power|leakage_power|output_current_rise|output_current_fall|receiver_capacitance)\s*\([^)]*\)\s*\{")
    while True:
        m = pattern.search(text, pos)
        if not m:
            out.append(text[pos:])
            break
        out.append(text[pos:m.start()])
        depth = 1
        j = m.end()
        while depth and j < len(text):
            c = text[j]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
            j += 1
        pos = j
    del depth_skip
    return "".join(out)


def read_liberty(paths: list[Path]) -> dict[str, dict[str, Any]]:
    """Return {cell_name: cell_record} over every file in ``paths``."""
    cells: dict[str, dict[str, Any]] = {}
    for path in paths:
        text = _strip_heavy(_read_text(Path(path)))
        root = _parse_groups(text)
        for gname, _gargs, library in root["groups"]:
            if gname != "library":
                continue
            for cname, cargs, cbody in library["groups"]:
                if cname != "cell":
                    continue
                cells[cargs[0]] = _cell_record(cargs[0], cbody)
    return cells


def _cell_record(name: str, body: dict[str, Any]) -> dict[str, Any]:
    rec: dict[str, Any] = {
        "name": name,
        "area": float(body["attrs"].get("area", 0.0)),
        "pins": {},
        "ff": None,
        "latch": None,
    }
    for gname, gargs, gbody in body["groups"]:
        if gname == "pin":
            attrs = gbody["attrs"]
            rec["pins"][gargs[0]] = {
                "direction": attrs.get("direction"),
                "function": attrs.get("function"),
                "clock": attrs.get("clock") == "true",
            }
        elif gname in ("ff", "latch"):
            attrs = gbody["attrs"]
            rec[gname] = {
                "vars": list(gargs),
                **{k: attrs[k] for k in (
                    "clocked_on", "next_state", "enable", "data_in", "clear", "preset",
                    "clear_preset_var1", "clear_preset_var2",
                ) if k in attrs},
            }
    return rec


_CACHE_VERSION = 2


def load_cells(paths: list[Path], cache_dir: Path | None = None) -> dict[str, dict[str, Any]]:
    """``read_liberty`` with an on-disk JSON cache keyed by the files' digests."""
    digest = hashlib.sha256()
    digest.update(str(_CACHE_VERSION).encode())
    for path in paths:
        digest.update(hashlib.sha256(Path(path).read_bytes()).digest())
    key = digest.hexdigest()[:24]
    if cache_dir is not None:
        cache = Path(cache_dir) / f"liberty_cells_{key}.json"
        if cache.is_file():
            return json.loads(cache.read_text())
    cells = read_liberty(paths)
    if cache_dir is not None:
        Path(cache_dir).mkdir(parents=True, exist_ok=True)
        tmp = cache.with_suffix(".tmp")
        tmp.write_text(json.dumps(cells, sort_keys=True))
        tmp.replace(cache)
    return cells


def default_asap7_liberty() -> list[Path]:
    import os

    root = Path(os.environ.get("OPENTALLAS_PDK_ASAP7_ROOT", Path.home() / ".local/opentallas-pdk-asap7"))
    nldm = root / "lib/NLDM"
    return [
        nldm / "asap7sc7p5t_AO_RVT_TT_nldm_211120.lib",
        nldm / "asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib",
        nldm / "asap7sc7p5t_OA_RVT_TT_nldm_211120.lib",
        nldm / "asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib",
        nldm / "asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib",
    ]


def cell_outputs(cell: dict[str, Any]) -> list[str]:
    return [p for p, info in cell["pins"].items() if info["direction"] == "output"]


def cell_inputs(cell: dict[str, Any]) -> list[str]:
    return [p for p, info in cell["pins"].items() if info["direction"] == "input"]
