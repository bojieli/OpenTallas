import json,pathlib,sys
W=pathlib.Path('/srv/opentallas-scratch2/claude/wt/codex-kv-pv-clock-1029');sys.path.insert(0,str(W/'tools/die_plan'));from core_infra import word
L=pathlib.Path('/srv/opentallas-scratch2/claude/codex-kv-phy-pad-1028/pv_clock')
for v in ['R0','fMX']:
 k=L/'corrected_kits'/('kv3_pv_pair__380.16x190.08'+('_fMX'if v=='fMX'else''));p=json.load(open(k/'core_infra_plan.json'));nick='hc_kv3_pv_pair__380_16x190_08'+('_fMX'if v=='fMX'else'')
 t=['read_db /work/run/results/asap7/'+nick+'/base/3_place.odb','source /work/core_infra_impl.tcl','set ::ot_ci_b [ord::get_db_block]','set ::ot_ci_tree_out [dict create]','set ::ot_ci_tree_expected {}','set ::ot_ci_tree_seen {}','set before_inst [llength [$::ot_ci_b getInsts]]','set before_net [llength [$::ot_ci_b getNets]]','set before_terms [dict create]','foreach i [$::ot_ci_b getInsts] {foreach it [$i getITerms] {dict set before_terms $it [$it getNet]}}']
 for l in p['core_tree']['leaves']:
  if not l.get('cts_open'):continue
  n=l['node'];t+=['dict set ::ot_ci_tree_out '+word(n)+' [$::ot_ci_b findNet '+word(n+'_out')+']']
  for s in l['sinks']:
   t+=['set path '+word(s),'set cut [string last / $path]','set i [$::ot_ci_b findInst [string range $path 0 [expr {$cut-1}]]]','if {$i eq "NULL"} {error "MISSING_PLANNED_INST $path"}','set it [$i findITerm [string range $path [expr {$cut+1}] end]]','if {$it eq "NULL"} {error "MISSING_PLANNED_PIN $path"}','lappend ::ot_ci_tree_expected $it']
 for l in p['core_tree']['leaves']:
  if l.get('cts_open'):
   for s in l['sinks']:t+=['ot_ci_tree_sink '+word(l['node'])+' '+word(s)]
 t+=['set unexpected 0','dict for {it old} $before_terms {if {[lsearch -exact $::ot_ci_tree_expected $it]<0 && [$it getNet] ne $old} {incr unexpected}}','if {$unexpected} {error "NONPLANNED_TERM_CHANGED $unexpected"}','if {$before_inst != [llength [$::ot_ci_b getInsts]] || $before_net != [llength [$::ot_ci_b getNets]]} {error "CELL_NET_CENSUS_CHANGED"}']
 for l in p['core_tree']['leaves']:
  if l.get('cts_open'):
   n=l['node'];t+=['set n [$::ot_ci_b findNet '+word(n+'_out')+']','set actual [expr {[llength [$n getITerms]]-1}]','if {$actual != '+str(len(l['sinks']))+'} {error "LEAF_CENSUS '+n+' $actual"}','puts "BOUND_LEAF '+n+' $actual"']
 t+=['puts "EXACT_APPROVED_BINDING_PASS 29770 register sinks; all other terminals/cells/nets unchanged"','write_db /work/run/results/asap7/'+nick+'/base/3_place.odb','exit']
 (k/'apply_approved_binding.tcl').write_text('\n'.join(t)+'\n')
