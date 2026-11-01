from pathlib import Path
import json,hashlib
B=Path(__file__).resolve().parent
raw=dict(schema='opentallas.die_plan.v1',note='Actual two-source single833ps-domain hold-exporter diagnostic; clk_send early -35ps, clk_recv early -85ps, late0 each; no production sizing claim',
 die=dict(name='parent_hold_multi',label='Routed hierarchy diagnostic',tech='asap7',outline_um=[120.96,60.48],period_ps=833,reach_um=405,rep_um=450,grid_um=8.64),
 partition_types={'parent':dict(module='hold_parent',outline_um=[120.96,60.48],buses=[],ft_slots=[],contents=[],
 hard_cores=[dict(inst=inst,module=mod,outline_um=[17.28,17.28],origin_um=[x,17.28],orient='R0',lef=f'hold_parent/macros/{mod}.lef',lib=f'hold_parent/macros/{mod}_tt.lib') for inst,mod,x in [('u_send','hold_tx',17.28),('u_r0.u_bs0','hold_rx',51.84),('u_other','hold_tx',86.4)]])},
 partitions=[dict(name='parent',type='parent',origin_um=[0,0],orient='R0')],ports=[],lanes=[],clock=dict(io_hold='sender_min',insertion_ps=0,insertion_tol_ps=80),reset={},budgets={},latency={})
(B/'parent_plan.json').write_text(json.dumps(raw,indent=1)+'\n')
digest=hashlib.sha256(json.dumps(raw,sort_keys=True,separators=(',',':')).encode()).hexdigest()
budget=dict(die='parent_hold_multi',type='hold_rx',parent_type='parent',io_hold=dict(mode='sender_min',plan_sha256=digest,requires_parent=True,receiver_kind='core'))
(B/'hold_rx'/'budget.json').write_text(json.dumps(budget,indent=1)+'\n')
(B/'hold_rx'/'sdc_lint.json').write_text(json.dumps(dict(hold_in_min_ports_ps={'a':100.0,'b':100.0},period_ps=833,unc_setup_ps=0,unc_hold_ps=25,source='Exact generated constraint.sdc; declaration only, no STA receipt'),indent=1)+'\n')
print(digest)
