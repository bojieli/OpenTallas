#!/usr/bin/env python3
"""Generate additive secondary with CURRENT bank eligibility separated from commits.

Original 37-word source remains byte-identical. No additional persistent state.
"""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def source():
 root=ROOT
 # Additive successor: preserve committed secondary source unchanged.
 old=root/'rtl/experimental/w2_nc6_secondary_20261003/ot_w2_nc6_coded_secondary.sv'
 x=old.read_text().replace('module ot_w2_nc6_coded_secondary #','module ot_w2_nc6_coded_secondary_acyclic #')
 # Preserve all semantic guards while moving only CURRENT views.
 # hand-defined exact current-only cone (all original semantic conditions remain below)
 current=''' always_comb begin
  local_all_clean=&clean;integrity_bad=(|badword)||(|table_bad)||other_bad;local_idle=1;
  for(view_client=0;view_client<6;view_client=view_client+1)begin
  cache[view_client]=payload[view_client][8:0];pending[view_client]=payload[24+view_client][4:0];epoch[view_client]=payload[30+view_client][7:0];
  worker[view_client]={payload[6+3*view_client+2],payload[6+3*view_client+1],payload[6+3*view_client]};census[view_client]=0;
  for(view_slot=0;view_slot<16;view_slot=view_slot+1)if(table_state[2*(16*view_client+view_slot)+:2]!=0)census[view_client]=census[view_client]+1;
  if(cache[view_client][4:0]!=0||pending[view_client][3]||worker[view_client][92]||epoch[view_client][7]||table_pending[view_client])local_idle=0;
  end end
  // Bank eligibility is CURRENT pre-qualification, never the final semantic permit.
  // Actual state writes and public handshakes still require final normal_permit.
  always_comb begin
  request_bank_open=0;completion_bank_open=0;
  for(bank_client=0;bank_client<6;bank_client=bank_client+1)
  if(OPT_PROTECTION!=0&&rst_n&&!integrity_bad&&!payload[36][0]&&!logic_fault&&local_all_clean&&(&table_clean)&&other_clean&&
  !table_pending[bank_client]&&!worker[bank_client][92]&&!pending[bank_client][3]&&!epoch[bank_client][6])begin
  completion_bank_open[bank_client]=1;
  if(cache[bank_client][4:0]<16&&integer'(cache[bank_client][4:0])==census[bank_client]&&!admission_stop)request_bank_open[bank_client]=1;
  end end
 '''
 # Strip current assignments from original block, retain every semantic check and next_worker init.
 x=x.replace('  local_all_clean=&clean;integrity_bad=(|badword)||(|table_bad)||other_bad;\n','')
 x=x.replace('normal_permit=0;repair_busy=0;fault=0;rearm_ready=0;local_idle=1;','normal_permit=0;repair_busy=0;fault=0;rearm_ready=0;')
 x=x.replace("commit_roles='0;request_bank_open='0;completion_bank_open='0;scrub_ready='0;","commit_roles='0;scrub_ready='0;")
 a=x.index('   cache[client]=');b=x.index('   if(cache[client][4:0]>16',a)
 x=x[:a]+'   next_worker[client]=worker[client];\n'+x[b:]
 a=x.index('    if(normal_permit&&!table_pending[client]');b=x.index('    roles=accept_intent',a);x=x[:a]+x[b:]
 x=x.replace('commit_roles=0;normal_permit=0;request_bank_open=0;completion_bank_open=0;scrub_ready=0;fault=1;','commit_roles=0;normal_permit=0;scrub_ready=0;fault=1;')
 x=x.replace(' always_comb begin\n  write_enable', ' integer view_client,view_slot,bank_client;\n'+current+' always_comb begin\n  write_enable',1)
 return x

if __name__=="__main__":
 (ROOT/"rtl/experimental/w2_nc6_primary_20261003/ot_w2_nc6_coded_secondary_acyclic.sv").write_text(source())
