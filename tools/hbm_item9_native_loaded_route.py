#!/usr/bin/env python3
"""Wire-join terminal caller/HA2 maps, then run one finite native physical context.

No synthesis, arithmetic change, additional register or external IO timing is
introduced. Both maps and the original exact gate must exist before preparation.
"""
import argparse
import collections
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import time

import hbm_item9_native_caller_map as C
import hbm_router_pipeline_route_20261006 as B

ROOT = Path(__file__).resolve().parents[1]
TOP = 'ot_hbm_item9_ha2_loaded_context'
NICK = 'turing_ha2_native_loaded'
SUB = Path('results/asap7') / NICK / 'base'
INPUTS = dict(clk=1, rst_n=1, go=1, endpoint_rearm_ready=1, rank=8, pf=16,
              context_operation=64, context_phase=32, inj_data=1024,
              w2_v=8, w2_d=4360, qr_pop=8)
OUTPUTS = dict(inj_rd=2, inj_idx=32, rb_pop=8, dq_own_pop=1, r_v=1,
               r_m=16, r_d=512, dupe=1, issue_o=1, owner_quiet=1,
               context_fault_o=1, delivery_words=2180, delivery_v=4,
               qr_heads=4360, qr_empty=8, qr_ovf=8, qr_counts=56)
LINKS = dict(caller_h_v=2, caller_h_d=1088, caller_p_v=8,
             caller_p_flit=4360, caller_active=1, caller_arm=1,
             caller_rank=8, caller_pf=16, adapter_r_v=1, adapter_r_m=16,
             adapter_r_d=512, adapter_dupe=1, adapter_issue=1, adapter_quiet=1)


def save(p, data):
    p.write_text(json.dumps(data, indent=2) + '\n')


def corner_verdict(content, corner, exitcode):
    """Fail closed on missing STA evidence; process success is not timing closure."""
    errors = []
    if exitcode:
        errors.append(f'STA process exit {exitcode}')
    if re.search(r'\[ERROR\b', content):
        errors.append('STA reported an error')
    if re.findall(r'^OT_CORNER (\S+)\s*$', content, re.M) != [corner]:
        errors.append('missing or ambiguous corner identity')
    metrics = {}
    for name in ('OT_WS', 'OT_WS_R2R', 'OT_VIOL_D_PINS'):
        values = re.findall(r'^' + name + r' ([^\s]+)\s*$', content, re.M)
        try:
            value = float(values[0]) if len(values) == 1 else float('nan')
        except ValueError:
            value = float('nan')
        if not math.isfinite(value):
            errors.append(f'missing, ambiguous or nonfinite {name}')
        else:
            metrics[name] = value
    if 'OT_VIOL_D_PINS' in metrics and (metrics['OT_VIOL_D_PINS'] < 0 or
                                      not metrics['OT_VIOL_D_PINS'].is_integer()):
        errors.append('invalid violating endpoint count')
    # worst_slack_cmd uses seconds; report path properties use ASAP7 ps.
    slack = metrics.get('OT_WS')
    passed = not errors and slack >= 0 and metrics['OT_WS_R2R'] >= 0 and metrics['OT_VIOL_D_PINS'] == 0
    return dict(evidence_valid=not errors, errors=errors,
                worst_slack_ps=None if slack is None else slack * 1e12,
                worst_internal_reg_to_reg_slack_ps=metrics.get('OT_WS_R2R'),
                violating_d_pins=metrics.get('OT_VIOL_D_PINS'),
                conditional_internal_timing_pass=passed,
                parent_qualified=False, full_endpoint_signoff=False)


def declaration(kind, name, width):
    return kind + (' ' if width == 1 else f' [{width-1}:0] ') + name


def wrapper():
    ports = [declaration('input wire', n, w) for n, w in INPUTS.items()]
    ports += [declaration('output wire', n, w) for n, w in OUTPUTS.items()]
    text = 'module ' + TOP + '(\n' + ',\n'.join(ports) + '\n);\n'
    text += '\n'.join(declaration('wire', n, w) + ';' for n, w in LINKS.items()) + '\n'
    # Real result fanout stays inside the mapped caller, including dqo/qr writes.
    names = list(INPUTS) + list(OUTPUTS) + list(LINKS)
    text += C.TOP + ' u_caller(\n' + ',\n'.join(f'.{n}({n})' for n in names) + '\n);\n'
    child = dict(clk='clk', rst_n='rst_n', active='caller_active', arm='caller_arm',
                 rank='caller_rank', pf='caller_pf', h_v='caller_h_v', h_d='caller_h_d',
                 p_v='caller_p_v', p_flit='caller_p_flit', r_v='adapter_r_v',
                 r_m='adapter_r_m', r_d='adapter_r_d', dupe='adapter_dupe',
                 issue_o='adapter_issue', quiet='adapter_quiet')
    text += 'ot_hbm_item9_ha2_cached_map u_adapter(\n'
    text += ',\n'.join(f'.{n}({v})' for n, v in child.items()) + '\n);\nendmodule\n'
    return text


