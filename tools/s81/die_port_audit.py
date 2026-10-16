#!/usr/bin/env python3
"""S81 die port audit (mtp-wfc 2026-10-11, main decision A: no placeholder pins, fail on any unbound functional pin).

For every master a recipe's die instantiates, compare the generator's die pins (tools/dsrom_s81_fulldie.py buses ->
m['pdir'][master]) with the master's RTL ports (`module <master>` under rtl/):
  unbound    an RTL input / output that no die bus reaches (clock / reset / scan / static-tie ports excepted)
  placeholder a die pin that the RTL does not have (the generator invented it: a "placeholder pin")
  width      a die pin whose bit count differs from the RTL port
  no_rtl     a master with no RTL module at all (a generated slab: every pin is a placeholder)
Exit 1 on any unbound / placeholder / width finding (no_rtl is reported; --strict makes it fatal too).

    python3 tools/s81/die_port_audit.py --recipe layer1kit [--out audit.json] [--strict]
"""
import argparse, json, re, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'tools/s81')]
CTRL = re.compile(r'^(ck|ckv|cks|ckh|ckc|clk|refclk|rst|rsv|rss|rs|rst_n|por|pll_\w+|rst_\w+|scan\w*|test\w*|tie\w*|grp)$')


def rtl_ports(module):
    """{port: (direction, bits or None)} from the RTL source of `module` (ANSI port list; widths from literal ranges)."""
    # filesystem scan (the audit also runs in extracted source trees that are not git checkouts)
    r = subprocess.run(['grep', '-rlE', '--include=*.sv', '--include=*.v', rf'^\s*module\s+{re.escape(module)}\b', 'rtl'],
                       cwd=ROOT, capture_output=True, text=True)
    files = sorted(f for f in r.stdout.split() if f and '/test/' not in f and '/tb' not in f)
    if not files:
        return None
    t = (ROOT / files[0]).read_text()
    m = re.search(rf'module\s+{re.escape(module)}\b.*?\)\s*\(\s*(.*?)\)\s*;', t, re.S) or \
        re.search(rf'module\s+{re.escape(module)}\b\s*\(\s*(.*?)\)\s*;', t, re.S)
    if not m:
        return {}
    body = re.sub(r'//.*', '', m.group(1))
    ports, d, w = {}, None, None
    for tok in re.split(r',', body):
        tok = tok.strip()
        mm = re.match(r'(input|output|inout)\s+(?:wire|reg|logic)?\s*(\[[^\]]+\])?\s*(\w+)', tok)
        if mm:
            d, rng, name = mm.group(1), mm.group(2), mm.group(3)
            w = None
            if rng:
                lo = re.match(r'\[\s*(\d+)\s*:\s*(\d+)\s*\]', rng)
                w = abs(int(lo.group(1)) - int(lo.group(2))) + 1 if lo else None
            else:
                w = 1
            ports[name] = (d, w)
        else:
            nm = re.match(r'(?:\[[^\]]+\])?\s*(\w+)$', tok)
            if nm and d:
                ports[nm.group(1)] = (d, w)
    return ports


def audit(m):
    pdir = m.get('pdir') or {}
    masters = sorted({it.master for it in m['insts']})
    out = dict(masters=len(masters), no_rtl=[], findings={})
    for ms in masters:
        die = pdir.get(ms, {})
        rp = rtl_ports(ms)
        if rp is None:
            out['no_rtl'].append(dict(master=ms, die_pins=len(die)))
            continue
        f = dict(unbound=[], placeholder=[], width=[])
        for p, (d, w) in rp.items():
            if CTRL.match(p):
                continue
            if p not in die:
                f['unbound'].append(f'{d} {p}[{w}]')
            elif w and die[p][1] != w:
                f['width'].append(f'{p}: die {die[p][1]} vs rtl {w}')
        for p in die:
            if p not in rp and not CTRL.match(p):
                f['placeholder'].append(p)
        if any(f.values()):
            out['findings'][ms] = f
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--recipe'); ap.add_argument('--out', type=Path); ap.add_argument('--strict', action='store_true')
    ap.add_argument('--opts', type=Path, help='a generator options file instead of a named recipe (ds-1010/s81die)')
    a = ap.parse_args()
    assert bool(a.recipe) != bool(a.opts), 'exactly one of --recipe / --opts'
    import s81_dies_recipe as RC
    import dsrom_s81_fulldie as F
    m = RC.build(RC.recipes()[a.recipe]['opts'] if a.recipe else a.opts.read_text().split())
    a.recipe = a.recipe or str(a.opts)
    if 'pdir' not in m:
        F.finalize_r8(m)
    res = audit(m)
    res['recipe'] = a.recipe
    if a.out:
        a.out.write_text(json.dumps(res, indent=1) + '\n')
    nf = sum(len(v) for f in res['findings'].values() for v in f.values())
    print(f"DIE_PORT_AUDIT {a.recipe}: masters {res['masters']}, with RTL findings {len(res['findings'])} ({nf} pins), "
          f"no RTL {len(res['no_rtl'])}")
    for ms, f in sorted(res['findings'].items()):
        print(f"  {ms}: " + '; '.join(f'{k} {len(v)} e.g. {v[:3]}' for k, v in f.items() if v))
    print('  no RTL: ' + ', '.join(x['master'] for x in res['no_rtl'][:40]))
    bad = bool(res['findings']) or (a.strict and res['no_rtl'])
    print('DIE_PORT_AUDIT ' + ('FAIL' if bad else 'PASS'))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
