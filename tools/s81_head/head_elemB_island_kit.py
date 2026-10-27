#!/usr/bin/env python3
"""HEAD-CORE-LAT-R5 /ELEMB (2026-10-26): elemB kit for GEOMETRY (synth + place only) on the DIE-BOUND top.

Root cause fixed here: the R2 elemB c2/c3q kits were derived from the Codex native kit_r2 netlist
ot_s81hd_elemB_l4_native (reduced face, 293 signal ports, FADD_L4 native profile) while the die binds
ot_s81hd_elemB_cv (458 signal ports, physical/die_plan/s81_head/cores/views/ot_s81hd_elemB_cv, die_plan.json, bundle
g_cvb.u_eB) and elemA is rebuilt from the matching CV wrapper ot_s81hd_elemA_rb.sv.  This kit starts from the
hd_elemA_rebuild.py --elem B kit (top ot_s81hd_elemB_cv from rtl/dsrom_sys/s81_head/ot_s81hd_elemB_rb.sv, closed
element RTL f11f3cc47) so the netlist face equals the die-bound abstract, then applies the SAME island chain as
elemA v4q (Codex codex/s81head-0733 9c664aa42): lattice outline 285.12 (E/N pins +7.468), ROMs per island_spec,
12.2a1 pushdown island = elemA v4q die cells translated to the elemB centre (142.56; -17.28 = 4 lattice cells, so
row/site alignment is identical), core rst_n kept as its own input, clk port replaced by the ft ports.
Not carried from v3q/v4q: the CT_* quadrant trunk cells and per-quadrant CTS (the in-core tree is plan-built by
head_tree_plan.py, R4/R5).  No CTS here.  No stubs or ties added (the kit adds no port beyond the island ft ports).
usage: head_elemB_island_kit.py SEED_KIT TOOLS_DIR SPEC_DIR QUAD_A_V4_JSON WORK_DIR
  -> WORK_DIR/{b1_patch,b2_v2,b3_v3q,kit} ; kit = the place-only kit.
"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

seed, tools, specd, qa, work = map(Path, sys.argv[1:6])
work.mkdir(parents=True, exist_ok=True)
py = sys.executable
OLD, NEW, C_A, C_B = 277.652, 285.12, 159.84, 142.56
D = C_B - C_A                                   # -17.28 = 4 x 4.32

# b1: seed copy (no run data) + lattice outline / E/N pin shift (infra_island_kit_patch.py)
b1 = work / 'b1_patch'
shutil.copytree(seed, b1, ignore=shutil.ignore_patterns('run', '__pycache__', 'trial.log', '*.log'))
for f in ('island_elemB.tcl', 'island_elemB_pins.tcl'):
    shutil.copy2(specd / f, b1 / f)
subprocess.run([py, str(tools / 'infra_island_kit_patch.py'), str(b1), str(OLD), str(NEW), 'elemB'], check=True)
# b2: ROM sites + centre pins from island_spec (infra_island_kit_v2.py)
b2 = work / 'b2_v2'
subprocess.run([py, str(tools / 'infra_island_kit_v2.py'), str(b1), str(b2), 'elemB', str(specd / 'island_spec.json')], check=True)
# b3: pushdown netlist patch + pre-GPL fixed island cells (infra_island_kit_v3q.py) with the elemA v4 island
A = json.loads(qa.read_text())
assert A['type'] == 'ot_s81hd_elemA_cv' and abs(A['centre'] - C_A) < 1e-9
H = 4.32
Q = dict(type='ot_s81hd_elemB_cv', centre=C_B, L=A['L'], diam=A['diam'],
         # v3q needs four lattice nodes for its (unused here) trunk script; mirror-symmetric, on the 4.32 lattice
         nodes={'WS': [C_B - 18 * H, C_B - 16 * H], 'WN': [C_B - 18 * H, C_B + 16 * H],
                'ES': [C_B + 18 * H, C_B - 16 * H], 'EN': [C_B + 18 * H, C_B + 16 * H]},
         size={'WS': 1, 'WN': 1, 'ES': 1, 'EN': 1},
         ft_ports=[[n, d, round(x + D, 3), round(y + D, 3)] for n, d, x, y in A['ft_ports']],
         die_cells=[[n, m, round(x + D, 3), round(y + D, 3), c] for n, m, x, y, c in A['die_cells']],
         remove_ports=A['remove_ports'], note_reset=A['note_reset'],
         pushdown_src='elemA v4q quad_v4.json (codex/s81head-0733) translated by %.2f um (centre %.2f -> %.2f)' % (D, C_A, C_B))
qb = work / 'quad_elemB_v5.json'
qb.write_text(json.dumps(Q, indent=1) + '\n')
b3 = work / 'b3_v3q'
subprocess.run([py, str(tools / 'infra_island_kit_v3q.py'), str(b2), str(b3), str(qb)], check=True)
# kit: v4q fixes made type-generic + place-only
K = work / 'kit'
shutil.copytree(b3, K)
io = (K / 'io.tcl').read_text()
rst = [l for l in (b2 / 'io.tcl').read_text().splitlines() if re.match(r'place_pin -pin_name \{rst_n\}', l)]
assert len(rst) == 1, rst
(K / 'io.tcl').write_text(io + rst[0] + '\n')
sdc = (K / 'constraint_pd.sdc').read_text().replace('[get_ports {ft_rst_i}]', '[get_ports {rst_n}]')
(K / 'constraint_pd.sdc').write_text(sdc)
ff = (K / 'face_flops.tcl').read_text()
old = 'set ff_skip_re {^(clk|rst_n)$}'
assert old in ff
ports = '|'.join(re.escape(p[0]) for p in Q['ft_ports'])
(K / 'face_flops.tcl').write_text(ff.replace(old, 'set ff_skip_re {^(clk|rst_n|' + ports + ')$}'))
pg = '''
foreach it [$i getITerms] {
  set sig [[$it getMTerm] getSigType]
  if {$sig eq "POWER" || $sig eq "GROUND"} {
    set pn [expr {$sig eq "POWER" ? "VDD" : "VSS"}]
    set net [$b findNet $pn]
    if {$net eq "NULL"} { set net [odb::dbNet_create $b $pn] }
    $net setSigType $sig
    $it connect $net
  }
}
'''
ps = (K / 'patch_synth.tcl').read_text().replace('$i setDoNotTouch 1', pg + '$i setDoNotTouch 1')
(K / 'patch_synth.tcl').write_text(ps)
pre = (K / 'pre_gpl_island.tcl').read_text()
pre = pre.replace('$i setDoNotTouch 1', pg.replace('$b ', '$::pi_b ') + '$i setDoNotTouch 1')
pre = '\n'.join(l for l in pre.splitlines() if not l.startswith('pi_cell CT_')) + '\n'   # no c3q trunk cells
(K / 'pre_gpl_island.tcl').write_text(pre)
cm = (K / 'config.mk').read_text()
cm = re.sub(r'^override export (CTS_ARGS|PRE_CTS_TCL|POST_CTS_TCL)\s*=.*$', '', cm, flags=re.M)
cm += '''
# HEAD-CORE-LAT-R5 /ELEMB: geometry kit (synth + place only).  Dedicated island ports are fixed infrastructure.
override export DONT_BUFFER_PORTS = 1
'''
(K / 'config.mk').write_text(cm)
(K / 'pre_cts_trunk.tcl').unlink()
# sdc_lint contract follows the SDC: 12.3/12.8 common latency, early core tap retired (v3q set the SDC source to 0)
sl = json.loads((K / 'sdc_lint.json').read_text())
assert sl['port_latency_ps'] == {'clk': -120.0}, sl['port_latency_ps']
sl['port_latency_ps'] = {'clk': 0.0}
(K / 'sdc_lint.json').write_text(json.dumps(sl, indent=1) + '\n')
(K / 'R5_KIT.json').write_text(json.dumps(dict(
    tool='head_elemB_island_kit.py', argv=sys.argv, top='ot_s81hd_elemB_cv', outline=NEW, centre=C_B,
    island=Q, scope='GEOMETRY ONLY: synth + place, no CTS/route, not a sign-off kit'), indent=1) + '\n')
print('R5 elemB kit', K)
