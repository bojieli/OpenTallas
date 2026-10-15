#!/usr/bin/env python3
"""S-NET (2026-10-15): ref_tile kits for the S81 die network masters redesigned to the owner's static-schedule rule.

Inputs are the die generator's own outputs (top-down): the case glue (die_glue.sv rendered with the S-NET flags
--node-static / --sstn-reg / --hend-static, see tools/dsrom_s81_fulldie.py) and the case pin LEF (outline + every pin
centre).  For each master this writes
  rtl/dsrom_sys/s81_static_net/gen/<master>.sv       the glue module text, byte-identical (sha recorded)
  physical/s81_die_pins/snet_<case>/<master>.tcl      place_pin of every pin at the generator centre
  tools/ref_tile/specs_s81_snet/<name>.json           the ref_tile spec (recipe 2), exact bench + observed failing mutants
Outline: the generator slot rounded UP to the 2.16-um lattice (FILL-S RC1: off-lattice slots lose the full-length M5 PG
stripes); a slot that cannot hold the recipe-2 content grows in depth and carries a slot_change_request.

  snet_kits.py --glue G.sv --lef P.lef.gz --counts inst_counts.txt --case TAG [--only M1,M2] [--gen]
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools' / 's81'))
import station_kits_gen18 as K  # noqa: E402  (modules / lef_macros / snap)

RTL_DIR = 'rtl/dsrom_sys/s81_static_net/gen'
SPEC_DIR = 'tools/ref_tile/specs_s81_snet'
SNET = 'rtl/dsrom_sys/s81_static_net'
LANE_CROSS = 'rtl/dsrom_sys/s81_die_bind/ot_s81_static_lane_cross.sv'
NODE_SRC = ['rtl/v41rom/ot_v41_ret.sv', 'rtl/proto/ot_fp32_add_rne_pipe.sv', 'rtl/hdc/ot_hdc_delay.sv',
            f'{SNET}/ot_s81_retn_static.sv']


def kind_of(mst: str) -> str:
    if mst.startswith('dsfd_node_'):
        return 'node'
    if mst.startswith(('dsfd_sstn_', 'dsfd_rstg')):
        return 'sstn'
    if mst.startswith('dsfd_xstg'):
        return 'xstg'
    raise SystemExit(f'{mst}: not an S-NET single-domain master')


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--glue', required=True)
    ap.add_argument('--lef', required=True)
    ap.add_argument('--counts', required=True)
    ap.add_argument('--case', required=True, help='short case tag, e.g. gen18r (pin dir physical/s81_die_pins/snet_<case>)')
    ap.add_argument('--only', required=True)
    ap.add_argument('--owner', default='Claude:s81-net')
    ap.add_argument('--branch', default='claude/el1015-s81-net-static')
    ap.add_argument('--tag', default='n1')
    ap.add_argument('--gen', action='store_true')
    a = ap.parse_args()
    pin_dir = f'physical/s81_die_pins/snet_{a.case}'
    glue_txt = Path(a.glue).read_text()
    glue_sha = hashlib.sha256(glue_txt.encode()).hexdigest()
    mods = K.modules(glue_txt)
    lef_txt = gzip.open(a.lef, 'rt').read() if a.lef.endswith('.gz') else Path(a.lef).read_text()
    macs = K.lef_macros(lef_txt)
    counts = {ln.split()[1]: int(ln.split()[0]) for ln in Path(a.counts).read_text().splitlines() if ln.strip()}
    for d in (RTL_DIR, pin_dir, SPEC_DIR):
        (ROOT / d).mkdir(parents=True, exist_ok=True)
    for mst in a.only.split(','):
        kd = kind_of(mst)
        txt = mods[mst]
        if kd == 'node':
            assert 'ot_s81_retn_static' in txt, f'{mst}: render the glue with --node-static'
        if kd == 'sstn':
            assert '& rs[0]' not in txt, f'{mst}: render the glue with --sstn-reg'
        if kd == 'xstg':
            assert 'ot_s81_static_lane_end' in txt, f'{mst}: render the glue with --hend-static'
        mac = macs[mst]
        dw, dh = K.snap(mac['w']), K.snap(mac['h'])
        sha = hashlib.sha256(txt.encode()).hexdigest()
        (ROOT / RTL_DIR / f'{mst}.sv').write_text('`timescale 1ns/1ps\n' + txt)
        scalar = set(re.findall(r'wire \[0:0\] (\w+)', txt))
        tcl = [f'# {mst}: die generator pin centres ({a.case} pins.lef); outline {dw} x {dh} (slot {mac["w"]} x {mac["h"]} '
               'rounded up to the 2.16-um lattice; N / E pins follow their face)']
        faces = {}
        for p in mac['pins']:
            x, y = p['x'], p['y']
            if p['face'] == 'E':
                x = dw - (mac['w'] - x)
            if p['face'] == 'N':
                y = dh - (mac['h'] - y)
            base = re.sub(r'\[\d+\]$', '', p['pin'])
            pname = re.sub(r'\[0\]$', '', p['pin']) if base in scalar else p['pin']
            tcl.append(f'place_pin -pin_name {{{pname}}} -layer {p["layer"]} -location {{{x:.6f} {y:.6f}}} '
                       '-force_to_die_boundary')
            faces.setdefault(p['face'], set()).add(base)
        ports = re.findall(r'(?:input|output) wire \[\d+:0\] (\w+)', txt)
        missing = [q for q in ports if q not in {b for v in faces.values() for b in v}]
        assert not missing, (mst, missing)
        (ROOT / pin_dir / f'{mst}.tcl').write_text('\n'.join(tcl) + '\n')
        name = f's81net_{mst[5:].lower()}'
        n = counts.get(mst, 0)
        rtl = f'{RTL_DIR}/{mst}.sv'
        if kd == 'node':
            sources = NODE_SRC + [rtl]
            clock, resets = 'clk', ['rst_n']
            bench = 'tools/s81_static_net/bench_node_master.sh'
            benches = [
                {'name': 'node_exact', 'cmd': f'bash {bench} pass {mst} {rtl} {{RUN}}/node_pass', 'expect': 'pass',
                 'pass_regex': 'NODE_STATIC_GATE PASS', 'threads': 2, 'peak_ram_gb': 4},
                {'name': 'node_window_mutant', 'cmd': f'bash {bench} mut_window {mst} {rtl} {{RUN}}/node_mw',
                 'expect': 'fail', 'fail_regex': 'NODE_STATIC', 'threads': 2, 'peak_ram_gb': 4},
                {'name': 'node_fault_chain_mutant', 'cmd': f'bash {bench} mut_fault {mst} {rtl} {{RUN}}/node_mf',
                 'expect': 'fail', 'fail_regex': 'NODE_STATIC', 'threads': 2, 'peak_ram_gb': 4}]
            change = (f'S-NET static return node {mst} ({n} die instances): the ot_v41_retn_w17w10 wrapper (D=64 x 2 queues, '
                      'WAIT-timeout forwarding, older-side-first / yield-to-add arbitration) is replaced by ot_s81_retn_static '
                      '(owner static-schedule rule 10-14 18:59): sibling window WIN=2, every output at edge early+WIN+8, no queue/'
                      'timeout/priority/ready; compiler model tools/s81/static_return_calendar.py; same die ports and leaf packing')
            extra = ['rtl/v41rom', 'rtl/proto', 'rtl/hdc', SNET, 'tools/s81_static_net', 'tools/s81/static_return_calendar.py']
        elif kd == 'sstn':
            sources = [rtl]
            clock, resets = 'ck', ['rs']
            bench = 'tools/s81_static_net/bench_sstn_master.sh'
            benches = [
                {'name': 'sstn_exact', 'cmd': f'bash {bench} pass {mst} {rtl} {{RUN}}/sstn_pass', 'expect': 'pass',
                 'pass_regex': 'SSTN_REG_GATE PASS', 'threads': 1, 'peak_ram_gb': 2},
                {'name': 'sstn_noreset_mutant', 'cmd': f'bash {bench} mut_noreset {mst} {rtl} {{RUN}}/sstn_mut',
                 'expect': 'fail', 'fail_regex': 'SSTN_REG', 'threads': 1, 'peak_ram_gb': 2}]
            change = (f'S-NET {mst} ({n} die instances): the reset-qualified valid is now a column-reset flop at the pin '
                      '(--sstn-reg) instead of flop AND rs behind the output pin (logic after the output register); '
                      + ('the undeclared cc driver removed; ' if mst == 'dsfd_sstn_e0c0' else '') + '0 cycles, same ports')
            extra = [SNET, 'tools/s81_static_net']
        else:
            sources = [LANE_CROSS, f'{SNET}/ot_s81_static_lane_end.sv', rtl]
            clock, resets = 'ck', []
            bench = 'tools/s81_static_net/bench_xstg_master.sh'
            benches = [
                {'name': 'xstg_exact', 'cmd': f'bash {bench} pass {mst} {rtl} {{RUN}}/xstg_pass', 'expect': 'pass',
                 'pass_regex': 'XSTG_STATIC_GATE PASS', 'threads': 1, 'peak_ram_gb': 2},
                {'name': 'xstg_offset_mutant', 'cmd': f'bash {bench} mut_offset {mst} {rtl} {{RUN}}/xstg_mut',
                 'expect': 'fail', 'fail_regex': 'XSTG', 'threads': 1, 'peak_ram_gb': 2}]
            change = (f'S-NET {mst} ({n} die instances): the d8g1 ot_meso_fifo (trained placement + CREDITS 16) is replaced by '
                      'ot_s81_static_lane_end (cw pin register, epoch from the lane marker, fixed-offset crossing, no credit/'
                      'ready/placement), o = {data, valid & live, live}')
            extra = ['rtl/dsrom_sys/s81_die_bind', SNET, 'tools/s81_static_net', 'physical/s81_static_net']
        spec = {
            'name': name, 'top': mst, 'kind': 'tile', 'sources': sources, 'params': {},
            'clock_port': clock, 'reset_ports': resets,
            'outline': {'w': dw, 'h': dh, 'exact': True}, 'layer_cap': 'M5',
            'pins': {f: sorted(v) for f, v in sorted(faces.items())},
            'io_tcl': f'{pin_dir}/{mst}.tcl', 'recipe': 2,
            'route': {'pd': 0.5, 'threads': 4, 'peak_ram_gb': 8, 'pin_h': 'M4', 'pin_v': 'M3 M5', 'm5_pg_pitch': 2.7},
            'structural_change': change + f'; RTL = the case glue module rendered by the generator (module sha256 {sha[:16]}, '
                                          f'glue {glue_sha[:16]}); pins at the generator centres ({a.case}).',
            'reroute_reason': {'kind': 'rtl_change'},
            'job': {'owner': a.owner, 'branch': a.branch, 'tag': a.tag,
                    'purpose': f'S81 S-NET static-schedule redesign: {mst} ({n} replicas, hardened once): exact bench + '
                               'observed failing mutants; recipe 2, M5 cap, generator pins',
                    'views_to': f'physical/ref_tile/{name}/views', 'record_to': f'results/rtl/ref_tile/{name}',
                    'extra_paths': [RTL_DIR, pin_dir] + extra, 'benches': benches}}
        if kd == 'xstg':
            spec['sdc_extra'] = ['physical/s81_static_net/xstg/dsfd_xstg_515.sdc']
            spec['boundary_tcl'] = ['physical/s81_static_net/xstg/dsfd_xstg_515_boundary.tcl']
        p = ROOT / SPEC_DIR / f'{name}.json'
        p.write_text(json.dumps(spec, indent=1) + '\n')
        print(f'{mst:28s} n={n:<5d} slot {mac["w"]}x{mac["h"]} -> {dw}x{dh}  {name}')
        if a.gen:
            r = subprocess.run([sys.executable, str(ROOT / 'tools/ref_tile/ref_tile.py'), 'gen', str(p)],
                               capture_output=True, text=True, cwd=ROOT)
            last = (r.stdout + r.stderr).strip().splitlines()[-3:]
            print('   gen rc', r.returncode, ' | '.join(x[:160] for x in last))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
