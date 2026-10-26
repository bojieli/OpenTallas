#!/usr/bin/env python3
"""Rebuild the native raw-fault LSL cut with resizable adder logic and shared core IO flow.

The input is the source-pinned mapped cut; only HA/FA combinational cells are
expanded. All other instances, including every state element, remain verbatim.
The parent must prove its 40 ps sender minimum before this local IO contract is
qualified. This script does not edit the release die plan.
"""
import argparse
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / 'tools/die_plan'))
import adder_map_dontuse as A
import core_flow
import sdc_lint

RULES = {
    'HAxp5_ASAP7_75t_R': {'CON': '~({A} & {B})', 'SN': '~({A} ^ {B})'},
    'FAx1_ASAP7_75t_R': {'CON': '~(({A} & {B}) | ({A} & {CI}) | ({B} & {CI}))',
                          'SN': '~({A} ^ {B} ^ {CI})'},
}


def expand(text):
    counts = {k: 0 for k in RULES}
    def sub(m):
        cell, inst, conns = m.groups()
        if cell not in RULES:
            return m.group(0)
        pins = dict(A.CONN_RE.findall(conns))
        need = {'A', 'B', 'CON', 'SN'} | ({'CI'} if cell.startswith('FA') else set())
        if set(pins) != need:
            raise ValueError((inst, sorted(pins), sorted(need)))
        counts[cell] += 1
        return '\n'.join('assign ' + pins[out] + ' = ' + expr.format(**{k: '('+v+')' for k,v in pins.items()}) + ';'
                         for out, expr in RULES[cell].items())
    result = A.INST_RE.sub(sub, text)
    # State and every non-adder cell stay byte-identical, rather than relying on
    # an FF count to hide an accidental connection or reset change.
    old = [m.group(0) for m in A.INST_RE.finditer(text) if m.group(1) not in RULES]
    new = [m.group(0) for m in A.INST_RE.finditer(result)]
    assert old == new
    return result, counts


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', required=True, type=Path)
    args = ap.parse_args()
    kd = args.out
    if kd.exists():
        raise SystemExit('refusing to overwrite existing kit ' + str(kd))
    kd.mkdir(parents=True)
    old = REPO / 'results/qc_a0_2157/rawfault_cut/leaf_kit'
    src = gzip.decompress((old / 'rawleaf_keep.v.gz').read_bytes()).decode()
    new, counts = expand(src)
    # The archived mapped cut predates the diagnosed synth_odb FF pruning fix.
    # Keep DNT through synth_odb, then release only in the reviewed PG/anchor hook.
    # This changes attributes only; no state, pin or connection changes.
    new, retained = re.subn(r'\(\* keep = 1 \*\)(\s+DFF\w+_ASAP7_)',
                           r'(* keep = 1, dont_touch = 1 *)\1', new)
    assert retained == 12030, retained
    # Source has 2300 HAs; the failed resynthesis pruned 122 to 2178.
    assert counts == {'HAxp5_ASAP7_75t_R': 2300, 'FAx1_ASAP7_75t_R': 334}, counts
    (kd / 'rawleaf_keep.v').write_text(new)
    for f in ('io.tcl', 'pdn.tcl', 'pins.json'):
        shutil.copyfile(old / f, kd / f)
    rows = []
    for pin in json.loads((old/'pins.json').read_text())['pins']:
        m = re.fullmatch(r'(.*)\[(\d+)\]', pin['name'])
        row = {k:v for k,v in pin.items() if k != 'name'}
        row.update(bus=m[1] if m else pin['name'], bit=int(m[2]) if m else None)
        rows.append(row)
    (kd/'pins.json').write_text(json.dumps(rows,indent=2)+'\n')
    for f in HERE.joinpath('template').iterdir():
        shutil.copyfile(f, kd / f.name)
    for f in ('anchor_row_packing.tcl',):
        shutil.copyfile(REPO / 'physical/common_flow' / f, kd / f)
    # The reviewed PG/retention ordering is retained. The source keeps all FFs
    # through synth_odb, then releases physical DNT only after PG and anchors.
    cfg = (old / 'config.mk').read_text()
    cfg = '\n'.join(l for l in cfg.splitlines() if not any(k in l for k in
          ('PRE_GLOBAL_ROUTE_TCL', 'POST_GLOBAL_ROUTE_TCL', 'OT_VCLK_', 'OT_HOLD_', 'ADDER_MAP_FILE')))
    cfg += '\n' + '\n'.join(core_flow.apply(kd, core_flow.binding(177.5,143.9,40,
                    'previous leaf CTS estimate; remeasure on fresh CTS', 'previous leaf CTS estimate'),
                    'lsl_rawfault_m3')) + '\n'
    cfg += 'export ADDER_MAP_FILE = /work/adder_map_dontuse.v\n'
    cfg += 'export OT_HOLD_IN_MIN = -40\nexport OT_HOLD_OUT_MIN = -27.5\n'
    (kd / 'config.mk').write_text(cfg)
    spec = importlib.util.spec_from_file_location('qcgen', REPO / 'physical/die_plan/qwen_compute/cores/legacy/gen_core_kit_qc.py')
    qc = importlib.util.module_from_spec(spec); spec.loader.exec_module(qc)
    (kd/'face_guard_core.py').write_text(qc.FACE_GUARD_CORE)
    (kd/'core.json').write_text(json.dumps(dict(module='ot_qwen_tile_lsl_rawfault_m3',
             boundary_role=dict(clk='clk',rst_n='reset')),indent=2)+'\n')
    (kd/'boundary_guard_context.json').write_text(json.dumps(dict(
             schema='opentallas.core_boundary_guard_context.v1',source_core_json='core.json',
             clock_ports=['clk'],unused_clock_ports=[],reset_ports=['rst_n'],data_pin_exemptions=[]),indent=2)+'\n')
    sdc = qc.sdc(833,177.5,40,['clk'],['rst_n'],'lsl_rawfault_m3')
    sdc += '\n# Two-sided 40 ps IO contract (COORD 2026-10-26 00:19); parent receipt required.\n'
    sdc += 'set_input_delay -min 40 -clock vclk [get_ports {split_d[*] w_d[*] x_d[*]}]\n'
    sdc += 'set_output_delay -min -27.5 -clock vclk [all_outputs]\n'
    (kd / 'constraint.sdc').write_text(sdc)
    inputs = ['rst_n','v_d','first_d','split_d','w_d','x_d']
    ctx = dict(period_ps=833,insertion_ps=177.5,insertion_ff_ps=143.9,insertion_tol_ps=40,
               clock_ports=['clk'],inputs=inputs,outputs=['t_out','fault_q'],unc_setup_ps=60,
               unc_hold_ps=25,time_unit_ps=1,io_floor_ps={p:166.6 for p in inputs+['t_out','fault_q']},
               port_latency_ps={},hold_in_min_ps=-40,hold_out_min_ps=-27.5,seam_hold_ps=67.5,
               hold_in_min_ports_ps={p:40 for p in ['split_d','w_d','x_d']})
    errors = sdc_lint.lint(sdc, **ctx)
    assert not errors, errors
    (kd / 'sdc_lint.json').write_text(json.dumps(ctx,indent=2)+'\n')
    (kd / 'io_hold.tcl').write_text('proc ot_io_hold_apply {vclk} {\n set_input_delay -min 40 -clock $vclk [get_ports {split_d[*] w_d[*] x_d[*]}]\n}\n')
    (kd / 'io_hold.json').write_text(json.dumps(dict(mode='sender_min',requires_parent=True,
                   inputs={p:dict(in_min_ps=40,basis='parent two-sided sender check required') for p in ['split_d','w_d','x_d']}),indent=2)+'\n')
    (kd / 'budget.json').write_text(json.dumps(dict(die='qwen_compute',type='lsl_rawfault_m3',
                     io_hold=dict(mode='sender_min',requires_parent=True),period_ps=833),indent=2)+'\n')
    for f in ('adder_map_dontuse.py','rtl_lint.py','sdc_lint.py'):
        shutil.copyfile(REPO / 'tools/die_plan' / f, kd / f)
    subprocess.run([sys.executable,'-I',str(REPO/'tools/die_plan/signoff.py'),'bundle',str(kd)],check=True)
    receipt = dict(source_sha256=hashlib.sha256(src.encode()).hexdigest(),expanded=counts,
                   non_adder_instances_unchanged=True,ff_expected=12030,cycles_added=0,
                   source_commit=subprocess.check_output(['git','-C',str(REPO),'rev-parse','HEAD'],text=True).strip(),
                   status='TRIAL PLACE ONLY; fresh geometry/CTS and parent IO receipt required')
    (kd / 'source.json').write_text(json.dumps(receipt,indent=2)+'\n')
    shutil.copyfile(HERE/'place.sh',kd/'place.sh')
    print(json.dumps(receipt))

if __name__ == '__main__':
    main()
