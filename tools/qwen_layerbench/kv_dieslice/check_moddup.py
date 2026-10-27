#!/usr/bin/env python3
"""TOK-QK-4 10-27: fail a Verilator source list that defines one module in more than one file.

Verilator with -Wno-MODDUP silently keeps the FIRST definition of a duplicated module, so a list that carries two
revisions of one file (e.g. an old vehicle copy and the fixed copy of qkd_ctrl_pc_nc.sv) builds the wrong RTL with no
error.  Rule: one source per module.  This check reads a Verilator argument file (recursing into -f / -F files), takes
every listed source file (options, +incdir+, +define+ and -y/-v library search paths are not sources: Verilator loads
a library file only for a module that no listed file defines), parses its `module` / `macromodule` / `primitive` /
`interface` / `package` declarations (comments and strings stripped) and exits 1 when any name is declared in two
different files (identical module text included: still two sources).  The same file listed twice is reported but is
not a duplicate definition.

usage: check_moddup.py LIST.f [LIST2.f ...] [--drop-redundant] [--allow NAME ...] [--json OUT]
exit 0 = one source per module, 1 = duplicates (listed), 2 = unreadable list or source.
"""
import argparse
import hashlib
import json
import os
import re
import sys

SRC_EXT = ('.sv', '.v', '.svh', '.vh', '.vlt', '.svp')
# options that take the next token as an argument (not a source)
ARG_OPTS = {'-y', '-v', '--top-module', '--prefix', '--mod-prefix', '-Mdir', '-j', '--build-jobs', '-CFLAGS', '-LDFLAGS',
            '--timescale', '-o', '--output-split', '--output-groups', '--x-assign', '--x-initial', '--hierarchical-block',
            '--threads', '-G', '--top'}
DECL = re.compile(r'^\s*(?:module|macromodule|primitive|interface|package|program)\s+(?:automatic\s+|static\s+)?'
                  r'([A-Za-z_][A-Za-z0-9_$]*)', re.M)
END = re.compile(r'\b(?:endmodule|endprimitive|endinterface|endpackage|endprogram)\b')


def strip_comments(s):
    out, i, n = [], 0, len(s)
    while i < n:
        c = s[i]
        if s.startswith('//', i):
            j = s.find('\n', i)
            i = n if j < 0 else j
        elif s.startswith('/*', i):
            j = s.find('*/', i + 2)
            seg = s[i:(n if j < 0 else j + 2)]
            out.append('\n' * seg.count('\n'))
            i = n if j < 0 else j + 2
        elif c == '"':
            j = i + 1
            while j < n and s[j] != '"':
                j += 2 if s[j] == '\\' else 1
            out.append('""')
            i = j + 1
        else:
            out.append(c)
            i += 1
    return ''.join(out)


def tokens(path):
    with open(path) as f:
        for line in f:
            line = line.split('//', 1)[0]
            for t in line.split():
                yield t


def sources(listfile, seen_lists=None):
    """Yield (source path, list file) in order, recursing into -f/-F (relative to cwd for -f, to the list for -F)."""
    seen_lists = set() if seen_lists is None else seen_lists
    real = os.path.realpath(listfile)
    if real in seen_lists:
        return
    seen_lists.add(real)
    toks = list(tokens(listfile))
    i = 0
    while i < len(toks):
        t = toks[i]
        if t in ('-f', '-F'):
            nxt = toks[i + 1]
            if t == '-F' and not os.path.isabs(nxt):
                nxt = os.path.join(os.path.dirname(listfile), nxt)
            yield from sources(nxt, seen_lists)
            i += 2
            continue
        if t in ARG_OPTS:
            i += 2
            continue
        if t.startswith('-') or t.startswith('+'):
            i += 1
            continue
        if t.endswith(SRC_EXT) and not t.endswith('.vlt'):
            yield t, listfile
        i += 1


