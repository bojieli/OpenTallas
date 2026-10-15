#!/usr/bin/env python3
"""Real registered static response tree and finite asynchronous CDC."""
import argparse,hashlib,json,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
TB=r'''`timescale 1ps/1fs
module tb;
parameter integer ONE_ROW=0,MUT_DATA=0,MUT_SKEW=0,MUT_TAG=0;
reg hbm_clk=0,core_clk=0,rst_n=0;always #512 hbm_clk=~hbm_clk;
integer phase_arg=0,ppm=0;real half_core;
initial begin if($value$plusargs("PHASE=%d",phase_arg))begin end if($value$plusargs("PPM=%d",ppm))begin end half_core=416.667*(1.0+ppm/1000000.0);#(phase_arg);forever #(half_core)core_clk=~core_clk;end
reg[31:0]kr_v;wire[31:0]kr_rdy;reg[543:0]kr_tag;reg[127:0]kr_beat=0;reg[8191:0]kr_data;
wire tree_v,tree_fault,full,empty;wire[264:0]tree_word,received_word;
ot_hbm_engram_return_tree_static #(.ONE_ROW(ONE_ROW),.MUT_DATA(MUT_DATA),.MUT_RIGHT_SKEW(MUT_SKEW)) tree(
 .node_clk({31{hbm_clk}}),.rst_n(rst_n),.kr_v(kr_v),.kr_rdy(kr_rdy),.kr_tag(kr_tag),.kr_beat(kr_beat),.kr_data(kr_data),.out_v(tree_v),.out_word(tree_word),.fault(tree_fault));
ot_hbm_accel_cdc_fifo #(.W(265),.AW(4)) fifo(.wclk(hbm_clk),.wrst_n(rst_n),.we(tree_v),.wdata(tree_word),.full(full),.rd_freed(),
 .rclk(core_clk),.rrst_n(rst_n),.re(!empty),.rdata(received_word),.empty(empty));
integer sent[0:31],last[0:31];reg[264:0]expected[0:1023];integer accepted_at[0:1023];
integer hc=0,wp=0,rp=0,outputs=0,last_output=-100,max_used=0,min_latency=999,max_latency=0;
function[255:0]pattern(input integer p,n);
 begin for(integer b=0;b<8;b=b+1)pattern[b*32+:32]=(32'h13579bdf*(b+1))^32'(p*4099+n*97);end
endfunction
always @*begin
 kr_v=0;kr_tag=0;kr_data=0;
 for(integer p=0;p<32;p=p+1)begin
  kr_v[p]=rst_n&&sent[p]<32;kr_tag[p*17+:17]=17'((p*17+sent[p])%512)|((MUT_TAG&&p==3)?17'h200:0);
  kr_data[p*256+:256]=pattern(p,sent[p]);
 end
end
always @(posedge hbm_clk)begin
 hc=hc+1;
 if(rst_n)begin
  if($countones(kr_rdy)>1)$fatal(1,"static reservation multiple PCs");
  for(integer p=0;p<32;p=p+1)if(kr_v[p]&&kr_rdy[p])begin
   if(last[p]>=0&&hc-last[p]!=64)$fatal(1,"perPC64edge fairness reservation");last[p]=hc;
   expected[wp]={9'((p*17+sent[p])%512),pattern(p,sent[p])};accepted_at[wp]=hc;wp=wp+1;sent[p]<=sent[p]+1;
  end
  if(tree_v)begin
   if(hc-last_output<2)$fatal(1,"unbalanced branch broke physical reservation arrival envelope");last_output=hc;
   if(outputs>=wp || tree_word!==expected[outputs])$fatal(1,"tree exact native tag/data/order item%0d",outputs);
   if(hc-accepted_at[outputs]<min_latency)min_latency=hc-accepted_at[outputs];if(hc-accepted_at[outputs]>max_latency)max_latency=hc-accepted_at[outputs];outputs=outputs+1;
  end
  #2;
  if(tree_fault||full)$fatal(1,"tree fault or finiteCDC overflow");
  if(((fifo.wbin-fifo.rsync_bin)&31)>max_used)max_used=(fifo.wbin-fifo.rsync_bin)&31;
  if(hc>2500)$fatal(1,"bounded return tree timeout");
 end
end
always @(posedge core_clk)if(rst_n&&!empty)begin
 if(rp>=wp||received_word!==expected[rp])$fatal(1,"actualCDC exact payload/order item%0d",rp);rp=rp+1;
 if(rp==1024)begin
  if(wp!=1024||outputs!=1024||min_latency!=(ONE_ROW?12:8)||max_latency!=min_latency||max_used>16)$fatal(1,"finite tree latency/occupancy");
  $display("PASS real return tree row%0d phase%0d ppm%0d payload1024 perPC64 latency%0d maxCDCused%0d",ONE_ROW,phase_arg,ppm,min_latency,max_used);$finish;
 end
end
initial begin for(integer p=0;p<32;p=p+1)begin sent[p]=0;last[p]=-1;end repeat(4)@(negedge hbm_clk);rst_n=1;end
endmodule
'''
def run(out):
 out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True);tb=out/'tb.sv';tb.write_text(TB);paths=['rtl/hbm_accel/service/ot_hbm_accel_cdc_fifo.sv','rtl/hbm_accel/engram_static_20261015/ot_hbm_engram_return_tree_static.sv'];runs=[];start=time.monotonic()
 profiles=[('two_row',0,0,0,0),('one_row',1,0,0,0),('tag_data_mutant',0,1,0,0),('branch_skew_mutant',0,0,1,0),('invalid_upper_tag',0,0,0,1)]
 for name,row,md,ms,mt in profiles:
  exe=out/name;cp=subprocess.run(['iverilog','-g2012','-s','tb',f'-Ptb.ONE_ROW={row}',f'-Ptb.MUT_DATA={md}',f'-Ptb.MUT_SKEW={ms}',f'-Ptb.MUT_TAG={mt}','-o',str(exe),*[str(ROOT/p)for p in paths],str(tb)],capture_output=True,text=True);(out/(name+'.build.log')).write_text(cp.stdout+cp.stderr);assert cp.returncode==0,cp.stdout+cp.stderr
  samples=[(p,ppm)for p in [0,104,208,312,416,520,624,728]for ppm in [-100,100]] if not(md or ms or mt) else [(104,0)]
  for phase,ppm in samples:
   rp=subprocess.run(['vvp',str(exe),f'+PHASE={phase}',f'+PPM={ppm}'],capture_output=True,text=True);tag=f'{name}_phase{phase}_ppm{ppm}';(out/(tag+'.run.log')).write_text(rp.stdout+rp.stderr);assert (rp.returncode==0)==(not(md or ms or mt)),rp.stdout+rp.stderr
   if not(md or ms or mt):assert 'PASS real return tree'in rp.stdout
   runs.append(dict(name=name,phase_ps=phase,core_drift_ppm=ppm,returncode=rp.returncode,output=rp.stdout.strip()))
 result=dict(schema='opentallas.hbm.engram.static_registered_return_tree.v1',status='pass',PCs=32,first_stage_pair_collectors=16,node_roots=31,per_PC_reservation_edges=64,global_minimum_response_spacing_HBM_edges=2,balanced_sample_latency_edges=dict(two_row=8,one_row=12),finite_CDC_entries=16,payloads_per_positive=1024,positive_phase_drift_cases=32,runs=runs,source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()for p in paths},wall_seconds=time.monotonic()-start,scope='Actual registered source/finiteCDC component, synthetic native K-return pins as input boundary. Fixed reservations remove a long combinational ready path. No ideal internal FIFO/model. Actual32-PC controller/Engram/releasedrow join, exact pin/relay placement<=500um, CTS/STA, universal service and original performance remain unqualified; candidate service reduction is explicit, not waived.')
 (out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);a=ap.parse_args();run(a.out)
