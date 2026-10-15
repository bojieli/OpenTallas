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
NODE_SRC = ['rtl/proto/ot_fp32_add_rne_pipe.sv', 'rtl/hdc/ot_hdc_delay.sv',
            f'{SNET}/ot_s81_retn_static.sv']


def kind_of(mst: str) -> str:
    if mst.startswith('dsfd_node_'):
        return 'node'
    if mst.startswith(('dsfd_sstn_', 'dsfd_rstg')):
        return 'sstn'
    if mst.startswith('dsfd_xstg'):
        return 'xstg'
    if re.match(r'dsfd_(m2l|r2l|l2r)_', mst):
        return 'hend'
    raise SystemExit(f'{mst}: not an S-NET single-domain master')


HEND_DIR = 'physical/s81_static_net/hend'
RATIO_SRC = f'{SNET}/ot_s81_static_ratio_cross.sv'


def hend_sdc(mst: str, txt: str) -> tuple[str, str]:
    """(route SDC, POST_CTS boundary) of a --hend-static end / start block.  Clock names follow make_sdc_hend.sh
    (core_clk, w_*, vclk, vw) so the boundary re-sets the virtual clocks to the measured insertion.  Crossing arcs: the
    static lane end / ratio cross read a slot written >= 4.5 VCO ticks (1,250 ps) earlier -> 1,190 ps max delay, as the
    d8g1 meso it replaces; a same-clock start (ck and cks are one die net) has no exception at all."""
    kind = mst[5:8]
    ratio = 'ot_s81_static_ratio_cross' in txt
    L = []
    io = []
    if kind == 'm2l':
        L += ['create_clock -name core_clk -period 833.333 [get_ports {ck[0]}]', 'set ot_w {}',
              'foreach p [get_ports {fi*}] { set n [get_property $p name]; regsub {\\[0\\]} $n {} b; create_clock -name w_$b -period 833.333 $p; lappend ot_w w_$b }',
              'create_clock -name vclk -period 833.333', 'create_clock -name vw -period 833.333']
        cross = ['foreach w $ot_w {', '  set_max_delay -ignore_clock_latency 1190.0 -from [get_clocks $w] -to [get_clocks core_clk]',
                 '  set_max_delay -ignore_clock_latency 1190.0 -from [get_clocks core_clk] -to [get_clocks $w]',
                 '  set_min_delay -ignore_clock_latency 0 -from [get_clocks $w] -to [get_clocks core_clk]',
                 '  set_min_delay -ignore_clock_latency 0 -from [get_clocks core_clk] -to [get_clocks $w]',
                 '  set_false_path -from [get_clocks vw] -to [get_clocks core_clk]', '  set_false_path -from [get_clocks core_clk] -to [get_clocks vw]',
                 '  set_false_path -from [get_clocks $w] -to [get_clocks vclk]', '  set_false_path -from [get_clocks vclk] -to [get_clocks $w]',
                 '  foreach w2 $ot_w { if {$w2 ne $w} { set_false_path -from [get_clocks $w] -to [get_clocks $w2] } }', '}',
                 'set_false_path -from [get_clocks vw] -to [get_clocks vclk]']
        io = ['set_input_delay 166.667 -clock vw [get_ports {di*}]', 'set_input_delay -min 0 -clock vw [get_ports {di*}]',
              'set_output_delay 316.667 -clock vclk [get_ports {o*}]', 'set_output_delay -min 0 -clock vclk [get_ports {o*}]']
    elif kind == 'r2l':
        L += ['create_clock -name w_fi0 -period 833.331 [get_ports {fi0[0]}]', 'create_clock -name core_clk -period 1111.108 [get_ports {ck[0]}]',
              'create_clock -name vw -period 833.331', 'create_clock -name vclk -period 1111.108']
        cross = ['set_max_delay -ignore_clock_latency 1190.0 -from [get_clocks w_fi0] -to [get_clocks core_clk]',
                 'set_min_delay -ignore_clock_latency 0 -from [get_clocks w_fi0] -to [get_clocks core_clk]',
                 'set_false_path -from [get_clocks vw] -to [get_clocks {core_clk vclk}]', 'set_false_path -from [get_clocks w_fi0] -to [get_clocks vclk]']
        io = ['set_input_delay 166.666 -clock vw [get_ports {di*}]', 'set_input_delay -min 0 -clock vw [get_ports {di*}]',
              'set_output_delay 372.222 -clock vclk [get_ports {o*}]', 'set_output_delay -min 0 -clock vclk [get_ports {o*}]']
    else:
        per = '1111.108' if ratio else '833.333'
        L += [f'create_clock -name core_clk -period {per} [get_ports {{ck[0]}}]', 'create_clock -name w_cks -period 833.333 [get_ports {cks[0]}]',
              f'create_clock -name vclk -period {per}', 'create_clock -name vw -period 833.333']
        cross = (['set_max_delay -ignore_clock_latency 1190.0 -from [get_clocks core_clk] -to [get_clocks w_cks]',
                  'set_min_delay -ignore_clock_latency 0 -from [get_clocks core_clk] -to [get_clocks w_cks]',
                  'set_max_delay -ignore_clock_latency 1190.0 -from [get_clocks w_cks] -to [get_clocks core_clk]',
                  'set_min_delay -ignore_clock_latency 0 -from [get_clocks w_cks] -to [get_clocks core_clk]'] if ratio else []) + \
                ['set_false_path -from [get_clocks vclk] -to [get_clocks w_cks]', 'set_false_path -from [get_clocks core_clk] -to [get_clocks vw]']
        io = [f'set_input_delay {0.2 * float(per):.3f} -clock vclk [get_ports {{i*}}]', 'set_input_delay -min 0 -clock vclk [get_ports {i*}]',
              'set_output_delay 316.667 -clock vw [get_ports {od*}]', 'set_output_delay -min 0 -clock vw [get_ports {od*}]',
              'set_false_path -to [get_ports {fo*}]']
        if 'output wire [2:0] st' in txt:
            io += [f'set_output_delay {0.2 * float(per):.3f} -clock vclk [get_ports {{st*}}]', 'set_output_delay -min 0 -clock vclk [get_ports {st*}]']
        if 'input wire' in txt and ' xf' in txt:
            io += [f'set_input_delay {0.2 * float(per):.3f} -clock vclk [get_ports {{xf*}}]', 'set_input_delay -min 0 -clock vclk [get_ports {xf*}]']
    if kind != 'l2r' and ' xf' in txt:
        io += ['set_input_delay 166.667 -clock vclk [get_ports {xf*}]', 'set_input_delay -min 0 -clock vclk [get_ports {xf*}]']
    io += ['set_false_path -from [get_ports {rs*}]']
    head = [f'# S-NET {mst} (--hend-static): fixed-calendar crossing, no FIFO / credit / ready']
    sdc = '\n'.join(head + L + ['set_clock_latency 0 [get_clocks {vclk vw}]', 'set_clock_uncertainty -setup 123 [all_clocks]',
                               'set_clock_uncertainty -hold 25 [all_clocks]'] + cross + io + ['set_max_fanout 32 [current_design]']) + '\n'
    post = (ROOT / 'physical/s81_die_views/glue/post_cts_hend.tcl').read_text()
    bnd = '\n'.join(['set ::ot_ref_pre_cts 0', 'set_propagated_clock [get_clocks {core_clk w_*}]', 'unset_input_delay [all_inputs]',
                     'unset_output_delay [all_outputs]', post] + io) + '\n'
    return sdc, bnd


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
        if kd == 'hend':
            assert 'ot_meso_fifo' not in txt and 'ot_ratio_cdc_fifo' not in txt, f'{mst}: render the glue with --hend-static'
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
                 'expect': 'fail', 'fail_regex': 'GATE MUTANT .*REJECTED', 'threads': 2, 'peak_ram_gb': 4},
                {'name': 'node_fault_chain_mutant', 'cmd': f'bash {bench} mut_fault {mst} {rtl} {{RUN}}/node_mf',
                 'expect': 'fail', 'fail_regex': 'GATE MUTANT .*REJECTED', 'threads': 2, 'peak_ram_gb': 4}]
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
                 'expect': 'fail', 'fail_regex': 'GATE MUTANT .*REJECTED', 'threads': 1, 'peak_ram_gb': 2}]
            change = (f'S-NET {mst} ({n} die instances): the reset-qualified valid is now a column-reset flop at the pin '
                      '(--sstn-reg) instead of flop AND rs behind the output pin (logic after the output register); '
                      + ('the undeclared cc driver removed; ' if mst == 'dsfd_sstn_e0c0' else '') + '0 cycles, same ports')
            extra = [SNET, 'tools/s81_static_net']
        elif kd == 'hend':
            sources = [LANE_CROSS, f'{SNET}/ot_s81_static_lane_end.sv', RATIO_SRC, rtl]
            clock, resets = 'ck', ['rs'] + (['rss'] if 'input wire [0:0] rss' in txt else [])
            bench = 'tools/s81_static_net/bench_hend_master.sh'
            if re.search(r'_vs[01]_1x1__', mst):   # status lane: start + end pair bench (partner RTL in the same dir)
                benches = [
                    {'name': 'status_pair_exact', 'cmd': f'bash tools/s81_static_net/bench_status_master.sh pass {mst} {rtl} {{RUN}}/st_pass',
                     'expect': 'pass', 'pass_regex': 'STATUS_STATIC_GATE PASS', 'threads': 1, 'peak_ram_gb': 2},
                    {'name': 'status_delay_mutant', 'cmd': f'bash tools/s81_static_net/bench_status_master.sh mut_offset {mst} {rtl} {{RUN}}/st_mut',
                     'expect': 'fail', 'fail_regex': 'GATE MUTANT .*REJECTED', 'threads': 1, 'peak_ram_gb': 2}]
            else:
                benches = [
                {'name': 'hend_exact', 'cmd': f'bash {bench} pass {mst} {rtl} {{RUN}}/hend_pass', 'expect': 'pass',
                 'pass_regex': 'HEND_STATIC_GATE PASS', 'threads': 1, 'peak_ram_gb': 4},
                {'name': 'hend_offset_mutant', 'cmd': f'bash {bench} mut_offset {mst} {rtl} {{RUN}}/hend_mut',
                 'expect': 'fail', 'fail_regex': 'GATE MUTANT .*REJECTED', 'threads': 1, 'peak_ram_gb': 4}]
            how = ('ot_s81_static_ratio_cross (fixed source-edge map, compiled bubble phase)' if 'ratio_cross' in txt else
                   'ot_s81_static_lane_end (pin register, marker epoch, fixed offset)' if 'lane_end' in txt else
                   'a same-clock pin pipeline (ck and cks are one die net)')
            change = (f'S-NET {mst} ({n} die instance(s)): the ot_meso_fifo (trained placement + CREDITS) / ot_ratio_cdc_fifo '
                      f'(ready + DOWN/WAIT/RUN handshake) crossing is replaced by {how}, owner static-schedule rule 10-14 18:59; '
                      'same ports and lane formats, {fault, live} folded as before')
            extra = ['rtl/dsrom_sys/s81_die_bind', SNET, 'tools/s81_static_net', HEND_DIR]
            sdc, bnd = hend_sdc(mst, txt)
            (ROOT / HEND_DIR).mkdir(parents=True, exist_ok=True)
            (ROOT / HEND_DIR / f'{mst}.sdc').write_text(sdc)
            (ROOT / HEND_DIR / f'{mst}_boundary.tcl').write_text(bnd)
        else:
            sources = [LANE_CROSS, f'{SNET}/ot_s81_static_lane_end.sv', rtl]
            clock, resets = 'ck', []
            bench = 'tools/s81_static_net/bench_xstg_master.sh'
            benches = [
                {'name': 'xstg_exact', 'cmd': f'bash {bench} pass {mst} {rtl} {{RUN}}/xstg_pass', 'expect': 'pass',
                 'pass_regex': 'XSTG_STATIC_GATE PASS', 'threads': 1, 'peak_ram_gb': 2},
                {'name': 'xstg_offset_mutant', 'cmd': f'bash {bench} mut_offset {mst} {rtl} {{RUN}}/xstg_mut',
                 'expect': 'fail', 'fail_regex': 'GATE MUTANT .*REJECTED', 'threads': 1, 'peak_ram_gb': 2}]
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
        if kd == 'hend':
            spec['sdc_extra'] = [f'{HEND_DIR}/{mst}.sdc']
            spec['boundary_tcl'] = [f'{HEND_DIR}/{mst}_boundary.tcl']
            spec['inhold'] = True
            spec['outhold'] = True
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
