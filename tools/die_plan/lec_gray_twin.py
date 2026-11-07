"""GRAY-MSB TWIN LEC hints, staged by every core/type kit generator (KW-FIX-24, COORD 11-06 21:2x (5)).

Class (DIE-S81-51 11-03 07:50 (b); DIE-HBM-82-RF 11-06 21:00): a gray-pointer FIFO (ot_s81_rate_match and its
copies) keeps a binary pointer P and its gray copy P_g, both written in the same branch

    P <= P + 1'b1;  P_g <= (P + 1'b1) ^ ((P + 1'b1) >> 1);

with the same reset 0.  The gray MSB IS the binary MSB, so P[msb] and P_g[msb] have the same next state and the
same reset: yosys opt_merge keeps one flop (P_g[msb]) and the LEC signature search proposes no relation for the
gold-only P[msb] -> NOT EQUIVALENT (S81 serdes__t14/t15: 573/4158 differs; HBM rx_bm3_rest: 4104 differs).
The proved fix is an untrusted correspondence hint per pointer (EQUIVALENT on HBM rx_bm3_rest vA/vB2):

    ["gold", "ff:u_dut.<inst path>.P[msb]", ["eq", "gate", "ff:u_dut.<inst path>.P_g[msb]", 0]]

Which flop opt_merge keeps differs per pointer (HBM rx_bm3_rest vA gate: wp_g[3] and rp[3]), so both
orientations are emitted; the one whose gate key is absent is skipped by lec.py (apply_hints), and lec.py
proves every applied hint by induction and drops a false one, so a hint is never a waiver.

Detection is structural, on the kit's staged RTL: a module qualifies when it declares P and P_g with the same
[N:0] range and contains the gray assignment above; the generator walks the instance tree from the kit top
(the LEC wrapper instance u_dut) and emits one hint per pointer per instance path.  Kits without such a
module are byte-identical (no file written).  An existing lec_hints.json (kit/recipe hints) is kept as is; a
gray hint is only appended when no existing hint names the same gold register.
"""
import hashlib
import json
import re
from pathlib import Path

LEC_TOP = "u_dut"                       # lec.py WRAP: the kit top is instance u_dut of lec_top
RTL_SUFFIXES = (".sv", ".v")

_COMMENT = re.compile(r"//[^\n]*|/\*.*?\*/", re.S)
_MODULE = re.compile(r"\bmodule\s+(\w+)(.*?)\bendmodule\b", re.S)
_GRAY = re.compile(r"\b(\w+)_g\s*<=\s*\(\s*\1\s*\+\s*1'b1\s*\)\s*\^\s*\(\s*\(\s*\1\s*\+\s*1'b1\s*\)\s*>>\s*1\s*\)")
_DECL = re.compile(r"\b(?:reg|logic)\s+(?:(?:unsigned|signed)\s+)?\[\s*(\d+)\s*:\s*0\s*\]\s*([^;]*);")
_KEYWORDS = {"module", "endmodule", "begin", "end", "if", "else", "for", "case", "assign", "always", "wire", "reg",
             "logic", "input", "output", "inout", "function", "task", "generate", "endgenerate", "initial"}


def strip_comments(text):
    return _COMMENT.sub(" ", text)


def parse_modules(texts):
    """{module name: body text} over the given source texts (comments removed; first definition wins)."""
    mods = {}
    for t in texts:
        for m in _MODULE.finditer(strip_comments(t)):
            mods.setdefault(m.group(1), m.group(2))
    return mods


def gray_pointers(body):
    """[(P, msb)] for every binary/gray pointer pair P, P_g of one module body (same [msb:0] range declared)."""
    width = {}
    for m in _DECL.finditer(body):
        for name in re.findall(r"\b([A-Za-z_]\w*)\b", re.sub(r"\[[^\]]*\]", " ", m.group(2))):
            width.setdefault(name, int(m.group(1)))
    out = []
    for p in dict.fromkeys(m.group(1) for m in _GRAY.finditer(body)):
        if p in width and width.get(f"{p}_g") == width[p] and width[p] >= 1:
            out.append((p, width[p]))
    return out


def _skip_parens(text, i):
    """index after the balanced (...) starting at text[i] == '(' (len(text) if unbalanced)."""
    depth = 0
    for j in range(i, len(text)):
        if text[j] == "(":
            depth += 1
        elif text[j] == ")":
            depth -= 1
            if depth == 0:
                return j + 1
    return len(text)


