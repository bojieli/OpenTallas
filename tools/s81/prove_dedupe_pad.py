#!/usr/bin/env python3
"""Prove every declared S81 width rebind against generated real original RTL.

Writes actual die netlist and per-instance PAD sidecar through write_netlist,
then binds actual modules and checks every output on both clock edges plus reset.
Run heavy simulation through ot-run; --prepare writes portable input artifacts only.
"""
import argparse
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import dsrom_s81_fulldie as G


ACTUAL_MODULES = ROOT / 'results/arch/native_pin_audit_snetfill_1015/dedupe_pad_1016/actual_modules.sv'

def ports(master):
    import die_port_bind as B
    mods = {m.name: m for m in B.parse_modules(ACTUAL_MODULES.read_text(), str(ACTUAL_MODULES))}
    mod = mods[master]
    return {pn: (direction, mod.width(pn, mod.env({}))) for pn, (direction, _) in mod.ports.items()}


def prepare(out, mapping):
    out.mkdir(parents=True, exist_ok=True)
    G.HSTN_POSEDGE = True
    G.RTL_BIND = False
    G.DEDUPE_PAD = dict(path='actual_map', map=mapping)
    G.STN_FOOTPRINTS = {}
    G.bound_views = lambda: {}
    G.real_ports = lambda: {}
    G.real_lef = lambda _: dict(name='unused', pins=[])
    G.die_master_params = lambda _: {}
    insts, buses, pd = [], [], {}
    tb, refs, checks, drives, connections = [], [], [], [], []
    for j, (frm, ent) in enumerate(sorted(mapping.items())):
        name = f'u{j}'
        insts.append(G.Inst(name, frm, 0, 0, 10, 10))
        pd[frm] = ports(frm)
        pd[ent['to']] = ports(ent['to'])
        for pn, pv in pd[frm].items():
            if pn not in ent['ports']:
                assert pd[ent['to']].get(pn) == pv, (frm, ent['to'], pn, 'non-data ABI mismatch')
        assert all(pn in pd[frm] or pv[0] == 'output' for pn, pv in pd[ent['to']].items()), (frm, ent['to'], 'extra canonical input')
        refconns = []
        for pn, (direction, w) in pd[frm].items():
            net = f'p{j}_{pn}'
            if direction == 'input':
                expr = 'rst_n' if pn == 'rs' else ('ck' if pn in ('ck', 'fi0') else net)
                tb.append(f'reg [{w-1}:0] {net};' if expr == net else '')
                if expr == net:
                    drives.append(f'{net} = {{$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random}};')
                connections.append(f'.{net}({expr})')
                refconns.append(f'.{pn}({expr})')
                buses.append((net, 'top_in', w, [('TOP', net), (name, pn)]))
            else:
                tb.append(f'wire [{w-1}:0] {net}, ref_{net};')
                connections.append(f'.{net}({net})')
                refconns.append(f'.{pn}(ref_{net})')
                checks.append(f'if ({net} !== ref_{net}) $fatal(1,"logical output mismatch {frm}.{pn} edge%0d",n);')
                buses.append((net, 'top_out', w, [(name, pn), ('TOP', net)]))
        refs.append(f'{frm} ref{j} ('+', '.join(refconns)+');')
    model = dict(insts=insts, buses=buses, pdir=pd, glue={})
    G._dedupe_pad(model)
    assert len(model['pad']) == len(mapping)
    # This is exactly the width promotion performed by finalize_r8, isolated from geometry planning.
    use = G.port_usage(model)
    final_pd = defaultdict(dict)
    for it in model['insts']:
        for pn, (direction, logical) in use[it.name].items():
            w = G.pad_std(model['pad'][it.name], pn) if pn in model['pad'][it.name]['ports'] else logical
            assert not (pn in final_pd[it.master]) or final_pd[it.master][pn] == (direction,w)
            final_pd[it.master][pn] = (direction,w)
    model['pdir'] = final_pd
    G.write_netlist(model, 1, out/'die.v', top='dedupe_die')
    # The DUT and reference instantiate byte-exact actual c26b source modules / canonical hardening RTL.
    # In particular horizontal forwarded stations have no fn0, unlike the vertical canonical station.
    (out/'masters.sv').write_text(ACTUAL_MODULES.read_text())
    body = '\n'.join(tb+refs+['dedupe_die dut ('+', '.join(connections)+');'])
    body += '\ninitial begin ck=0;rst_n=0; for(n=0;n<2000;n=n+1) begin\n'
    body += '\n'.join(drives)+'\n#2;ck=1;#1;\n'+'if(n>0) begin\n'+'\n'.join(checks)+'\nend'
    # First rising edge precedes the forwarded lane first declared falling capture; compare it from edge 1.
    body += '\n#2;ck=0;#1;\n'+'\n'.join(checks)
    body += '\nif(n%53==0) begin rst_n=0;#1;end else begin rst_n=1;#1;end\nend\n$display("DEDUPE_PAD_EXACT PASS 30 mappings 2000 cycles both edges; generated original RTL vs padded standard");$finish;end\n'
    (out/'tb.sv').write_text('`timescale 1ns/1ps\nmodule tb;reg ck,rst_n;integer n;\n'+body+'\nendmodule\n')
    (out/'ot_fwd_link_stage.sv').write_text((ROOT/'rtl/common/ot_fwd_link_stage.sv').read_text())
    (out/'mapping.json').write_text(json.dumps(mapping,indent=1))
    # Binding positives and logical-tie mutant at same master with differing logical widths.
    return model


