#!/usr/bin/env python3
"""Smallest current HOST-mux/HBC witness for a legal data/control collision.

Compile a new160-word HEAD context with static slots. After COMMIT send two
ordinary type7 payloads differing in one bit: the first is forwarded, the second
has the HBC magic/address and is wrongly claimed. All payload FP32 words are
finite. This diagnoses the shared namespace; it is not a production token gate.
"""
import argparse
import json
from pathlib import Path
import subprocess
from head_entry_schedule import compile_entry

ROOT=Path(__file__).resolve().parents[2]
TB=r'''`timescale 1ns/1ps
module tb_head_hbc_collision;
reg ck=0,rn=0;always #0.4165 ck=~ck;
reg hv=0;reg[552:0]hd=0;
wire[1103:0]from_prev,local_ring;
wire ctx;wire[47:0]boot,epoch;wire[7:0]fault;
wire[511:0]fields;wire ctxbk;wire[47:0]epochbk;
wire[16:0]muxfault;wire cv;wire[552:0]cd;wire[1:0]tv;wire[1105:0]td;
wire slot=(boot==@HEADER@)||(boot==@HEADER@+4)||(boot==@COMMIT@);
ot_s81hd_host_frame_mux #(.HBC_SCOPE(@SCOPE@))m(.ck(ck),.rst_n(rn),.context_valid(ctx),.boot_control_slot(slot),
 .host0_v(hv),.host1_v(1'b0),.host0_d(hd),.host1_d(553'd0),
 .local_ring(local_ring),.source_fault(17'd0),.ctl_v(1'b0),.ctl_d(553'd0),
 .from_prev(from_prev),.ctl_rx_v(cv),.ctl_rx_d(cd),.lane_tx_v(tv),.lane_tx_d(td),.fault(muxfault));
dsdv_hbc1_loader #(.ENABLE(1),.LOCAL_STAGE(@STAGE@),.LOCAL_RANK(@RANK@),.PHASE_BOUND(1),
 .VARIABLE_WORDS(1),.CLOCK_RESET_ID(64'd@IDENTITY@),.BOOT_HEADER_EDGE(48'd@HEADER@),
 .BOOT_COMMIT_EDGE(48'd@COMMIT@))h(.ck(ck),.rst_n(rn),.ring_i(from_prev),.job_active(1'b0),
 .local_ring(local_ring),.active_fields(fields),.context_valid(ctx),.receiver_edge(epoch),.boot_edge(boot),
 .fault(fault),.context_valid_bk(ctxbk),.receiver_edge_bk(epochbk));
integer c=0,control_seen=0,collision_claimed=0;
localparam[511:0]DATA=(512'h31434248 | (512'd@STAGE@<<40) | (512'd@RANK@<<48));
function automatic[552:0]fr(input[511:0]p);fr={1'b1,24'd0,p,12'd0,4'd7};endfunction
always@(negedge ck)begin
 c=c+1;rn=(c>=8);hv=0;hd=0;
 @SLOTS@
 if(c==@CONTROL@)begin
  if(!ctx||fault)$fatal(1,"compiled HBC context not admitted ctx%b fault%h",ctx,fault);
  if(fields[281:272]!=160)$fatal(1,"HEAD word count wrong");
  hv=1;hd=fr(DATA^512'd1);
 end
 if(c==@CONTROL_CHECK@)begin
  if(!cv||cd[527:16]!=(DATA^512'd1)||fault)$fatal(1,"ordinary one-bit control failed");
  control_seen=1;
 end
 if(c==@COLLISION@)begin hv=1;hd=fr(DATA);end
 if(c==@COLLISION_CHECK@)begin
  if(@SCOPE@==0)begin
   if(local_ring[0]||cv)$fatal(1,"expected current HBC classification did not claim matching data");
  end else if(!cv||cd[527:16]!=DATA)$fatal(1,"candidate lost legal finite activation payload");
  collision_claimed=1;
 end
 if(c==@FINISH@)begin
  if(!control_seen||!collision_claimed||((@SCOPE@==0)?fault==0:fault!=0))$fatal(1,"unexpected namespace result");
  if(@SCOPE@==0)$display("HEAD_HBC_PAYLOAD_COLLISION CONFIRMED stage%0d rank%0d fault%h data%h controlforward1 collisionforward0",@STAGE@,@RANK@,fault,DATA);
  else $display("HEAD_HBC_PAYLOAD_NAMESPACE PASS scope%0d stage%0d rank%0d fault%h controlforward1 collisionforward1 words160 addedcycles0",@SCOPE@,@STAGE@,@RANK@,fault);
  $finish;
 end
end
endmodule
'''


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--scope',type=int,choices=(0,1,2),default=0)
    a=p.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
    job=dict(rank=3,tid=37,user=0,position=0,token=7,epoch=1,programme=9,
             host_word_count=160,plen=1,glen=0,group=4,rbase=97024,
             issue_offset=20,issue_period=10357,merge_deadline=10000)
    timing=dict(scope='CURRENT_PROVIDER_ENTRY_ONLY',reset_deassert_edge=8,host_counter_zero_edge=10,
                link_ready_edge=24,peer_to_hbc_input=0,peer_frame_period=4,
                peer_launch_modulus=2,peer_launch_residue=0,peer_to_ctl_settled=37,
                commit_to_context_valid=1,ctl_start_offset=0)
    timing['hbc_command_scope']=a.scope
    schedule=compile_entry(dict(stages=81,TP=4,head_dies=4),job,timing)
    hp=schedule['host_params'];control=schedule['context_valid_global_edge']+3
    collision=control+4
    values=dict(STAGE=hp['LOCAL_STAGE'],RANK=hp['LOCAL_RANK'],IDENTITY=hp['CLOCK_RESET_ID'],SCOPE=a.scope,
                HEADER=hp['BOOT_HEADER_EDGE'],COMMIT=hp['BOOT_COMMIT_EDGE'],CONTROL=control,
                CONTROL_CHECK=control,COLLISION=collision,COLLISION_CHECK=collision,FINISH=collision+3)
    # Inspect combinational classification after the input is placed, before
    # the next rising edge latches the fault. No dynamic-ready scheduling.
    tb=TB.replace('@SLOTS@','\n'.join(f"if(c=={f['edge']})begin hv=1;hd=553'h{f['frame']:0139x};end"
                                      for f in schedule['frames'] if f['lane']==0))
    tb=tb.replace('if(c==@CONTROL_CHECK@)begin','if(c==@CONTROL_CHECK@)begin #0.01;')
    tb=tb.replace('if(c==@COLLISION_CHECK@)begin','if(c==@COLLISION_CHECK@)begin #0.01;')
    for key,value in values.items():tb=tb.replace('@'+key+'@',str(value))
    (out/'tb.sv').write_text(tb);(out/'schedule.json').write_text(json.dumps(schedule,indent=1)+'\n')
    files=['rtl/dsrom_sys/s81_head/ot_s81hd_host_ep_core.sv',
           'rtl/dsrom_sys/s81_dv/hostb/dsdv_hbc1_loader.sv',
           'rtl/dsrom_sys/s81_dv/hostb/dsdv_hostb_hold.sv',
           'rtl/dsrom_sys/s81_dv/hostb/dsdv_hostb_crc512.sv','rtl/lib/ot_reset_sync.sv']
    cmd=['verilator','--binary','--timing','-j','4','-O1','-Wno-fatal','--top-module','tb_head_hbc_collision',
         '--Mdir',str(out/'obj'),'-o','tb',*(str(ROOT/f) for f in files),str(out/'tb.sv')]
    with (out/'build.log').open('w') as log:subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,check=True)
    with (out/'run.log').open('w') as log:r=subprocess.run([str(out/'obj/tb')],stdout=log,stderr=subprocess.STDOUT)
    raw=(out/'run.log').read_text()
    expected='HEAD_HBC_PAYLOAD_COLLISION CONFIRMED' if a.scope==0 else 'HEAD_HBC_PAYLOAD_NAMESPACE PASS'
    if r.returncode or expected not in raw:
        raise SystemExit('witness failed; inspect '+str(out))
    (out/'verdict.json').write_text(json.dumps(dict(verdict='FAIL_DATA_CONTROL_NAMESPACE' if a.scope==0 else 'PASS_NAMESPACE_CANDIDATE',
        witness='actual HOST frame mux + HBC loader',control_forwarded=True,
        scope=a.scope,collision_forwarded=a.scope!=0,payload_FP32_words_all_finite=True,
        old_failure_preserved=True,full_head_token=False),indent=1)+'\n')
    print(raw.strip())


if __name__=='__main__':main()