def instances(body, known):
    """[(module, instance)] of the known modules instantiated in one module body (scalar instances only)."""
    out = []
    for m in re.finditer(r"(?<![\w.$`'])([A-Za-z_]\w*)\b", body):
        mod = m.group(1)
        if mod not in known or mod in _KEYWORDS:
            continue
        i = m.end()
        while i < len(body) and body[i].isspace():
            i += 1
        if body.startswith("#", i):
            i += 1
            while i < len(body) and body[i].isspace():
                i += 1
            if not body.startswith("(", i):
                continue
            i = _skip_parens(body, i)
        im = re.compile(r"\s*([A-Za-z_]\w*)\s*\(").match(body, i)
        if im and im.group(1) not in _KEYWORDS:
            out.append((mod, im.group(1)))
    return out


def gray_twin_hints(sources, top, prefix=LEC_TOP):
    """Hints for every gray pointer under `top`.  sources: an RTL directory or an iterable of files/texts."""
    if isinstance(sources, Path) or (isinstance(sources, str) and "\n" not in sources):
        d = Path(sources)                         # an RTL directory (a missing one = no RTL staged: no hints)
        texts = [p.read_text(errors="replace") for p in sorted(d.rglob("*"))
                 if p.is_file() and p.suffix in RTL_SUFFIXES] if d.is_dir() else []
    else:
        texts = [Path(s).read_text(errors="replace") if isinstance(s, Path) or
                 (isinstance(s, str) and "\n" not in s and Path(s).is_file()) else s for s in sources]
    mods = parse_modules(texts)
    if top not in mods:
        return []
    gp = {n: gray_pointers(b) for n, b in mods.items()}
    if not any(gp.values()):
        return []
    hints, stack, seen = [], [(top, prefix, (top,))], set()
    while stack:
        mod, path, chain = stack.pop()
        for p, msb in gp.get(mod, ()):
            key = (path, p)
            if key not in seen:
                seen.add(key)
                a, b = f"ff:{path}.{p}[{msb}]", f"ff:{path}.{p}_g[{msb}]"
                hints.append(["gold", a, ["eq", "gate", b, 0]])     # gate kept P_g[msb] (the proved HBM form)
                hints.append(["gold", b, ["eq", "gate", a, 0]])     # gate kept P[msb] (merged the other way)
        for sub, inst in reversed(instances(mods[mod], mods)):
            if sub not in chain:                  # no recursion through a cycle
                stack.append((sub, f"{path}.{inst}", chain + (sub,)))
    return hints


def merge(existing, extra):
    """existing hints (array or opentallas.lec_hint_plan.v1 object) + extra; never overrides an existing hint of the
    same gold register.  -> (merged, added)."""
    def named(hs):
        return {h[1] for h in hs if isinstance(h, (list, tuple)) and len(h) >= 2 and isinstance(h[1], str)}
    if existing is None:
        existing = []
    if isinstance(existing, dict):
        have = named(existing.get("preseed", [])) | named(existing.get("post", []))
        add = [h for h in extra if h[1] not in have]
        if not add:
            return existing, []
        out = dict(existing)
        out["post"] = list(existing.get("post", [])) + add
        return out, add
    have = named(existing)
    add = [h for h in extra if h[1] not in have]
    return (list(existing) + add if add else existing), add


def stage(kd, top, rtl=None, prefix=LEC_TOP):
    """Merge the gray-MSB twin hints of `top` into KIT/lec_hints.json (before the kit hash / freeze).
    -> None (no pointer, or all already hinted: the kit is untouched) or {file, added, count, sha256}."""
    kd = Path(kd)
    hints = gray_twin_hints(rtl if rtl is not None else kd / "rtl", top, prefix)
    if not hints:
        return None
    f = kd / "lec_hints.json"
    cur = json.loads(f.read_text()) if f.is_file() else None
    merged, add = merge(cur, hints)
    if not add:
        return None
    body = json.dumps(merged, indent=1) + "\n"
    f.write_text(body)
    n = len(merged) if isinstance(merged, list) else len(merged.get("preseed", [])) + len(merged.get("post", []))
    return dict(file="lec_hints.json", added=[h[1] for h in add], count=n,
                sha256=hashlib.sha256(body.encode()).hexdigest())
