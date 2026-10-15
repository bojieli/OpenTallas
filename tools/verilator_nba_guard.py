#!/usr/bin/env python3
"""Fail closed when a Verilator model applied a clocked non-blocking loop in place (no __Vdly shadow).

Defect (found by H-ATTQ 2026-10-15, generalised by root): Verilator 5.050 compiles a NOT-unrolled loop of
non-blocking writes such as ``for (i=1;i<=D;i++) r[i] <= (i==1) ? d : r[i-1];`` as an in-place loop on ``r``
itself: blocking semantics, every stage collapses to ``d`` in one edge. It happens whenever the trip count
exceeds ``--unroll-count`` -- with ``--unroll-count 1/4/5`` for D=6, and ALSO with the default 64 (or 128) once
D > 64, where the packed vector is a VlWide word array (that form escapes the original bit-insert regex).
RTL is correct; the simulation model is not, so any PASS/FAIL from such a model is unproven.

Signature in the generated C++ (non-Slow files, NBA-region functions): inside a ``while`` loop, a statement
writes ``vlSelfRef.X`` (scalar, bit insert or VlWide word) and reads ``vlSelfRef.X`` on its right-hand side,
X is not a loop counter of that while, and the model has no ``__Vdly__X`` shadow at all.

Usage: verilator_nba_guard.py OBJ_DIR [OBJ_DIR...]  -> exit 1 if any in-place NBA loop is found.
Library: scan(obj_dir) -> dict(findings=[...], loops_checked=n); check(obj_dir) raises SystemExit on findings.
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys

FUNC = re.compile(r'^(?:VL_ATTR_COLD\s+|VL_INLINE_OPT\s+|static\s+)*[\w:<>\*&\s]+?\b(\w+)\([^;{]*\)\s*\{\s*$', re.M)
WHILE = re.compile(r'\bwhile\s*\(')
SELF = re.compile(r'\bvlSelf(?:Ref\.|->)(\w+)')


def _balanced(text: str, start: int, open_ch: str, close_ch: str) -> int:
    """Index just past the bracket matching text[start] == open_ch (or len(text))."""
    depth = 0
    for k in range(start, len(text)):
        c = text[k]
        if c == open_ch:
            depth += 1
        elif c == close_ch:
            depth -= 1
            if depth == 0:
                return k + 1
    return len(text)


def _assign_split(stmt: str):
    """Split a C++ statement at its top-level simple '=' (not ==, <=, >=, !=, op=)."""
    depth = 0
    for k, c in enumerate(stmt):
        if c in '([{':
            depth += 1
        elif c in ')]}':
            depth -= 1
        elif c == '=' and depth == 0:
            prev = stmt[k - 1] if k else ''
            nxt = stmt[k + 1] if k + 1 < len(stmt) else ''
            if nxt == '=' or prev in '=<>!+-*/%&|^':
                continue
            return stmt[:k], stmt[k + 1:]
    return None


def _functions(text: str):
    """Yield (name, body) for each top-level function definition."""
    for m in FUNC.finditer(text):
        brace = text.index('{', m.end() - 1)
        yield m.group(1), text[brace:_balanced(text, brace, '{', '}')]


def _model_text(obj_dir: str):
    for f in sorted(glob.glob(os.path.join(obj_dir, '**', '*.cpp'), recursive=True)):
        if '__Slow' in os.path.basename(f) or f.endswith('__main.cpp'):
            continue
        with open(f, errors='replace') as fh:
            yield f, fh.read()


def scan(obj_dir: str) -> dict:
    files = list(_model_text(obj_dir))
    if not files:
        raise FileNotFoundError(f'no generated Verilator model (*.cpp) under {obj_dir}')
    shadows = set()
    for _, text in files:
        shadows.update(re.findall(r'__Vdly__(\w+)', text))
    findings, loops = [], 0
    for path, text in files:
        for fname, body in _functions(text):
            if 'nba' not in fname and 'Inlined CFunc: _nba' not in body:
                continue
            for w in WHILE.finditer(body):
                paren = body.index('(', w.start())
                cond_end = _balanced(body, paren, '(', ')')
                counters = set(SELF.findall(body[paren:cond_end]))
                brace = body.find('{', cond_end)
                if brace < 0 or body[cond_end:brace].strip():
                    continue
                loop = body[brace + 1:_balanced(body, brace, '{', '}') - 1]
                loops += 1
                for stmt in loop.split(';'):
                    # Control-flow braces (if/else blocks) precede the assignment; expressions carry none.
                    parts = _assign_split(re.split(r'[{}]', stmt)[-1])
                    if not parts:
                        continue
                    lhs, rhs = parts
                    m = re.match(r'\s*vlSelf(?:Ref\.|->)(\w+)', lhs)
                    if not m:
                        continue
                    var = m.group(1)
                    if var.startswith('__V') or var in counters or var in shadows:
                        continue
                    if re.search(r'\bvlSelf(?:Ref\.|->)' + re.escape(var) + r'\b', rhs):
                        findings.append(dict(file=os.path.relpath(path, obj_dir), function=fname, var=var,
                                             counter=sorted(counters)))
    # A blocking prefix loop (``p[i] = p[i-1] ^ x``) has the same C++ shape. Separate it with the actual
    # Verilog sources Verilator recorded (__verFiles.dat): only a variable the RTL writes with ``<=`` is
    # an in-place NBA miscompile. Unreadable sources keep the finding (fail closed).
    sources, missing = _sources(obj_dir)
    modules = {}
    for s in sources:
        for m in MODULE.finditer(s):
            h = re.match(r'(?:module|interface|program)\s+(?:automatic\s+|static\s+)?(\w+)', m.group(0))
            if h:
                modules.setdefault(h.group(1), []).append(m.group(0))
    kept, blocking = [], 0
    for f in findings:
        parts = [re.sub(r'__BRA__.*$', '', x).replace('__PVT__', '') for x in f['var'].split('__DOT__')]
        if parts[-1].startswith('__V'):
            continue
        if missing or not sources:
            f['source_check'] = 'UNAVAILABLE'
        elif _nba_in_rtl(modules, parts):
            f['source_check'] = 'NBA_IN_RTL'
        else:
            blocking += 1
            continue
        kept.append(f)
    return dict(obj_dir=obj_dir, loops_checked=loops, findings=kept, blocking_loops_excluded=blocking,
                sources_read=len(sources), sources_missing=missing)


MODULE = re.compile(r'\b(?:module|interface|program)\b.*?\b(?:endmodule|endinterface|endprogram)\b', re.S)


def _named_block(text: str, label: str):
    """Text of the named block ``begin : label`` (begin/end balanced), or None."""
    m = re.search(r'\bbegin\s*:\s*' + re.escape(label) + r'\b', text)
    if not m:
        return None
    depth = 0
    for tok in re.finditer(r'\b(begin|end)\b', text[m.start():]):
        depth += 1 if tok.group(1) == 'begin' else -1
        if depth == 0:
            return text[m.start():m.start() + tok.end()]
    return text[m.start():]


def _nba_in_scope(module: str, name: str, parent: str) -> bool:
    """The RTL writes ``name`` with <= in the scope Verilator named: the named block ``parent`` if the
    module has one, else anywhere in a module that declares ``name``."""
    # Statement position only (line start, ';', begin/else, ')' of if/for, ':' of a case item), so a
    # ``<=`` comparison inside an expression is not taken for a non-blocking write.
    nba = re.compile(r'(?:^|;|\bbegin\b|\belse\b|\)|:)[ \t]*' + re.escape(name) + r'\s*(?:\[[^;=]*\]\s*)*<=', re.M)
    block = _named_block(module, parent) if parent else None
    if block is not None:
        return bool(nba.search(block))
    decl = re.compile(r'\b(?:reg|logic|bit|integer|int|wire|var)\b[^;]*\b' + re.escape(name) + r'\b')
    return bool(decl.search(module) and nba.search(module))


def _resolve(modules: dict, parts: list):
    """Module texts that own the variable: walk the hierarchical path from the top module through instance
    declarations (named/generate blocks stay in the module). None when the path cannot be resolved."""
    cur = modules.get(parts[0])
    if not cur:
        return None
    for comp in parts[1:-1]:
        nxt = None
        for text in cur:
            if re.search(r'\bbegin\s*:\s*' + re.escape(comp) + r'\b', text):
                nxt = cur
                break
            m = re.search(r'\b(\w+)\s*(?:#\s*\((?:[^()]|\((?:[^()]|\([^()]*\))*\))*\))?\s*\b' + re.escape(comp)
                          + r'\s*(?:\[[^\]]*\]\s*)?\(', text)
            if m and m.group(1) in modules:
                nxt = modules[m.group(1)]
                break
        if nxt is None:
            return None
        cur = nxt
    return cur


def _nba_in_rtl(modules: dict, parts: list) -> bool:
    name, parent = parts[-1], (parts[-2] if len(parts) > 1 else '')
    owners = _resolve(modules, parts)
    if owners is None:  # unresolved path: any module that declares the variable (conservative)
        owners = [t for texts in modules.values() for t in texts]
    return any(_nba_in_scope(m, name, parent) for m in owners)

def _strip_comments(text: str) -> str:
    """Drop // and /* */ comments (keeping strings) so module/always scanning sees only code."""
    return re.sub(r'"(?:\\.|[^"\\])*"|//[^\n]*|/\*.*?\*/',
                  lambda m: m.group(0) if m.group(0).startswith('"') else ' ', text, flags=re.S)


