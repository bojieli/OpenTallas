#!/usr/bin/env python3
"""Correct c3q's global cluster-size and reset-feedthrough construction.

CTS-only diagnostic, not a sign-off recipe: the master-plan slice and the
dedicated infrastructure timing models still gate release.
Usage: infra_island_kit_v4q.py SRC_V2_KIT DST QUAD_JSON
"""
import json
from pathlib import Path
import re
import subprocess
import sys

src, dst, spec = map(Path, sys.argv[1:4])
dst.mkdir(parents=True, exist_ok=True)
q = json.loads(spec.read_text())
assert q['type'] == 'ot_s81hd_elemA_cv', 'elemA proof first; elemB needs its own plan-fixed reset coordinates'
# A feed-through preserves reset polarity and adds no unpriced reset cycle.
# Core rst_n remains a distinct delivered-reset input, connected at the parent.
q['remove_ports'] = ['clk']
q['die_cells'] = [c for c in q['die_cells'] if c[0] not in ('u_isl_rst', 'u_isl_rstb', 'u_isl_m1')]
q['die_cells'].append(['u_isl_rstft', 'BUFx4_ASAP7_75t_R', 157.14, 158.22,
                       {'A': 'ft_rst_i', 'Y': 'ft_rst_o'}])
q['note_reset'] = 'Polarity-preserving, combinational dedicated feedthrough; core rst_n separate; +0 reset cycles.'
q['cts_construction'] = 'Separate OpenROAD session per quadrant; ceil(actual placed sinks / L), no measured-clock inputs.'
qpath = dst / 'quad_v4.json'
qpath.write_text(json.dumps(q, indent=2) + '\n')
subprocess.run([sys.executable, str(Path(__file__).with_name('infra_island_kit_v3q.py')),
                str(src), str(dst), str(qpath)], check=True)
# v3 removed rst_n unconditionally when creating pins and SDC. Restore it.
io = (dst / 'io.tcl').read_text()
io += '\n'.join(l for l in (src / 'io.tcl').read_text().splitlines()
                if re.match(r'place_pin -pin_name \{rst_n\}', l)) + '\n'
(dst / 'io.tcl').write_text(io)
sdc = (dst / 'constraint_pd.sdc').read_text().replace('[get_ports {ft_rst_i}]', '[get_ports {rst_n}]')
(dst / 'constraint_pd.sdc').write_text(sdc)
# Generic face-flop cloning must not treat die-owned infrastructure as data IO.
ff = (dst / 'face_flops.tcl').read_text()
old = 'set ff_skip_re {^(clk|rst_n)$}'
assert old in ff
ports = '|'.join(re.escape(p[0]) for p in q['ft_ports'])
(dst / 'face_flops.tcl').write_text(ff.replace(old, 'set ff_skip_re {^(clk|rst_n|' + ports + ')$}'))
# Bind PG before locking newly instantiated cells. The plan uses the core's
# VDD/VSS rails; no island holes or separate invented supplies.
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
ps = (dst / 'patch_synth.tcl').read_text().replace('$i setDoNotTouch 1', pg + '$i setDoNotTouch 1')
(dst / 'patch_synth.tcl').write_text(ps)
pre = (dst / 'pre_gpl_island.tcl').read_text()
pg_pre = pg.replace('$b ', '$::pi_b ')
pre = pre.replace('$i setDoNotTouch 1', pg_pre + '$i setDoNotTouch 1')
(dst / 'pre_gpl_island.tcl').write_text(pre)
cm = (dst / 'config.mk').read_text()
cm += '\n# Dedicated island ports are fixed infrastructure, never generic buffered IO.\n'
cm += 'override export DONT_BUFFER_PORTS = 1\n'
(dst / 'config.mk').write_text(cm)
# Use the actual pre-CTS placement census, the already reviewed deterministic
# rule. Each fresh process characterizes one tree, avoiding CTS-0065.
prep = (dst / 'pre_cts_trunk.tcl').read_text()
prep += '''
set f [open /work/quad_sizes.tcl w]
dict for {k n} $cnt {
  if {$k eq "M"} continue
  set size [expr {int(ceil($n / double(%d)))}]
  puts $f "dict set ::quad_sizes $k $size"
  puts "V4Q_PLAN $k sinks $n cluster_size $size target_leaves %d"
}
close $f
''' % (q['L'], q['L'])
(dst / 'pre_cts_trunk.tcl').write_text(prep)
(dst / 'cts_seq.tcl').write_text('''
source $::env(SCRIPTS_DIR)/load.tcl
set phase $::env(OT_QPHASE)
if {$phase eq "prep"} {
  load_design 3_place.odb 3_place.sdc
  source /work/pre_cts_trunk.tcl
  repair_clock_inverters
} else {
  load_design 4_seq.odb 4_seq.sdc
  if {$phase eq "final"} {
    detailed_placement
    estimate_parasitics -placement
    report_clock_skew
  } else {
    source /work/quad_sizes.tcl
    if {$phase eq "M"} { set size 2; set net clk_m } else {
      set size [dict get $::quad_sizes $phase]; set net clk_q$phase
    }
    set_dont_use $::env(DONT_USE_CELLS)
    clock_tree_synthesis -clk_nets $net -sink_clustering_enable \\
      -sink_clustering_size $size -sink_clustering_max_diameter 40 \\
      -dont_use_dummy_load
  }
}
orfs_write_db $::env(RESULTS_DIR)/4_seq.odb
orfs_write_sdc $::env(RESULTS_DIR)/4_seq.sdc
''')
print('V4Q_READY', dst)
