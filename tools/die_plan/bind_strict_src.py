"""Strict-bind source-tree checks (BIND-STRICT-SRC, COORD 11-11; class S7 of the s25 gate bind from a stale tree).

`bind.py bind --strict` calls check() after bind.f is written.  Every error is a bind error (non-zero exit).

BIND_SRC_OUTSIDE  a bind.f path outside the allowed roots.  Allowed roots (data driven, no per-die list):
                    the repository the running tool lives in (E.REPO), the bind output dir, the plan dir, the plan's
                    asbuilt base (the declared source tree), the plan key asbuilt.external_roots [paths], and
                    --allow-src-root PATH (repeatable; a diagnostic exception, recorded in the report).
                  Entries captured by the as-built elaboration itself (asbuilt_sources.json `lib`, written from the
                  declared manifest) are the as-built capture and are exempt; their directories are reported.
BIND_SRC_MISSING  a bind.f path that is not a file.
BIND_GROUP_MASTER a module instantiated by a bound-group rewrite (bound_groups.materialize products) that no bind.f
                  file defines (a master registered in neither the as-built lib nor extra_lib).
BIND_PARAM_UNKNOWN a bound-RTL instance overrides parameter P of module M while every bind.f definition of M lacks P
                  (text check: header #( ) and body `parameter` lists; QREG on a ring without a QREG parameter).
"""
import re
from pathlib import Path

_MOD = re.compile(r"^\s*module\s+(?:automatic\s+|static\s+)?(\w+)", re.M)
_INST = re.compile(r"^[ \t]*(\w+)[ \t\r\n]*#[ \t\r\n]*\(", re.M)
_KW = {"module", "if", "for", "case", "assign", "always", "initial", "generate", "function", "task", "else", "begin",
       "parameter", "localparam", "typedef", "import", "class", "interface", "program", "package", "bind"}


def _strip(s):
    s = re.sub(r"/\*.*?\*/", " ", s, flags=re.S)
    return re.sub(r"//[^\n]*", "", s)


def definitions(text):
    """{module: set(parameter names)} from SV text (comments stripped)."""
    t = _strip(text)
    ms = list(_MOD.finditer(t))
    out = {}
    for m in ms:
        end = t.find("endmodule", m.end())
        body = t[m.end(): end if end >= 0 else len(t)]
        semi = body.find(";")
        header = body[:semi] if semi >= 0 else body
        names = set()
        h = re.search(r"#\s*\((.*)", header, re.S)
        if h:
            names |= set(re.findall(r"(\w+)\s*=(?!=)", h.group(1)))
        for chunk in re.findall(r"\bparameter\b([^;]*);", body):
            names |= set(re.findall(r"(\w+)\s*=(?!=)", chunk))
        out.setdefault(m.group(1), set()).update(names)
    return out


def _balanced(t, i):
    """index just past the paren group opened at t[i] == '('."""
    d = 0
    for j in range(i, len(t)):
        c = t[j]
        if c == "(":
            d += 1
        elif c == ")":
            d -= 1
            if d == 0:
                return j + 1
    return len(t)


def instances(text):
    """[(module, [override names], line)] for `mod #(.P(..), ...) inst (` instantiations."""
    t = _strip(text)
    res = []
    for m in _INST.finditer(t):
        mod = m.group(1)
        if mod in _KW or mod.startswith("end"):
            continue
        o = t.index("(", m.end() - 1)
        e = _balanced(t, o)
        if not re.match(r"\s*(\w+|\\\S+)\s*(\[[^\]]*\]\s*)?\(", t[e:e + 400]):
            continue
        inner = t[o + 1: e - 1]
        names, d = [], 0
        for k, c in enumerate(inner):
            if c == "(":
                d += 1
            elif c == ")":
                d -= 1
            elif c == "." and d == 0 and (k == 0 or not (inner[k - 1].isalnum() or inner[k - 1] == "_")):
                n = re.match(r"\.(\w+)", inner[k:])
                if n:
                    names.append(n.group(1))
        res.append((mod, names, t.count("\n", 0, m.start()) + 1))
    return res


_ANY_INST = re.compile(
    r"^[ \t]*(\w+)(?:[ \t\r\n]*#[ \t\r\n]*\((?:[^()]|\((?:[^()]|\([^()]*\))*\))*\))?[ \t\r\n]+(?:\\\S+|\w+)[ \t\r\n]*\(",
    re.M)


def instantiated_modules(text):
    """every `mod [#(...)] inst (` instantiation module name (for the group-master check)."""
    return {m.group(1) for m in _ANY_INST.finditer(_strip(text))
            if m.group(1) not in _KW and not m.group(1).startswith("end")}


def allowed_roots(repo, out, plan, base, ab, extra=()):
    roots = [repo, out, Path(plan).parent, base] + [Path(x) for x in (ab or {}).get("external_roots", [])] + \
            [Path(x) for x in extra]
    return [Path(r).resolve() for r in roots if r]


def _inside(p, roots):
    p = Path(p).resolve()
    return any(p == r or r in p.parents for r in roots)


def check(files_f, as_built_lib, extra_lib, emitted, group_products, roots):
    """files_f: bind.f entries in order; as_built_lib: the subset captured by the as-built elaboration (exempt from
    the root check); extra_lib/emitted: tool-resolved entries.  Returns (errors, info)."""
    errs, info = [], {}
    exempt = {str(Path(f).resolve()) for f in as_built_lib}
    info["as_built_roots"] = sorted({str(Path(f).parent) for f in as_built_lib})[:50]
    bad = [f for f in files_f if str(Path(f).resolve()) not in exempt and not _inside(f, roots)]
    if bad:
        errs.append(f"BIND_SRC_OUTSIDE {len(bad)} bind.f path(s) outside the declared source tree (allowed roots: "
                    f"{', '.join(str(r) for r in roots)}); first {bad[0]}.  Bind from the branch tree, or declare a "
                    f"legitimate external root: plan asbuilt.external_roots or --allow-src-root PATH")
    miss = [f for f in files_f if not Path(f).is_file()]
    if miss:
        errs.append(f"BIND_SRC_MISSING {len(miss)} bind.f path(s) are not files; first {miss[0]}")
    defs = {}
    for f in files_f:
        try:
            for m, ps in definitions(Path(f).read_text(errors="replace")).items():
                defs.setdefault(m, set()).update(ps)
        except OSError:
            continue
    for g in group_products:
        try:
            used = instantiated_modules(Path(g).read_text(errors="replace"))
        except OSError:
            continue
        gone = sorted(m for m in used if m not in defs)
        if gone:
            errs.append(f"BIND_GROUP_MASTER {Path(g).name}: module(s) {gone[:8]} instantiated by a bound group rewrite "
                        f"but defined in no bind.f file (register the master in extra_lib: bound_groups.register_masters)")
    seen = set()
    for f in emitted:
        try:
            text = Path(f).read_text(errors="replace")
        except OSError:
            continue
        for mod, ov, line in instances(text):
            if mod not in defs or not ov:
                continue
            for p in ov:
                if p not in defs[mod] and (mod, p) not in seen:
                    seen.add((mod, p))
                    errs.append(f"BIND_PARAM_UNKNOWN {Path(f).name}:{line} {mod} overrides parameter {p} that no bind.f "
                                f"definition of {mod} declares (stale or wrong RTL in bind.f?)")
    return errs, info