def _sources(obj_dir: str):
    texts, missing = [], []
    for dat in glob.glob(os.path.join(obj_dir, '**', '*__verFiles.dat'), recursive=True):
        for line in open(dat, errors='replace'):
            m = re.match(r'^S\s.*"([^"]+)"\s*$', line)
            if not m or '/share/verilator/' in m.group(1) or m.group(1).endswith('verilator_bin'):
                continue
            path = m.group(1)
            # Relative paths are relative to the build's cwd: try cwd, then the model dir and its ancestors.
            base, cands = os.path.abspath(obj_dir), [path]
            if not os.path.isabs(path):
                for _ in range(6):
                    cands.append(os.path.join(base, path))
                    base = os.path.dirname(base)
            for c in cands:
                if os.path.isfile(c):
                    texts.append(_strip_comments(open(c, errors='replace').read()))
                    break
            else:
                missing.append(path)
    return texts, sorted(set(missing))


def summarize(result: dict) -> str:
    groups = {}
    for f in result['findings']:
        key = re.sub(r'BRA__\d+__KET', 'BRA__N__KET', f['var'])
        groups[key] = groups.get(key, 0) + 1
    lines = [f"{result['obj_dir']}: loops_checked={result['loops_checked']} "
             f"INPLACE_NBA_LOOPS={len(result['findings'])}"]
    for k, v in sorted(groups.items(), key=lambda x: -x[1])[:20]:
        lines.append(f'  INPLACE_NBA_LOOP x{v} {k[:220]}')
    return '\n'.join(lines)


def check(obj_dir: str) -> dict:
    result = scan(obj_dir)
    print(summarize(result))
    if result['findings']:
        raise SystemExit('VERILATOR_NBA_GUARD FAIL: model applies non-blocking loop writes in place '
                         '(Verilator 5.050 non-unrolled NBA loop miscompile); raise --unroll-count above the '
                         'largest NBA loop trip count or rewrite the loop; evidence from this model is invalid')
    return result


def main(argv) -> int:
    as_json = '--json' in argv
    dirs = [a for a in argv if a != '--json']
    if not dirs:
        print(__doc__)
        return 2
    rc = 0
    for d in dirs:
        r = scan(d)
        print(json.dumps(r) if as_json else summarize(r))
        rc |= bool(r['findings'])
    if rc:
        print('VERILATOR_NBA_GUARD FAIL', file=sys.stderr)
    return rc


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