def cell_counts(path):
    counts = collections.Counter()
    with path.open() as stream:
        for line in stream:
            m = re.match(r'\s*(\w+_ASAP7_75t_R)\s+\S+\s*\(', line)
            if m:
                counts[m[1]] += 1
    assert counts, ('no actual mapped cells', str(path))
    return counts


def prepare(caller, child, lef, out):
    if out.exists():
        raise ValueError('preserve all previous outputs; use a new prepared root')
    cr = json.loads((caller / 'result.json').read_text())
    assert cr['phase'] == 'MAPPED_CALLER_ANALYSIS_TERMINAL' and cr['map_exit'] == 0
    assert len(cr['corners']) == 2 and all(v['exit'] == 0 for v in cr['corners'].values())
    assert cr['source_commit'].startswith('8bf656990'), 'selected caller source changed'
    dr = json.loads((child / 'result.json').read_text())
    assert dr['exit'] == 0 and dr['synthesis_only']
    assert dr['shape'] == dict(CUTS=1, NC=8, NOG=8, PFMAX=384, LANES=16,
                               BF16=1, INJ=2, NPT=8, LAT=7, SLOTREG=1)
    gate = json.loads((ROOT / 'results/rtl/hbm_item9_closure_20261005/HA2_cuts_exact_r2/result.json').read_text())
    assert gate['verdict'] == 'PASS_CHANGED_HA2_FULL16_GOLDEN'
    for f, h in dr['sources_sha256'].items():
        assert h == gate['source_sha256'][f], f
    cm = caller / 'orfs/results/asap7/turing_ha2_native_caller/base/1_2_yosys.v'
    dm, = child.glob('work/orfs/results/asap7/*/base/1_2_yosys.v')
    assert C.sha(cm) == cr['mapped_sha256']
    assert C.sha(dm) == dr['artifacts'][str(dm.relative_to(child))]['sha256']
    cc, dc = cell_counts(cm), cell_counts(dm)
    cp = json.loads((caller / 'orfs/caller_pin_caps.json').read_text())
    assert sum(v for k, v in cc.items() if k.startswith('DFF')) == sum(cp['sequential_cells'].values())
    areas = {}
    for name, body in re.findall(r'MACRO\s+(\S+)\s+(.*?)\nEND\s+\S+', lef.read_text(), re.S):
        size = re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)', body)
        if size:
            areas[name] = float(size[1]) * float(size[2])
    counts = cc + dc
    assert not (set(counts) - set(areas)), 'actual cell masters absent from selected LEF'
    area = sum(n * areas[k] for k, n in counts.items())
    model = json.loads((ROOT / 'results/physical/hbm_die_abstracts_20261006/integration/ha2_native_boundary_context/prebuild_final_inventory.json').read_text())
    outer = model['selected_outer_r16g_bbox_um']
    # Five microns per side belong to the parent halo, never free rows.
    w, h = round(outer[2]-outer[0]-10, 3), round(outer[3]-outer[1]-10, 3)
    core = [2.16, 2.16, round(w-2.16, 3), round(h-2.16, 3)]
    row_area = (core[2]-core[0]) * (core[3]-core[1])
    cap = row_area * model['maximum_final_utilization']
    baseline = ROOT/'results/physical/hbm_die_abstracts_20261006/compute/router_pipeline_r1/flowrepair_r2_terminal_SS_FAIL'
    peak_kib = max(map(int, re.findall(r'Peak memory: (\d+)KB', (baseline/'5_2_route.log').read_text())))
    baseline_cells = json.loads((baseline/'6_report.json').read_text())['finish__design__instance__count__stdcell']
    # Actual mapped cell inventory replaces FF-only scaling: native FIFOs and
    # arithmetic have different combinational/FF ratios. This is an admission
    # reservation estimate with repair/extraction headroom, never an RSS cap.
    scaled_gib = peak_kib / 1024**2 * sum(counts.values()) / baseline_cells
    ram = math.ceil((scaled_gib * 1.25 + 64) / 16) * 16
    record = dict(evidence_class='CONDITIONAL_CONNECTED_NATIVE_HA2_CONTEXT',
                  caller_root=str(caller), child_root=str(child),
                  caller_terminal_sha256=C.sha(caller/'result.json'),
                  child_terminal_sha256=C.sha(child/'result.json'),
                  caller_map_sha256=C.sha(cm), child_original_map_sha256=C.sha(dm),
                  gate_sha256=C.sha(ROOT/'results/rtl/hbm_item9_closure_20261005/HA2_cuts_exact_r2/result.json'),
                  actual_cell_counts=dict(counts), actual_cell_area_um2=area,
                  actual_LEF_sha256=C.sha(lef), outer_bbox_um=outer, halo_um=5,
                  die_area_um=[0, 0, w, h], core_area_um=core,
                  nominal_row_area_um2=row_area, maximum_final_cell_CTS_repair_um2=cap,
                  remaining_CTS_repair_um2=cap-area,
                  source_clock_qualified=False, external_IO_bound=False,
                  new_register_edges=0, child_ABC_replayed=False, caller_ABC_replayed=False,
                  physical_closed=False, declared_RAM_GiB=ram, workers=16,
                  RAM_basis=dict(measured_baseline_peak_KiB=peak_kib,
                                 measured_baseline_stdcell_count=baseline_cells,
                                 actual_mapped_cell_count=sum(counts.values()),
                                 scaled_peak_GiB=scaled_gib,
                                 repair_growth_fraction=.25, library_extraction_reserve_GiB=64,
                                 baseline_DRT_log_sha256=C.sha(baseline/'5_2_route.log'),
                                 baseline_metrics_sha256=C.sha(baseline/'6_report.json'),
                                 estimate_not_measured_context_peak=True,
                                 process_or_wall_or_file_cap=False),
                  disk_need_GiB=128)
    # The stage never discovers an undersized architecture through placement.
    if area >= cap:
        raise ValueError(f'Actual mapped area {area} exceeds finite final cap {cap}; resize/repartition required before route')
    out.mkdir(parents=True)
    work = out/'orfs'; base = work/SUB; base.mkdir(parents=True)
    shutil.copy2(cm, work/'caller_mapped.v')
    text, n = re.subn(r'(?m)^(module\s+)ot_ha2_tu_owner_adapter_item9_cuts(?=\s*\()',
                      r'\1ot_hbm_item9_ha2_cached_map', dm.read_text())
    assert n == 1, 'only the exact child module header may be renamed'
    (work/'child_mapped.v').write_text(text)
    (work/'loaded_context.v').write_text(wrapper())
    with (base/'1_2_yosys.v').open('w') as stream:
        for p in ['caller_mapped.v', 'child_mapped.v', 'loaded_context.v']:
            with (work/p).open() as src:
                shutil.copyfileobj(src, stream)
            stream.write('\n')
    sdc = ROOT/'physical/hbm_die_abstracts_20261006/integration/ha2_native_boundary_internal.sdc'
    shutil.copy2(sdc, base/'1_2_yosys.sdc')
    shutil.copy2(sdc, work/'constraint.sdc')
    pins = '''set_io_pin_constraint -group -region bottom:* -pin_names {inj_data[*] inj_idx[*] inj_rd[*]}
set_io_pin_constraint -group -region top:* -pin_names {w2_v[*] w2_d[*]}
set_io_pin_constraint -group -region right:* -pin_names {qr_heads[*] qr_counts[*] qr_empty[*] qr_ovf[*] delivery_words[*] delivery_v[*] r_v r_m[*] r_d[*]}
set_io_pin_constraint -group -region left:* -pin_names {clk rst_n go endpoint_rearm_ready rank[*] pf[*] context_operation[*] context_phase[*] qr_pop[*] rb_pop[*] dq_own_pop dupe issue_o owner_quiet context_fault_o}
'''
    (work/'pins.tcl').write_text(pins)
    cfg = [f'export DESIGN_NAME = {TOP}', f'export DESIGN_NICKNAME = {NICK}',
           'export PLATFORM = asap7', 'export VERILOG_FILES = /work/loaded_context.v',
           'export SDC_FILE = /work/constraint.sdc', 'export CORNER = WC',
           'export CORNERS = WC BC', 'export WC_LIB_FILES = $(WC_NLDM_LIB_FILES)',
           'export BC_LIB_FILES = $(BC_NLDM_LIB_FILES)', 'export ASAP7_USE_VT = RVT',
           'export DIE_AREA = '+' '.join(map(str, record['die_area_um'])),
           'export CORE_AREA = '+' '.join(map(str, core)), 'export PLACE_DENSITY = 0.55',
           'export IO_CONSTRAINTS = /work/pins.tcl', 'export IO_PLACER_H = M6',
           'export IO_PLACER_V = M7', 'export GPL_TIMING_DRIVEN = 0',
           'export TNS_END_PERCENT = 100', 'export REPORT_CLOCK_SKEW = 1']
    (work/'config.mk').write_text('\n'.join(cfg)+'\n')
    record['prepared_sha256'] = {str(p.relative_to(work)): C.sha(p) for p in
        [work/'caller_mapped.v', work/'child_mapped.v', work/'loaded_context.v',
         base/'1_2_yosys.v', base/'1_2_yosys.sdc', work/'constraint.sdc', work/'config.mk', work/'pins.tcl']}
    record['phase'] = 'PREPARED_TERMINAL_MAPS_CONNECTED_NO_SYNTHESIS_REPLAY'
    save(out/'preparation.json', record)


