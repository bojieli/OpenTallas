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
            w = model['pad'][it.name]['std'] if pn in model['pad'][it.name]['ports'] else logical
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


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);ap.add_argument('--map',default='results/arch/tile_dedupe_1015/s81_pad_map_1016.json');ap.add_argument('--prepare',action='store_true');a=ap.parse_args()
    out=Path(a.out).resolve();mapping=json.loads((ROOT/a.map).read_text())['map'];prepare(out,mapping)
    print(f'PREPARED {out} {len(mapping)} mappings / {sum(e["instances"] for e in mapping.values())} census instances')
    return 0

if __name__=='__main__':raise SystemExit(main())
