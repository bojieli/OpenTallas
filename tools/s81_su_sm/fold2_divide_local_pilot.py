#!/usr/bin/env python3
"""Generate the reviewed, standalone folded-SMD PLACE pilot; never adopt a die plan.

Run through ot-run, then view the generated pins/core image before PLACE. The
native service timing and the parent R5 plan remain separate qualifications.
"""
import argparse
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE = 'ot_s81_su_smd_fold2_local'
RTL = 'rtl/dsrom_sys/s81_dv/su_sm/ot_s81_su_smd_fold2_local.sv'
MEASURED_RTL_SHA = '7370c1e357ac93ebcc4e272440ff753a01436784374d561355bd469025ee12fd'
SIDE = 155.52
PORTS = [
    ('clk', 'input', 1), ('rst_in', 'input', 1), ('cfg_p', 'input', 2),
    ('i_pv', 'input', 1), ('i_pa', 'input', 128), ('i_dv', 'input', 1),
    ('i_den', 'input', 32), ('i_csv', 'input', 1), ('i_csi', 'input', 5),
    ('i_csd', 'input', 64), ('o_ov', 'output', 1), ('o_o', 'output', 64),
    ('o_f', 'output', 2),
]
FACES = {
    'W': [('i_pa', 128), ('i_pv', 1)],
    'E': [('o_o', 64), ('o_ov', 1), ('o_f', 2)],
    'N': [('i_den', 32), ('i_dv', 1)],
    'S': [('cfg_p', 2), ('i_csd', 64), ('i_csi', 5), ('i_csv', 1)],
}


def model():
    return dict(kind='ONE_LEAF_PLACE_PILOT', outline_um=[SIDE, SIDE],
                core_margin_um=4.32, estimated_cells=63884, estimated_std_area_um2=7134.84156,
                mapped_core_fill=7134.84156 / (SIDE - 8.64) ** 2,
                cell_area_scope='original measured SMD + conservative 1000 cells/300um2 local control budget; before 301 face flops', mission_added_cycles=0,
                added_pin_cycles=dict(rx=1, tx=1), signal_cap='M6',
                qualification='unqualified standalone candidate; no die plan adoption',
                measured_rtl_sha256=MEASURED_RTL_SHA)


