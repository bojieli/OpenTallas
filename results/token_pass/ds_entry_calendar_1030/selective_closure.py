exec(open('/srv/opentallas-scratch2/claude/codex-ds-entry-current-1030/guard_paths.py').read().split('cases=[]')[0])
from native_phase import qualify_selected,SELECTED_SEQHOST_CLOSURE
qualify_selected(t,S,kw['manifest'],i)
caught=[]
for name in ('rtl/dsrom_sys/s81_dv/unit/dsdv_mu_hwin.sv','rtl/lib/ot_rst_relay.sv'):
 q=copy.deepcopy(t);del q['source_sha256'][name]
 try:qualify_selected(q,S,kw['manifest'],i)
 except ValueError:caught.append(name)
 else:raise AssertionError('selective missing closure escaped: '+name)
r=dict(status='PASS_COMPLETE_SELECTED_SEQHOST_CLOSURE_GUARD',actual_current_source_pass=True,required_nested_dependencies=len(SELECTED_SEQHOST_CLOSURE),all_measured_master_paths_required=True,selective_single_omissions_caught=caught,no_native_fixture_rerun=True)
(R/'selective_closure.json').write_text(json.dumps(r,indent=2)+'\n');print(r['status'],len(caught))