def check(lists, allow=()):
    defs = {}          # name -> [(path, sha)]
    listed = {}        # realpath -> count
    order = []
    for lf in lists:
        for src, _ in sources(lf):
            rp = os.path.realpath(src)
            listed[rp] = listed.get(rp, 0) + 1
            if listed[rp] > 1:
                continue
            order.append(src)
    errors = []
    for src in order:
        try:
            raw = open(src, errors='replace').read()
        except OSError as e:
            errors.append(f'{src}: {e}')
            continue
        body = strip_comments(raw)
        for m in DECL.finditer(body):
            # hash the declaration's own text (to its matching end keyword), whitespace-normalised: two files that
            # carry the same module body are 'identical copies', different bodies are a silent RTL choice
            end = END.search(body, m.end())
            text = ' '.join(body[m.start():end.end() if end else len(body)].split())
            sha = hashlib.sha256(text.encode()).hexdigest()[:12]
            defs.setdefault(m.group(1), []).append((src, sha))
    dups = {n: v for n, v in defs.items() if len({os.path.realpath(p) for p, _ in v}) > 1 and n not in allow}
    relisted = sorted(p for p, c in listed.items() if c > 1)
    return dups, relisted, errors, len(order), defs, order


def redundant_files(defs, order):
    """Later files whose EVERY declaration is already made, with identical module text, by earlier listed files: dropping
    such a file cannot change the elaborated RTL (Verilator keeps the first definition anyway). Anything else (different
    text, or a file that also declares something new) stays and is reported as a duplicate."""
    first = {}
    for n, v in defs.items():
        first[n] = v[0]
    per_file = {}
    for n, v in defs.items():
        for p, sha in v:
            per_file.setdefault(p, []).append((n, sha))
    drop = []
    for p in order:
        decl = per_file.get(p, [])
        if decl and all(first[n][0] != p and first[n][1] == sha for n, sha in decl):
            drop.append(p)
    return drop


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('lists', nargs='+')
    ap.add_argument('--allow', nargs='*', default=[], help='module names exempt (must be justified at the call site)')
    ap.add_argument('--json')
    ap.add_argument('--drop-redundant', action='store_true',
                    help='rewrite the list(s) without later files whose every module an earlier file defines with '
                         'identical text (safe: same elaborated RTL), then check the rest strictly')
    a = ap.parse_args(argv)
    try:
        dups, relisted, errors, nsrc, defs, order = check(a.lists, set(a.allow))
        if a.drop_redundant and not errors:
            drop = set(redundant_files(defs, order))
            for lf in a.lists:   # top-level lists only (build.sh flattens files.f/hostside.f into vl.f)
                lines = open(lf).read().splitlines(keepends=True)
                keep = [ln for ln in lines if ln.strip() not in drop]
                for ln in lines:
                    if ln.strip() in drop:
                        print(f'MODDUP_DROP identical redundant copy removed from {lf}: {ln.strip()}')
                if len(keep) != len(lines):
                    open(lf, 'w').writelines(keep)
            dups, relisted, errors, nsrc, defs, order = check(a.lists, set(a.allow))
    except OSError as e:
        print(f'MODDUP_CHECK ERROR {e}')
        return 2
    for e in errors:
        print(f'MODDUP_CHECK ERROR unreadable source {e}')
    for n in sorted(dups):
        v = dups[n]
        same = len({s for _, s in v}) == 1
        print(f'MODDUP {n} defined in {len(v)} files ({"identical module text" if same else "DIFFERENT module text"}); '
              f'Verilator -Wno-MODDUP would keep the first:')
        for p, s in v:
            print(f'    {s} {p}')
    for p in relisted:
        print(f'MODDUP_NOTE listed twice (same file, not a duplicate definition): {p}')
    if a.json:
        with open(a.json, 'w') as f:
            json.dump({'sources': nsrc, 'duplicates': {n: v for n, v in dups.items()}, 'relisted': relisted,
                       'errors': errors}, f, indent=1)
    verdict = 'FAIL' if dups else ('ERROR' if errors else 'PASS')
    print(f'MODDUP_CHECK {verdict} sources {nsrc} duplicated_modules {len(dups)} unreadable {len(errors)}')
    return 1 if dups else (2 if errors else 0)


if __name__ == '__main__':
    sys.exit(main())