KCOPY_FROM_RTL = ROOT / 'results/arch/native_pin_audit_snetfill_1015/kcopy_proof_1016/from_modules.sv'


def _modules(*paths):
    import die_port_bind as B
    out = {}
    for p_ in paths:
        for m_ in B.parse_modules(Path(p_).read_text(), str(p_)):
            out[m_.name] = m_
    return out


def _mports(mod):
    return {pn: (d, mod.width(pn, mod.env({}))) for pn, (d, _) in mod.ports.items()}


def to_sources(master):
    """the RTL a CLOSED standard was hardened from: physical/ref_tile/<job dir>/spec.json 'sources' (the view-binding
    table names the view's export directory under that job dir)"""
    tab = json.loads((ROOT / 'results/arch/s81_native_20261013/view_binding_closed_codex0912_split.json').read_text())['bound']
    d_ = Path(tab[master]['files']['lef']['path']).parts
    spec = json.loads((ROOT / Path(*d_[:3]) / 'spec.json').read_text())
    assert spec['top'] == master, (master, spec['top'])
    return [ROOT / s_ for s_ in spec['sources']]


def mutate(km, mutant):
    """deliberate defects the bench must reject: 'swap' (hstnv_4096: the two copies take each other's di slice),
    'droppad' (l2r hx_E copy B loses its lane-valid chunk i[0]: its spare pad then starts one bit low)"""
    km = json.loads(json.dumps(km))
    if mutant == 'swap':
        c0, c1 = km['dsfd_hstnv_4096']['copies']
        c0['ports']['di'], c1['ports']['di'] = [['di', 2047, 4095]], [['di', 0, 2046]]
    elif mutant == 'droppad':
        km['dsfd_l2r_vr_1100x1__hx_E']['copies'][1]['ports']['i'] = [['i', 565, 1100]]
    else:
        assert mutant == 'none', mutant
    return km


