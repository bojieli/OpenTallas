#!/usr/bin/env python3
"""Disabled source event: retain all real HF fault fields, prune reserved3/4 at physical cuts."""
from pathlib import Path
import hashlib,json,re
R=Path(__file__).resolve().parents[2];B=R/'results/hbm_hfdep_native_0250';O=B/'fc9/proposed';O.mkdir(parents=True,exist_ok=True)
sha=lambda s:hashlib.sha256(s.encode()).hexdigest()
s=(B/'selected/hfd_ep_static.sv').read_text();s=s.replace('module hfd_ep_static #','module hfd_ep_static_fc9 #').replace('output reg  [10:0]  fault_cause','output reg  [8:0]   fault_cause').replace("fault_cause <= 11'd0","fault_cause <= 9'd0").replace('fault_cause <= {p_st[0], cal_fault, early, lock_lost, bd_cause};','fault_cause <= {p_st[0], cal_fault, early, lock_lost, bd_cause[6:5], bd_cause[2:0]};');assert 'output reg  [8:0]'in s and 'bd_cause[6:5]'in s
(O/'hfd_ep_static_fc9.sv').write_text(s)
def prune(s,bus,hi,lo):
 def num(x):
  n=int(x);assert not lo<=n<=hi,(bus,n)
  return n-2 if n>hi else n
 def sub(m):return bus+'['+str(num(m[1]))+(':'+str(num(m[2]))if m[2]is not None else'')+']'
 s=re.sub(r'\b'+re.escape(bus)+r'\[(\d+)(?::(\d+))?\]',sub,s)
 s=re.sub(r'\[(\d+):0\](\s+'+re.escape(bus)+r'\b)',lambda m:'['+str(int(m[1])-2)+':0]'+m[2],s)
 return s
rows=[]
for f,bus,hi,lo,inst in [('hbm_arch_NE_io','L125_o',4,3,'N2'),('hbm_arch_q_spb0','L117_o',4,3,'S0'),('hbm_arch_q_spb0__physical_v1','L117_o',4,3,'S0'),('hbm_arch_vsN0','L118_o',5,4,'S1')]:
 old=(B/'fc9/selected_callers'/(f+'.sv')).read_text();s=old.replace('hfd_ep_static u_u_ep_','hfd_ep_static_fc9 u_u_ep_');net='w_u_ep_'+inst+'_fault_cause'
 s=s.replace('[10:0] '+net,'[8:0] '+net)
 if f=='hbm_arch_NE_io':s=s.replace(net+'[6:0]',net+'[4:0]').replace(net+'[10:7]',net+'[8:5]')
 elif f=='hbm_arch_vsN0':s=s.replace(net+'[9:0]',net+'[7:0]').replace(net+'[10]',net+'[8]')
 else:s=s.replace(net+'[10:0]',net+'[8:0]')
 s=prune(s,bus,hi,lo);oldw=7 if f=='hbm_arch_NE_io'else 11;s=s.replace(f'#(.W({oldw})) u_bout_'+bus,f'#(.W({oldw-2})) u_bout_'+bus)
 assert s!=old and 'hfd_ep_static_fc9 u_u_ep_'in s
 (O/(f+'.sv')).write_text(s);rows.append(dict(module=f,source_sha256=sha(old),proposed_sha256=sha(s),carrier=bus,old_data_bits=oldw,new_data_bits=oldw-2,removed_old_data_indices=[hi,lo],epoch=dict(old=oldw,new=oldw-2)))
# Actual root consumers capture the compact physical vectors; no zero restoration
# is sent into the separate observer hard cut. Its true136-bit physical master
# must restore the old144 logical observation positions AFTER its own captures.
f=B/'fc9/selected_callers/hbm_arch_root.sv';old=f.read_text();s=old
for bus,oldw,hi,lo in [('L117_i',11,4,3),('L117m_i',11,4,3),('L118_i',11,5,4),('L125m_i',7,4,3)]:
 s=prune(s,bus,hi,lo);s=prune(s,bus+'_q',hi,lo);s=s.replace(f'#(.W({oldw})) u_bin_'+bus,f'#(.W({oldw-2})) u_bin_'+bus)
# Only OBS_C's selected N144 master changes; fixed logical debug indices stay144
# inside the additive observer master. All other observer/relay uses untouched.
s=s.replace('ot_hbm_obs_leaf #(.LID(0), .N(144),','ot_hbm_obs_leaf_fc136 #(.LID(0),')
assert 'ot_hbm_obs_leaf_fc136'in s and '.rx_i({L118_i_q[0]'in s
(O/'hbm_arch_root.sv').write_text(s)
model=dict(status='DISABLED_FC9_FOUR_CARRIERS_AND_ROOT_OBS136_JOIN_PREP',old_top='hfd_ep_static',new_top='hfd_ep_static_fc9',old_ABI=2288,new_ABI=2286,inputs=1148,outputs=1138,selected_static_instances=4,SRAMs_per_instance=4,macros_changed=False,clock_reset_changed=False,added_cycles=0,retained_fault_mapping=dict(new8_3='old10_5',new2_0='old2_0',fault_scalar='exact unchanged'),removed_old_fault_bits=[4,3],callers=rows,root_consumer=dict(module='hbm_arch_root',sha256=sha(old),proposed_sha256=sha(s),ports=['L117_i','L117m_i','L118_i','L125m_i'],fault_scalar_relay='L118_i_q[0] to ot_hbm_b2_ep_root_relay unchanged',observer='ot_hbm_obs_leaf N144/LID0/SYNC0 u_u_obs_C; compact136 physical input with old144 logical index semantics must join'),declared_state_delta=dict(child_fault_output=-2,per_source_and_root_boundary_data=-16,observer='separate candidate/mapped unmeasured'),holds=['Selected2288/source-native4NEQ2 remains preserved','Removedreservedbits native4semantic invariant pending FLOW rawAIG BASE+STEP; no zero assumption','OBS136 separate actual source/miter/typedpin join pending; no restore before its physical cut','Actual current physical lane/relay/pin plans must prune paired source+destination semantic identities','New nativeFC9SYNTH/officialLEC/faceguard NOTRUN','No default/caller/parent/calendar/clock/P&R adoption'])
(O/'event.json').write_text(json.dumps(model,indent=1)+'\n');print('FC9 trueABI2286, fourrealcarriers, actualrootOBS136join PREP')
