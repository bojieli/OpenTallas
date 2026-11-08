"""Actual GRT RC diagnostic, not routed sign-off. Frozen kit library selector + native nominal uncertainty helper."""
import sys,json,subprocess
from pathlib import Path
K=Path('/srv/opentallas-scratch2/claude/codex-su-1209/fullx_vL_cts_release')
sys.path.insert(0,str(K));import signoff
O=K/'vis_grt'/'nominal1551b';O.mkdir(exist_ok=False);(O/'.keep').touch()
s=(K/'postcts_gate.tcl').read_text().replace('/work/postcts_gate_', '/out/postcts_gate_')
needle='set per [get_property [get_clocks clk] period]';assert s.count(needle)==1
s=s.replace(needle,'proc so {k args} { puts \"SO $k [join $args { }]\" }\n'+signoff.unc_policy_tcl('nominal')+'\n'+needle)
s+='''\nset np 0; set ni 0; set wp 0.0; set wi 0.0
foreach p [find_timing_paths -path_delay min -group_path_count 200000 -endpoint_path_count 1 -slack_max 0] {
 set sp [get_property $p startpoint];set z [get_property $p slack]
 if {[get_property $sp is_port]} {incr np;if {$z<$wp} {set wp $z}} else {incr ni;if {$z<$wi} {set wi $z}}
}
puts "NOMINAL_GRT_CENSUS ports $np port_wns $wp other $ni other_wns $wi"
report_checks -path_delay max -group_path_count 3 -format full_clock_expanded > /out/worst_max_$ot_pg_c.rpt
'''
(O/'session.tcl').write_text(s)
B=K/'run/results/asap7/hbc_ot_hbm_su_pg_lane_full_x_core/base/5_1_grt.odb'
for c in ['TT','FF']:
 cmd=['docker','run','--rm','--memory','12g','--memory-swap','12g','--cpus','2','-e',f'OT_CORNER={c}','-e','OT_POSTCTS_GRT=1','-e','ODB=/work/'+str(B.relative_to(K)),'-v',str(K)+':/work:ro','-v',str(O)+':/out','openroad/orfs:asap7lock','bash','-lc','source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /out/session.tcl']
 with open(O/f'{c}.log','w') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
 assert r.returncode==0,(c,r.returncode)
 d=json.load(open(O/f'postcts_gate_{c.lower()}.json'));assert d['parasitics']=='global_routing',d
 print(c,d,flush=True)
print('ADVISORY_GRT_ONLY_NOT_SIGNED',flush=True)
