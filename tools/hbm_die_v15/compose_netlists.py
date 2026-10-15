#!/usr/bin/env python3
"""Compose a v15 die subnet over per-master SYNTHESISED netlists (H-DIE 2026-10-15).

    compose_netlists.py SUBNET_V NETLIST_DIR OUT_DIR [--map name=dir ...]

Source-level elaboration of the SW subnet timed out twice (5,000 s full, 3,300 s without the IDX body).  This composes
the same structural subnet (tools/hbm_die_v15_subnet.py output) over gate netlists from tools/hbm_die_v15/synth_master.sh:
every instance `M #(.P(v)...) inst (...)` is bound to the netlist of (M, params) -- renamed to a unique module
M__<variant> so parameter variants coexist -- and the parameter override is dropped (it is baked into the netlist).
A master with no netlist is an error (no stub).  Writes OUT_DIR/composed_top.v, OUT_DIR/compose.ys and
OUT_DIR/compose_map.json; compose.ys runs `hierarchy -check`, `check -assert` (undriven / multiply-driven / unknown
cells fail) and `stat` with the ASAP7 libs and the mapped SRAM black boxes.
"""
import argparse, json, re
from pathlib import Path

INST = re.compile(r'^(\s*)([A-Za-z_]\w*)\s*(#\s*\((?:[^()]|\([^()]*\))*\))?\s+([A-Za-z_]\w*)\s*\(\s*$', re.M)


def params_of(s):
    return {k: v.strip() for k, v in re.findall(r'\.(\w+)\s*\(([^()]*)\)', s or '')}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('subnet'); ap.add_argument('netdir'); ap.add_argument('out')
    ap.add_argument('--map', action='append', default=[], help='NAME=SYNTHDIR: (master,params) key json -> synth run name')
    a = ap.parse_args()
    nd, out = Path(a.netdir), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    runs = {}
    for d in sorted(nd.iterdir()):
        ys = d / f'{d.name}.ys'
        nl = d / f'{d.name}.netlist.v'
        if not (ys.exists() and nl.exists()):
            continue
        t = ys.read_text()
        top = re.search(r'hierarchy -check -top (\S+)', t).group(1)
        prm = dict(re.findall(r'chparam -set (\w+) (\S+) ', t))
        bb = re.findall(r'^blackbox (\S+)', t, re.M)
        runs.setdefault(top, []).append(dict(run=d.name, params=prm, netlist=str(nl), blackboxes=bb))
    src = Path(a.subnet).read_text()
    used, binds, missing = {}, [], []

    def norm(v):
        v = v.strip()
        m = re.fullmatch(r"(\d+)?'?[dD]?(\d+)", v)
        return str(int(m.group(2))) if m else v

    def repl(m):
        ind, mod, prm, inst = m.groups()
        p = {k: norm(v) for k, v in params_of(prm).items()}
        cands = [r for r in runs.get(mod, []) if {k: norm(v) for k, v in r['params'].items()} == p and not r['blackboxes']]
        cands = cands or [r for r in runs.get(mod, []) if {k: norm(v) for k, v in r['params'].items()} == p]
        if not cands:
            missing.append(dict(instance=inst, master=mod, params=p))
            return m.group(0)
        r = cands[0]
        new = f'{mod}__{r["run"]}'
        used[new] = r
        binds.append(dict(instance=inst, master=mod, params=p, run=r['run'], blackboxes=r['blackboxes']))
        return f'{ind}{new} {inst} ('
    comp = INST.sub(repl, src)
    (out / 'composed_top.v').write_text(comp)
    top = re.search(r'^module\s+(\w+)', src, re.M).group(1)
    L = ['read_liberty -lib /tmp/lib/all.lib']
    macros = set()
    for new, r in used.items():
        fl = json.loads((Path(r['netlist']).parent / f'{r["run"]}.files.json').read_text())
        for m in fl['macros']:
            macros.add(m['file'])
        # rename the netlist's top module to the variant name (only the module header line)
        nl = Path(r['netlist'])
        mod = re.search(r'^module\s+(\S+?)\s*\(', nl.read_text(errors='replace'), re.M).group(1)
        dst = out / f'{new}.v'
        txt = nl.read_text(errors='replace')
        txt = re.sub(r'^module\s+' + re.escape(mod) + r'\s*\(', f'module {new}(', txt, count=1, flags=re.M)
        dst.write_text(txt)
        L.append(f'read_verilog -icells {dst.name}')
    # black boxes kept inside a master's netlist (e.g. IDX hslices) bind to their own synthesised netlist (unchanged name)
    for new, r in list(used.items()):
        for b in r['blackboxes']:
            rb = [x for x in runs.get(b, []) if not x['params']]
            if not rb:
                missing.append(dict(instance=f'{new}/<{b}>', master=b, params={}))
                continue
            key = f'__bb__{b}'
            if key in used:
                continue
            used[key] = rb[0]
            fl = json.loads((Path(rb[0]['netlist']).parent / f'{rb[0]["run"]}.files.json').read_text())
            for m in fl['macros']:
                macros.add(m['file'])
            (out / f'{b}.v').write_text(Path(rb[0]['netlist']).read_text(errors='replace'))
            L.append(f'read_verilog -icells {b}.v')
    L = L[:1] + [f'read_verilog -lib /src/{m}' for m in sorted(macros)] + L[1:]
    L += ['read_verilog composed_top.v', f'hierarchy -check -top {top}', 'check -assert', 'tee -o compose.stat stat']
    (out / 'compose.ys').write_text('\n'.join(L) + '\n')
    (out / 'compose_map.json').write_text(json.dumps(dict(top=top, binds=binds, missing=missing), indent=1) + '\n')
    print(json.dumps(dict(top=top, bound=len(binds), missing=missing)))
    raise SystemExit(1 if missing else 0)


if __name__ == '__main__':
    main()
