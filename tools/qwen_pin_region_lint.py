#!/usr/bin/env python3
"""Pin-region coverage lint for the Qwen ROM die-master cfgs (pinregion 2026-10-08).

Every die-face port of a die master must land on its assigned edge, so each port (each bit of a bus) of the cfg's
TOP must match EXACTLY ONE --pin-region regex.  A prefix written as '^(x_|...)(\\[|$)' matches only a port named
literally 'x_' (Tcl regexp on the bterm name 'x_dv[3]'), which left whole buses unconstrained while the exact names
in the same group kept the region non-empty; this lint catches that statically.  The same rule is enforced at
floorplan time by run_abi3_physical.py --pin-regions-exhaustive (route_master.sh passes it).

  python3 tools/qwen_pin_region_lint.py [CFG ...]   (default: every physical/qwen_die_masters/cfg/*.env with PINS)
Exit 1 when any port matches no region or more than one.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CFG_DIR = ROOT / 'physical/qwen_die_masters/cfg'


def load_cfg(name):
    sh = (f'set -e; source {CFG_DIR / name}.env >/dev/null 2>&1; echo @@CFG@@; printf "%s\\n" "$TOP"; printf "%s\\n" "$SRCS"; '
          'for p in "${PINS[@]}"; do printf "%s\\n" "$p"; done')
    out = subprocess.run(['bash', '-c', sh], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    out = out.split('@@CFG@@\n', 1)[1].split('\n')
    top, srcs, pins = out[0], out[1].split(), [p for p in out[2:] if p]
    regions = [pins[i + 1] for i, p in enumerate(pins) if p == '--pin-region']
    return top, srcs, regions


def _strip(t):
    return re.sub(r'/\*.*?\*/', '', re.sub(r'//[^\n]*', '', t), flags=re.S)


def _balanced(s, k):
    d = 0
    for j in range(k, len(s)):
        d += s[j] == '('
        d -= s[j] == ')'
        if d == 0:
            return j
    raise ValueError('unbalanced')


def top_ports(srcs, top):
    """ANSI header ports of TOP: [(name, is_bus)]."""
    for f in srcs:
        p = ROOT / f
        if not p.exists() or p.suffix not in ('.sv', '.v'):
            continue
        t = _strip(p.read_text(errors='replace'))
        m = re.search(r'\bmodule\s+' + re.escape(top) + r'\b', t)
        if not m:
            continue
        s = t[m.end():].lstrip()
        if s.startswith('#'):
            k = s.index('(')
            s = s[_balanced(s, k) + 1:].lstrip()
        if not s.startswith('('):
            return []
        hdr = re.sub(r'\(\*.*?\*\)', ' ', s[1:_balanced(s, 0)], flags=re.S)
        ports, bus = [], False
        for part in hdr.split(','):
            part = re.sub(r'\s+', ' ', part.replace('[', ' [')).strip()
            if not part:
                continue
            bare = re.sub(r'\[[^\]]*\]', ' ', part).split()
            if re.match(r'(input|output|inout)\b', part):
                bus = '[' in part.rsplit(' ', 1)[0]
            elif '[' in part.rsplit(' ', 1)[0]:
                bus = True
            ports.append((bare[-1], bus))
        return ports
    raise SystemExit(f'top module {top} not found in its SRCS')


def lint(cfg):
    top, srcs, regions = load_cfg(cfg)
    pats = [(r, re.compile(r.rsplit('=', 1)[0])) for r in regions]
    errs = []
    for name, bus in top_ports(srcs, top):
        for bt in ([f'{name}[{k}]' for k in range(12)] if bus else [name]):
            hit = [r for r, p in pats if p.search(bt)]
            if len(hit) != 1:
                errs.append(dict(port=bt, matches=hit))
    dead = [r for r, p in pats if not any(p.search(b) for n, bus in top_ports(srcs, top)
                                           for b in ([f'{n}[{k}]' for k in range(12)] if bus else [n]))]
    return dict(cfg=cfg, top=top, regions=len(regions), errors=errs, empty_regions=dead,
                ok=not errs and not dead)


def main(argv):
    cfgs = argv or sorted(p.stem for p in CFG_DIR.glob('*.env') if 'pin-region' in p.read_text())
    res = [lint(c) for c in cfgs]
    bad = [r for r in res if not r['ok']]
    for r in bad:
        print(json.dumps(r))
    print(f'qwen_pin_region_lint: {len(res)} cfgs, {len(bad)} failing')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