def pin_table():
    pins = []
    for face, buses in FACES.items():
        n = sum(width for _, width in buses)
        start = round(((SIDE - 0.576 * (n - 1)) / 2 - 0.024) / 0.048) * 0.048 + 0.024
        k = 0
        for bus, width in buses:
            for bit in range(width):
                p = round(start + 0.576 * k, 4)
                k += 1
                x, y = ((0, p) if face == 'W' else (SIDE, p) if face == 'E'
                        else (p, SIDE) if face == 'N' else (p, 0))
                pins.append(dict(name=bus if width == 1 else f'{bus}[{bit}]', x=x, y=y,
                                 layer='M4' if face in 'WE' else 'M5'))
    pins.extend([dict(name='clk', x=77.784, y=77.76, layer='M5'),
                 dict(name='rst_in', x=75.624, y=77.76, layer='M5')])
    return pins


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path)
    ap.add_argument('--describe', action='store_true')
    a = ap.parse_args()
    digest = hashlib.sha256((ROOT / RTL).read_bytes()).hexdigest()
    if digest != MEASURED_RTL_SHA:
        raise SystemExit('RTL changed: measure its cell/area budget before reusing this outline')
    if a.describe:
        print(json.dumps(dict(model=model(), pins=len(pin_table())), indent=2))
        return
    if a.out is None:
        ap.error('--out is required for generation')
    out = a.out.resolve()
    if out.exists() and any(out.iterdir()):
        raise SystemExit('Use a fresh output root; existing attempts are preserved')
    inputs = out / '_inputs'
    inputs.mkdir(parents=True, exist_ok=True)
    put = lambda name, value: (inputs / name).write_text(json.dumps(value, indent=1) + '\n')
    put('pins.json', pin_table())
    put('model.json', model())
    put('candidate.json', dict(die=dict(name='codex_svc_sm_leaf_pilot', outline_um=[SIDE, SIDE],
                                       reach_um=405, period_ps=833),
                               clock=dict(common_latency_ps=250, insertion_ps=250, insertion_tol_ps=40),
                               partition_types={}, partitions=[], ports=[], lanes=[]))
    view = MODULE + '@pilot_local_vA'
    put('views.json', dict(plan=str(inputs / 'candidate.json'), view_list=[dict(
        view=view, module=MODULE, outline_um=[SIDE, SIDE], pins_file='pins.json',
        pins_sha256=hashlib.sha256((inputs / 'pins.json').read_bytes()).hexdigest(),
        instances=['pilot.u_div'], placed=1, recipe_keys=[MODULE])]))
    shared = ROOT / 'physical/die_plan/hbm_arch_cores'
    sys.path[:0] = [str(shared), str(ROOT / 'tools/die_plan')]
    sp = importlib.util.spec_from_file_location('fold2_core_generator', shared / 'gen_core_kit_hbm.py')
    gen = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(gen)
    commit = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip()
    script = (ROOT / 'tools/s81_su_sm/smd_fold2_local_bench.sh').read_text()
    files = list(dict.fromkeys('rtl/' + f for f in re.findall(r'"\$S/([^"\n]+)"', script)
                               if '/test/' not in f))
    recipe = dict(top=MODULE, files=files, params={}, macros=[], source_commit=commit,
                  read_at_commit=True, synth_memory_max_bits=16384)
    profile = dict(source_commit=commit, family='S81_SM_FOLD2_ONE_LEAF_PILOT',
                   clock_ports=['clk'], reset_ports=['rst_in'], diagnostic_inputs=True,
                   pin_placement_policy='DECLARED_CLOCK_RESET_POINTS',
                   qualification='PLACE_ONLY_UNQUALIFIED', added_face_cycles=dict(rx=1, tx=1),
                   port_inventory=dict(top=MODULE, source_file=RTL, source_sha256=digest, ports=PORTS))
    sys.argv = ['gen_core_kit_hbm', '--views', str(inputs / 'views.json'), '--view', view,
                '--out', str(out), '--recipe-key', MODULE, '--corner', 'TC', '--util', '0.40',
                '--sigmax', 'M6', '--face-shell', 'on', '--face-shell-drop', 'off',
                '--clock-pin-entry', 'on', '--core-insertion', 'none', '--max-fanout', '8',
                '--hold-ff-margin', '0', '--trial']
    gen.main(recipe_overrides={MODULE: recipe}, source_profile=profile)
    kit = out / re.sub(r'[^A-Za-z0-9_.-]', '_', view)
    # Source-specific local control bands; fresh form, no exclusive GPL regions.
    import shutil
    shutil.copyfile(ROOT / 'tools/s81_su_sm/smd_local_control_pose.tcl', kit / 'local_control_pose.tcl')
    with (kit / 'face_flops.tcl').open('a') as f:
        f.write('\nsource /work/local_control_pose.tcl\n')
    with (kit / 'face_flops_release.tcl').open('a') as f:
        f.write("""
set lc_fp [open $::env(RESULTS_DIR)/ot_local_control_pose.tsv r]
foreach lc_line [split [read $lc_fp] "\n"] {
 if {$lc_line eq ""} continue
 set lc_i [[ord::get_db_block] findInst [lindex [split $lc_line "\t"] 1]]
 if {$lc_i ne "NULL" && [$lc_i getPlacementStatus] eq "FIRM"} {$lc_i setPlacementStatus PLACED}
}
close $lc_fp
""")
    (kit / 'HOLD_ROUTE').write_text('PLACE pilot only; actual placed geometry review required\n')
    (kit / 'DO_NOT_COUNT').write_text('No die plan adoption or physical sign-off\n')
    frozen = json.loads((kit / 'freeze.json').read_text())
    frozen['local_control_pose'] = dict(file='local_control_pose.tcl', sha256=gen.sha(kit / 'local_control_pose.tcl'), mission_added_cycles=0)
    frozen['kit_hash'] = gen.kit_hash(kit)
    (kit / 'freeze.json').write_text(json.dumps(frozen, indent=1)+'\n')
    gen.stamp_generation_inputs(kit)


if __name__ == '__main__':
    main()