def prepare_kcopy(out, km, from_rtl, cycles=2000):
    """The generator's own k-copy (G._dedupe_kcopy + write_netlist) on one instance of every FROM master, each wired
    through a pass-through io block (so the cut nets slice a non-copied endpoint too), against the FROM master itself;
    TO = the closed views' hardening RTL.  Every output compared at every rising edge (and after the falling edge)."""
    out.mkdir(parents=True, exist_ok=True)
    G.HSTN_POSEDGE, G.RTL_BIND, G.HEND_STATIC = True, False, True
    G.STN_FOOTPRINTS = {}
    G.DEDUPE_PAD = dict(path='kcopy_map', map={}, kcopy=km)
    tos = sorted({c['to'] for e in km.values() for c in e['copies']})
    srcs = []
    for t in tos:
        srcs += [s_ for s_ in to_sources(t) if s_ not in srcs]
    tmods = _modules(*srcs)
    fmods = _modules(from_rtl)
    def bv():
        return {t: dict(w=40.0 + 10 * i, h=30.0 + 5 * i,
                        pins={(f'{pn}[{b}]' if w_ > 1 else pn): d.upper() for pn, (d, w_) in _mports(tmods[t]).items()
                              for b in range(w_)}) for i, t in enumerate(tos)}
    G.bound_views = bv
    G.real_ports = lambda: {}
    G.real_lef = lambda _: dict(name='unused', pins=[])
    G.die_master_params = lambda _: {}
    G.DIE = (5000.0, 5000.0)
    insts, buses, glue, io_mods, tb, refs, chk, drv, conns = [], [], {}, [], [], [], [], [], []
    for j, frm in enumerate(sorted(km)):
        fm = _mports(fmods[frm])
        hend = '__' in frm
        name = frm.split('__', 1)[1] if hend else f'u{j}'
        mst = frm.split('__', 1)[0] if hend else frm
        if hend:
            g_ = re.fullmatch(r'dsfd_(l2r)_([a-z0-9]+)_(\d+)x1', mst)
            glue[mst] = dict(kind=g_.group(1), lanes=[int(g_.group(3))], fmt=g_.group(2))
        insts.append(G.Inst(name, mst, 400.0 * j, 1000.0, 60.0, 60.0, 'R0', kind='hend' if hend else 'hstn'))
        io = G.Inst(f'io{j}', f'kcio{j}', 400.0 * j, 3000.0, 20.0, 20.0, 'R0', kind='io')
        insts.append(io)
        ml = [f'module kcio{j} (']
        mp = []
        refc = []
        for pn, (d, w) in fm.items():
            t = f'p{j}_{pn}'
            if d == 'input':
                if pn in ('ck', 'cks'):
                    ex = 'ck'
                elif pn in ('rs', 'rss'):
                    ex = 'rst_n'
                else:
                    ex = t
                    tb.append(f'reg [{w - 1}:0] {t};')
                    drv.append(f'for (k = 0; k < {w}; k = k + 32) {t}[k +: 32] = $random;' if w > 32 else f'{t} = $random;')
                mp += [f'input [{w - 1}:0] t_{pn}', f'output [{w - 1}:0] {pn}']
                ml.append(f'  assign {pn} = t_{pn};')
                buses.append((t, 'top_in', w, [('TOP', t), (io.name, f't_{pn}')]))
                buses.append((f'q{j}_{pn}', 'local', w, [(io.name, pn), (name, pn)]))
                conns.append(f'.{t}({ex})')
                refc.append(f'.{pn}({ex})')
            else:
                tb.append(f'wire [{w - 1}:0] {t}, ref_{t};')
                mp += [f'input [{w - 1}:0] {pn}', f'output [{w - 1}:0] t_{pn}']
                ml.append(f'  assign t_{pn} = {pn};')
                buses.append((f'q{j}_{pn}', 'local', w, [(name, pn), (io.name, pn)]))
                buses.append((t, 'top_out', w, [(io.name, f't_{pn}'), ('TOP', t)]))
                conns.append(f'.{t}({t})')
                refc.append(f'.{pn}(ref_{t})')
                chk.append(f'if ({t} !== ref_{t}) begin err = err + 1; if (err < 6) $display("KCOPY_MISMATCH {frm}.{pn} cycle %0d", n); end')
        io_mods.append(ml[0] + ', '.join(mp) + ');\n' + '\n'.join(ml[1:]) + '\nendmodule')
        refs.append(f'{frm} ref{j} (' + ', '.join(refc) + ');')
    model = dict(insts=insts, buses=buses, pdir={}, glue=glue)
    G._dedupe_kcopy(model, km)
    use = G.port_usage(model)
    pd = defaultdict(dict)
    for it in model['insts']:
        pr_ = (model.get('pad') or {}).get(it.name)
        for pn, (d, lg) in use[it.name].items():
            w = G.pad_std(pr_, pn) if pr_ and pn in pr_['ports'] else lg
            assert pd[it.master].get(pn, (d, w)) == (d, w), (it.master, pn, pd[it.master].get(pn), (d, w))
            pd[it.master][pn] = (d, w)
    model['pdir'] = pd
    G.write_netlist(model, 1, out / 'die.v', top='kcopy_die')
    (out / 'io.sv').write_text('\n'.join(io_mods) + '\n')
    (out / 'to_modules.f').write_text('\n'.join(str(s_.relative_to(ROOT)) for s_ in srcs) + '\n')
    for s_ in srcs:
        (out / s_.name).write_text(s_.read_text())
    (out / 'from_modules.sv').write_text(Path(from_rtl).read_text())
    body = '\n'.join(tb + refs + ['kcopy_die dut (' + ', '.join(conns) + ');'])
    body += ('\ninitial begin ck = 0; rst_n = 0; err = 0;\n'
             f'for (n = 0; n < {cycles}; n = n + 1) begin\n' + '\n'.join(drv) +
             '\nif (n == 3) rst_n = 1; if (n == 1000) rst_n = 0; if (n == 1010) rst_n = 1;'
             '\n#2; ck = 1; #1;\n' + '\n'.join(chk) + '\n#2; ck = 0; #1;\n' + '\n'.join(chk) + '\nend\n'
             f'if (err == 0) $display("KCOPY_EXACT PASS {len(km)} FROM masters {cycles} cycles every output both edges incl. mid-run reset");'
             '\nelse begin $display("KCOPY_FAIL %0d mismatches", err); $fatal(1); end\n$finish; end\n')
    (out / 'tb.sv').write_text('`timescale 1ns/1ps\nmodule tb; reg ck, rst_n; integer n, k, err;\n' + body + '\nendmodule\n')
    (out / 'run.sh').write_text('#!/bin/bash\nset -uo pipefail\ncd "$(dirname "$0")"\n'
                               'iverilog -g2012 -s tb -o kc.vvp tb.sv die.v io.sv from_modules.sv '
                               + ' '.join(s_.name for s_ in srcs) + ' && vvp kc.vvp\n')
    rec = dict(kcopy=model['kcopy'], pads=json.loads((out / 'die.v.pads.json').read_text()) if (out / 'die.v.pads.json').exists() else None,
               kcopy_nc=model.get('kcopy_nc'), pad={k_: v_ for k_, v_ in (model.get('pad') or {}).items()})
    (out / 'model.json').write_text(json.dumps(rec, indent=1, default=str) + '\n')
    return model


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);ap.add_argument('--map',default='results/arch/tile_dedupe_1015/s81_pad_map_1016.json');ap.add_argument('--prepare',action='store_true')
    ap.add_argument('--kcopy', action='store_true', help="prove the map's 'kcopy' section (S-DIE-KCOPY 2026-10-16)")
    ap.add_argument('--from-rtl', default=str(KCOPY_FROM_RTL))
    ap.add_argument('--mutant', default='none', choices=['none', 'swap', 'droppad'])
    a=ap.parse_args()
    out=Path(a.out).resolve()
    if a.kcopy:
        km = mutate(json.loads((ROOT/a.map).read_text())['kcopy'], a.mutant)
        md = prepare_kcopy(out, km, a.from_rtl)
        print(f'PREPARED_KCOPY {out} mutant={a.mutant} {md["kcopy"]["instances"]} instances -> {md["kcopy"]["copies"]} copies')
        return 0
    mapping=json.loads((ROOT/a.map).read_text())['map'];prepare(out,mapping)
    print(f'PREPARED {out} {len(mapping)} mappings / {sum(e["instances"] for e in mapping.values())} census instances')
    return 0

if __name__=='__main__':raise SystemExit(main())
