#!/usr/bin/env python3
"""SS25-TOK 11-03: a simulation vehicle must not elaborate an empty black box that drives outputs.

Why: KV veh60c45 picked ot_rom_64x32_m2_bb.v from its bind recipe.  Verilator accepts the empty (* blackbox *) module and
its outputs read 0, so the D2D calibration profile was all zero: the boot words looked stale and the admission run had
length 0.  It cost a 9:23 h build and a 3:57 h run, and a read-0 memory could also fake a token result.

    check_vehicle_blackbox.py LIST.f [LIST.f ...] [--top MODULE] [--root DIR] [--allow REGEX] [--json OUT]

Reads the file lists (a path per line; +define/+incdir skipped; -y DIR adds that directory's sources as definitions), walks
the module tree from --top (default: every module nothing instantiates) and reports each reachable module whose body is
empty and which has an output.  Tree walking is a word match over the source, with no `ifdef or generate evaluation, so it
can over-report and must not under-report.  --allow names modules the bench models on purpose (off-die PHY hard macros);
the module must then be defined by a bench file or be named here.  rc 2 = a reachable empty module not allowed."""
import argparse, json, os, re, sys
MOD = re.compile(r'^[ \t]*(?:\(\*[^*]*\*\)\s*)?(?:module|macromodule)\s+(?:automatic\s+)?(\w+)(.*?)\bendmodule\b', re.M | re.S)
WORD = re.compile(r'\b[A-Za-z_]\w*\b')
SRC = ('.sv', '.v', '.svh', '.vh')


def strip(text):
    text = re.sub(r'/\*.*?\*/', ' ', text, flags=re.S)
    return re.sub(r'//[^\n]*', '', text)


def read_list(path, root, seen=None):
    """Return (files, -y dirs) of one list, following nested -f."""
    seen = set() if seen is None else seen
    files, ydirs = [], []
    base = root or os.path.dirname(os.path.abspath(path))
    if os.path.abspath(path) in seen:
        return files, ydirs
    seen.add(os.path.abspath(path))
    for line in open(path, errors='replace'):
        for tok in [line.strip()] if not line.strip().startswith(('-y ', '-f ', '-F ')) else [line.strip()]:
            if not tok or tok.startswith(('#', '//', '+')):
                continue
            if tok.startswith('-y '):
                ydirs.append(os.path.join(base, tok[3:].strip()))
            elif tok.startswith(('-f ', '-F ')):
                f, y = read_list(os.path.join(base, tok[3:].strip()), root, seen)
                files += f; ydirs += y
            elif tok.startswith('-'):
                continue
            elif tok.endswith(SRC):
                files.append(os.path.join(base, tok))
    return files, ydirs


def header_end(body):
    """Offset just after the module header's closing ';' (paren depth 0)."""
    depth = 0
    for i, c in enumerate(body):
        if c == '(':
            depth += 1
        elif c == ')':
            depth -= 1
        elif c == ';' and depth == 0:
            return i + 1
    return len(body)


def is_empty(body):
    """True when the module drives outputs and has nothing that could drive them."""
    if not re.search(r'\boutput\b', body):
        return False
    rest = body[header_end(body):]
    # Non-ANSI port lists only leave declarations after the header; anything else is real content.
    rest = re.sub(r'^\s*(input|output|inout|wire|reg|logic|parameter|localparam|`\w+)\b[^;\n]*;?\s*$', '', rest, flags=re.M)
    return not rest.strip()


def scan(files, ydirs):
    defs = {}
    def add(path, weak):
        try:
            text = strip(open(path, errors='replace').read())
        except OSError:
            return False
        for m in MOD.finditer(text):
            if weak and m.group(1) in defs:
                continue
            old = defs.get(m.group(1))
            # A real definition listed anywhere wins over an empty one: Verilator would report the duplicate otherwise.
            if old and not old['empty'] and is_empty(m.group(2)):
                continue
            defs[m.group(1)] = {'file': path, 'body': m.group(2), 'empty': is_empty(m.group(2))}
        return True
    unread = [f for f in files if not add(f, False)]
    for d in ydirs:
        for f in sorted(os.listdir(d)) if os.path.isdir(d) else []:
            if f.endswith(SRC):
                add(os.path.join(d, f), True)
    return defs, unread


def walk(defs, tops):
    parent = {t: None for t in tops if t in defs}
    todo = list(parent)
    while todo:
        m = todo.pop()
        b = defs[m]['body']
        for w in set(WORD.findall(b[header_end(b):])):
            if w in defs and w not in parent and w != m:
                parent[w] = m
                todo.append(w)
    return parent


def path_to(parent, m):
    out = []
    while m is not None and len(out) < 12:
        out.append(m)
        m = parent[m]
    return ' <- '.join(out)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('lists', nargs='+')
    ap.add_argument('--top', action='append', default=[])
    ap.add_argument('--root', default=None, help='base for relative paths (default: each list\'s directory)')
    ap.add_argument('--allow', default=None)
    ap.add_argument('--json', default=None)
    a = ap.parse_args(argv)
    files, ydirs = [], []
    for lst in a.lists:
        f, y = read_list(lst, a.root)
        files += f; ydirs += y
    defs, unread = scan(files, ydirs)
    tops = a.top
    if not tops:
        used = set()
        for name, d in defs.items():
            used |= {w for w in set(WORD.findall(d['body'])) if w in defs and w != name}
        tops = sorted(set(defs) - used)
    missing = [t for t in tops if t not in defs]
    parent = walk(defs, tops)
    allow = re.compile(a.allow) if a.allow else None
    empties = sorted(m for m in parent if defs[m]['empty'])
    allowed = [m for m in empties if allow and allow.search(m)]
    bad = [m for m in empties if m not in allowed]
    for m in allowed:
        print(f'VEHICLE_BLACKBOX allowed {m} {defs[m]["file"]}')
    for m in bad:
        print(f'VEHICLE_BLACKBOX EMPTY {m} {defs[m]["file"]} via {path_to(parent, m)}')
    if unread:
        print(f'VEHICLE_BLACKBOX note: {len(unread)} listed files unreadable, first {unread[0]}')
    verdict = 'FAIL' if bad or missing else 'PASS'
    print(f'VEHICLE_BLACKBOX {verdict} modules {len(defs)} reachable {len(parent)} empty {len(empties)} allowed {len(allowed)} '
          f'bad {len(bad)} tops {len(tops)} missing_tops {missing}')
    if a.json:
        json.dump({'verdict': verdict, 'bad': bad, 'allowed': allowed, 'tops': tops, 'unread': unread}, open(a.json, 'w'), indent=1)
    return 2 if verdict == 'FAIL' else 0


if __name__ == '__main__':
    sys.exit(main())
