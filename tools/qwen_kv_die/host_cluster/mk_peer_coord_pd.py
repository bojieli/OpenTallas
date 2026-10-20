# KV-HOST/PEER r6 (10-19) generator, committed by KV-HOST4; run from anywhere: writes into the repository root of this file.
import os; W=os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../..')+'/'
HI=W+'rtl/qwen_sys/host_integrated_20261014/'
OUT=W+'rtl/qwen_sys/host_cluster_20261017/peer_pd/'
src=open(HI+'qkd_host_peer_coordinator_codec.sv').read()
def sub(old,new,count=1):
    global src
    n=src.count(old); assert n==count,(n,old[:90]); src=src.replace(old,new)
HDR='''// KV-HOST/PEER r6 (10-19): qkd_host_peer_coordinator_codec_pd = rtl/qwen_sys/host_integrated_20261014/
// qkd_host_peer_coordinator_codec.sv (unchanged) with ONE change (SAFE item 4; r5 gate CTS classes
// coordinator token_grant_* -> 81-b allocation compare -> TX choice -> root mux grant g -80.5 / physical_tx_data -55.3):
//  ALLOCATION STAGE (+1 ck edge): the allocated_* inputs pass one register (async-cleared by por_n, as the lifecycle
//  registers that drive them) before the codec uses them, and the per-rank "allocation changed since last sent" test
//  (last_allocation[k] != allocation) is a register adiff[k] computed one edge ahead from the next-edge values
//  (alloc' = the inputs, last' = sent ? alloc_q : last), so the TX choice / tx_valid come from registers only.
//  Equivalent to the original codec with the allocated_* inputs delayed one edge (bench rtl/test/qwen_host/hr_peer_codec_pd_1019:
//  every output every edge vs the original fed through the same one-edge por_n-cleared delay; QKD_HR_PE_CPD_MUTANT drops
//  the sent bypass of adiff and must FAIL).  Schedule: class6 allocation broadcast and the class1 request check see a
//  new allocation one ck_codec edge later (HOST lifecycle transport class9, not the per-token compute schedule).
'''
src=HDR+src
sub('module qkd_host_peer_coordinator_codec(','module qkd_host_peer_coordinator_codec_pd(')
sub(' input wire allocated_valid,allocated_delivered,input wire[58:0]allocated_tag,input wire[1:0]allocated_gen,input wire[17:0]allocated_position,',
    ' input wire allocated_valid_i,allocated_delivered_i,input wire[58:0]allocated_tag_i,input wire[1:0]allocated_gen_i,input wire[17:0]allocated_position_i,')
sub(' wire[80:0]allocation={allocated_position,allocated_gen,allocated_tag,allocated_delivered,allocated_valid};',
''' // r6 allocation stage (+1 edge) and the registered per-rank change test
 reg allocated_valid,allocated_delivered;reg[58:0]allocated_tag;reg[1:0]allocated_gen;reg[17:0]allocated_position;
 wire[80:0]allocation={allocated_position,allocated_gen,allocated_tag,allocated_delivered,allocated_valid};
 wire[80:0]allocation_n={allocated_position_i,allocated_gen_i,allocated_tag_i,allocated_delivered_i,allocated_valid_i};
 reg[7:0]adiff;   // == (last_allocation[k] != allocation) every edge''')
sub("   else if(!allocation_sent[k]||last_allocation[k]!=allocation)begin choice[k]=6;tx_data[k*512+30+:81]=allocation;end",
    "   else if(!allocation_sent[k]||adiff[k])begin choice[k]=6;tx_data[k*512+30+:81]=allocation;end")
# reset + per-edge update: put in the por_n always block
sub("   for(i=0;i<8;i=i+1)begin rx_seq[i]<=0;tx_seq[i]<=0;last_recovery[i]<=0;last_allocation[i]<=0;end\n  end else begin",
"""   for(i=0;i<8;i=i+1)begin rx_seq[i]<=0;tx_seq[i]<=0;last_recovery[i]<=0;last_allocation[i]<=0;end
   allocated_valid<=0;allocated_delivered<=0;allocated_tag<=0;allocated_gen<=0;allocated_position<=0;adiff<=0;
  end else begin
   {allocated_position,allocated_gen,allocated_tag,allocated_delivered,allocated_valid}<=allocation_n;
   for(i=0;i<8;i=i+1)begin
`ifdef QKD_HR_PE_CPD_MUTANT
    adiff[i]<=allocation_n!=last_allocation[i];
`else
    adiff[i]<=(tx_valid[i]&&tx_ready[i]&&choice[i]==6)?allocation_n!=allocation:allocation_n!=last_allocation[i];
`endif
   end""")
open(OUT+'qkd_host_peer_coordinator_codec_pd.sv','w').write(src)
# coordinator fork: only the codec module name changes
c=open(HI+'qkd_host_tp8_coordinator.sv').read()
assert c.count('module qkd_host_tp8_coordinator(')==1 and c.count(' qkd_host_peer_coordinator_codec u_peer(')==1
assert c.count('.allocated_valid(allocated_valid),.allocated_delivered(allocated_delivered),.allocated_tag(token_grant_tag),.allocated_gen(token_grant_gen),.allocated_position(token_grant_position),')==1
c=c.replace('module qkd_host_tp8_coordinator(','module qkd_host_tp8_coordinator_pd(').replace(' qkd_host_peer_coordinator_codec u_peer(',' qkd_host_peer_coordinator_codec_pd u_peer(')
c=c.replace('.allocated_valid(allocated_valid),.allocated_delivered(allocated_delivered),.allocated_tag(token_grant_tag),.allocated_gen(token_grant_gen),.allocated_position(token_grant_position),',
            '.allocated_valid_i(allocated_valid),.allocated_delivered_i(allocated_delivered),.allocated_tag_i(token_grant_tag),.allocated_gen_i(token_grant_gen),.allocated_position_i(token_grant_position),')
c='''// KV-HOST/PEER r6 (10-19): qkd_host_tp8_coordinator_pd = rtl/qwen_sys/host_integrated_20261014/qkd_host_tp8_coordinator.sv
// (unchanged) binding qkd_host_peer_coordinator_codec_pd (allocation stage +1 edge, registered per-rank change test) in
// place of the class9 codec; nothing else differs (tools/qwen_kv_die/host_cluster/mk_peer_pd2.py).
'''+c
open(OUT+'qkd_host_tp8_coordinator_pd.sv','w').write(c)
print('ok')
