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


# hand RTL outside rtl/ (s81die-1011/ctrl): the host ingest master lives with its physical package
RTL_ROOTS = ('rtl', 'physical/rom_host_ingest/rtl')
# hard-macro VIEWS (black-box port lists of the LEF'd macros), compared pin for pin but reported as views, not RTL
VIEWS = {'ot_rom_4096x72_m8': 'physical/asap7_memory_macros_v2/ot_rom_4096x72_m8/ot_rom_4096x72_m8_bb.v',
         'ot_hbm3e_phy_v41x_aw30_e8p5': 'physical/asap7_memory_macros_v2/ot_hbm3e_phy_v41x_aw30_e8p5/'
                                        'ot_hbm3e_phy_v41x_aw30_e8p5_bb.v',
         'ot_pdie_serdes': 'physical/asap7_v41x_pdie_macros_v2/ot_pdie_serdes/ot_pdie_serdes_bb.v',
         'ot_pdie_ucie': 'physical/asap7_v41x_pdie_macros_v2/ot_pdie_ucie/ot_pdie_ucie_bb.v'}


def _ports_from_text(module, t):
    m = re.search(rf'module\s+{re.escape(module)}\b.*?\)\s*\(\s*(.*?)\)\s*;', t, re.S) or \
        re.search(rf'module\s+{re.escape(module)}\b\s*\(\s*(.*?)\)\s*;', t, re.S)
    return _parse_body(m) if m else {}


def rtl_ports(module, text=None, path=None):
    """{port: (direction, bits or None)} from the RTL source of `module` (ANSI port list; widths from literal ranges);
    `text` = an already generated source (the case's glue RTL), `path` = a given file (a macro view)."""
    if text is not None:
        return _ports_from_text(module, text) if re.search(rf'^\s*module\s+{re.escape(module)}\b', text, re.M) else None
    if path is not None:
        return _ports_from_text(module, (ROOT / path).read_text()) if (ROOT / path).exists() else None
    # filesystem scan (the audit also runs in extracted source trees that are not git checkouts)
    r = subprocess.run(['grep', '-rlE', '--include=*.sv', '--include=*.v', rf'^\s*module\s+{re.escape(module)}\b',
                        *[d for d in RTL_ROOTS if (ROOT / d).exists()]], cwd=ROOT, capture_output=True, text=True)
    files = sorted(f for f in r.stdout.split() if f and '/test/' not in f and '/tb' not in f)
    if not files:
        return None
    t = (ROOT / files[0]).read_text()
    return _ports_from_text(module, t)


def _parse_body(m):
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


def _expand_real(die, gmap):
    """die pins of a real-macro master are pin GROUPS (generator r8 binding, real_ports_r8): {group: (dir, bits)} ->
    {macro port base: (dir, bits bound)}; a group the binding does not map stays as is (-> placeholder finding)"""
    out = {}
    for g, v in die.items():
        if g not in gmap:
            out[g] = v
            continue
        for pin in gmap[g]:
            b = re.sub(r'\[\d+\]$', '', pin)
            d_, n_ = out.get(b, (v[0], 0))
            out[b] = (d_, n_ + 1)
    return out


def audit(m, glue_out=None, absent=None):
    """glue masters (tools/dsrom_s81_fulldie.py GLUE_PREFIX: stations, relays, lane ends, FIFOs, nodes) are read from
    THIS die's generated glue RTL (glue_rtl(m): structural over ot_fwd_link_stage / ot_meso_fifo / ot_ratio_cdc_fifo /
    ot_v41_retn_w17w10), written to glue_out when given, the way die_top_lint binds them; macro views by their bb."""
    pdir = m.get('pdir') or {}
    masters = sorted({it.master for it in m['insts']})
    out = dict(masters=len(masters), no_rtl=[], findings={}, views=[], glue=0)
    glue_txt = None
    try:
        import dsrom_s81_fulldie as F
        if m.get('glue') is not None:
            glue_txt = F.glue_rtl(m)
            if glue_out:
                Path(glue_out).write_text(glue_txt)
    except Exception as e:       # no glue model: glue masters fall back to the tree scan (reported, not waived)
        out['glue_error'] = repr(e)[:300]
    try:     # real macros / the routed q element: die pin groups -> macro pins (the generator's r8 binding)
        real_map = F.real_ports_r8()
    except Exception as e:
        real_map = {}
        out['real_map_error'] = repr(e)[:300]
    for ms in masters:
        die = pdir.get(ms, {})
        if ms in VIEWS:
            rp = rtl_ports(ms, path=VIEWS[ms])
            out['views'].append(dict(master=ms, view=VIEWS[ms], found=rp is not None))
        elif glue_txt is not None and F.is_glue(ms):
            rp = rtl_ports(ms, text=glue_txt)
            out['glue'] += rp is not None
        else:
            rp = rtl_ports(ms)
        if rp is None:
            out['no_rtl'].append(dict(master=ms, die_pins=len(die)))
            continue
        if ms in real_map:
            die = _expand_real(die, real_map[ms])
        f = dict(unbound=[], placeholder=[], width=[])
        dec = (absent or {}).get(ms, {})
        for p, (d, w) in rp.items():
            if CTRL.match(p):
                continue
            if p not in die and p in dec:
                ok_ = (dec[p] == 'open') == (d == 'output') and \
                      (d == 'output' or (w is None or re.match(rf'^{w}\'', str(dec[p])) is not None))
                out.setdefault('declared_absent', []).append(dict(master=ms, port=p, dir=d, bits=w, value=dec[p], ok=ok_))
                if not ok_:
                    f['unbound'].append(f'{d} {p}[{w}] (declared absent as {dec[p]}: direction / width mismatch)')
                continue
            if p not in die:
                f['unbound'].append(f'{d} {p}[{w}]')
            elif w and die[p][1] != w:
                sp_ = f'{p}[{die[p][1]}:{w - 1}]'       # a declared unused upper slice (e.g. ROM spare columns)
                if die[p][1] < w and dec.get(sp_) == 'open' and d == 'output':
                    out.setdefault('declared_absent', []).append(dict(master=ms, port=sp_, dir=d, bits=w - die[p][1],
                                                                      value='open', ok=True))
                    continue
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