def capacity(out, phase, ram):
    def cpu():
        v = list(map(int, Path('/proc/stat').read_text().splitlines()[0].split()[1:])); return sum(v[:8]), v[3]+v[4]
    t, i = cpu(); time.sleep(.5); tt, ii = cpu(); n = os.cpu_count()
    idle = (ii-i)/(tt-t)*n
    mem = int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024
    free = shutil.disk_usage(out).free
    r = dict(phase=phase, utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
             load=os.getloadavg()[0], idle_cpus=idle, MemAvailable_bytes=mem, free_disk_bytes=free)
    r['fits'] = r['load'] < n and idle >= 16 and mem >= ram*1024**3 and free >= 128*1024**3
    with (out/'capacity.jsonl').open('a') as f: f.write(json.dumps(r)+'\n')
    return r['fits']


def run(out, admitted):
    assert socket.gethostname() == 'ot-epyc1tb', 'E1 only; no localhost heavy work'
    assert not (out/'route.json').exists(), 'preserve existing attempt'
    r = json.loads((out/'preparation.json').read_text()); work = out/'orfs'
    for p, h in r['prepared_sha256'].items(): assert C.sha(work/p) == h, p
    if not capacity(out, 'post_guard' if admitted else 'pre_guard', r['declared_RAM_GiB']): return 75
    if not admitted:
        return subprocess.call(['/srv/opentallas-scratch/admit.sh', str(r['declared_RAM_GiB']), '--',
                                sys.executable, str(Path(__file__).resolve()), '--out', str(out), '--admitted'])
    # Native do-1_synth links already mapped Verilog to ODB; it never runs Yosys.
    # Freeze mapped prerequisites and that linked ODB during every later stage.
    make = 'make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base NUM_CORES=16 '
    freeze = ' '.join('-o /work/'+str(SUB/p) for p in ['1_2_yosys.v', '1_2_yosys.sdc', '1_synth.odb', '1_synth.sdc'])
    shell = ('python3 /src/tools/orfs_allcorner_spef.py /OpenROAD-flow-scripts/flow/scripts/final_outputs.tcl && '
             'cd /OpenROAD-flow-scripts/flow && '+make+'do-1_synth && '+make+freeze+' finish metadata-generate')
    cmd = ['docker', 'run', '--name', 'turing-ha2-native-loaded-'+out.name, '--cpus', '16',
           '-e', 'OMP_NUM_THREADS=16', '-v', str(ROOT)+':/src:ro', '-v', str(work)+':/work', B.IMAGE,
           'bash', '-lc', shell]
    r.update(phase='RUNNING_CONNECTED_NATIVE_LOADED_CONTEXT', command=cmd)
    save(out/'route.json', r)
    with (out/'route.log').open('w') as f: rc = subprocess.call(cmd, stdout=f, stderr=subprocess.STDOUT)
    r.update(flow_exit=rc, phase='FLOW_FAIL_RETAINED' if rc else 'ROUTED_NAMED_CORNER_COLLECTION_REQUIRED')
    save(out/'route.json', r)
    if rc == 0:
        spec = importlib.util.spec_from_file_location('native_corner_template', ROOT/'tools/w18/corner_sta.py')
        template = importlib.util.module_from_spec(spec); spec.loader.exec_module(template)
        rel = '/work/'+str(SUB)
        corners = {}
        for name, corner, kind in [('ss', 'WC', 'max'), ('ff', 'BC', 'min')]:
            tcl = template.script(name, rel, []).replace('get_pins -hierarchical */D', 'all_registers -data_pins')
            tcl = f'define_corners {corner}\n'+re.sub(r'(?m)^read_liberty (.*)$',
                                                     rf'read_liberty -corner {corner} \1', tcl)
            tcl = tcl.replace(f'read_spef {rel}/6_final.spef',
                              f'read_spef -corner {corner} {rel}/6_final.spef')
            extra = '''
puts "OT_EVIDENCE CONNECTED_NATIVE_INTERNAL_PROPAGATED_CTS_SOURCE_AND_EXTERNAL_IO_UNQUALIFIED"
check_setup -verbose
set caller_launch {}; set adapter_launch {}; set caller_capture {}; set adapter_capture {}
foreach p [all_registers -clock_pins] {
  set n [get_full_name $p]
  if {[string match "u_caller/*" $n]} {lappend caller_launch $p}
  if {[string match "u_adapter/*" $n]} {lappend adapter_launch $p}
}
foreach p [all_registers -data_pins] {
  set n [get_full_name $p]
  if {[string match "u_caller/*" $n]} {lappend caller_capture $p}
  if {[string match "u_adapter/*" $n]} {lappend adapter_capture $p}
}
puts "OT_NATIVE_CALLER_TO_ADAPTER"
report_checks -from $caller_launch -to $adapter_capture -path_delay KIND -group_path_count 20 -format full_clock_expanded
puts "OT_NATIVE_ADAPTER_TO_DQO_QR"
report_checks -from $adapter_launch -to $caller_capture -path_delay KIND -group_path_count 20 -format full_clock_expanded
report_checks -unconstrained -from [get_ports rst_n] -path_delay KIND -group_path_count 10 -format full_clock_expanded
report_check_types -max_slew -max_capacitance -max_fanout -violators
'''.replace('KIND', kind)
            tcl = tcl.replace('\nexit\n', extra+'\nexit\n')
            path = work/('native_'+name+'.tcl'); path.write_text(tcl)
            cmd = ['docker', 'run', '--rm', '--cpus', '16', '-v', str(work)+':/work', B.IMAGE,
                   '/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad', '-no_init', '-exit',
                   '-threads', '16', '/work/'+path.name]
            with (out/('native_'+name+'.log')).open('w') as f:
                exitcode = subprocess.call(cmd, stdout=f, stderr=subprocess.STDOUT)
            corners[name] = dict(exit=exitcode, named_parasitic_corner=corner,
                                 tcl_sha256=C.sha(path), log_sha256=C.sha(out/('native_'+name+'.log')),
                                 **corner_verdict((out/('native_'+name+'.log')).read_text(), name, exitcode))
            if exitcode: break
        r.update(phase='CONNECTED_NATIVE_ROUTE_CORNERS_TERMINAL', corners=corners,
                 retained_sha256={p: C.sha(work/SUB/p) for p in ['6_final.odb', '6_final.spef', '6_final.sdc']})
        metrics = json.loads((work/'logs/asap7'/NICK/'base/6_report.json').read_text())
        r['actual_final_stdcell_area_um2'] = metrics['finish__design__instance__area__stdcell']
        r['finite_cell_CTS_repair_cap_pass'] = r['actual_final_stdcell_area_um2'] <= r['maximum_final_cell_CTS_repair_um2']
        r['parent_qualified'] = False
        r['full_endpoint_signoff'] = False
        r['conditional_internal_timing_pass'] = (
            set(corners) == {'ss', 'ff'} and
            all(v['conditional_internal_timing_pass'] for v in corners.values()))
        r['verdict'] = ('CONDITIONAL_NATIVE_INTERNAL_SSFF_PASS_PARENT_OPEN'
                        if r['conditional_internal_timing_pass'] and r['finite_cell_CTS_repair_cap_pass']
                        else 'CONDITIONAL_NATIVE_INTERNAL_SSFF_FAIL_PARENT_OPEN')
        save(out/'route.json', r)
        if not r['finite_cell_CTS_repair_cap_pass'] or not r['conditional_internal_timing_pass']:
            return 1
    return rc


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--out', type=Path, required=True)
    p.add_argument('--prepare', action='store_true'); p.add_argument('--caller-map', type=Path)
    p.add_argument('--child-map', type=Path); p.add_argument('--cell-lef', type=Path)
    p.add_argument('--admitted', action='store_true'); a = p.parse_args()
    if a.prepare:
        if not all([a.caller_map, a.child_map, a.cell_lef]): p.error('both terminal maps and actual selected cell LEF required')
        prepare(a.caller_map.resolve(), a.child_map.resolve(), a.cell_lef.resolve(), a.out.resolve())
    else: sys.exit(run(a.out.resolve(), a.admitted))
