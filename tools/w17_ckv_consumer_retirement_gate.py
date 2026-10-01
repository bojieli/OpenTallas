#!/usr/bin/env python3
"""Unchanged full K512 merger: final done waits for actual output acceptance."""
import argparse,hashlib,json,pathlib,re,subprocess,tempfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
PIN='d2c28c279c4b8df731f9c4937e790831529a954b'
PATH='rtl/chip/ot_chip_v41x_ckv_stream_merge.sv'
LIFECYCLE='rtl/chip/ot_chip_v41x_attn_desc_lifecycle.sv'
BENCH=r'''
`timescale 1ns/1ps
module tb;
reg clk=0;always #5 clk=~clk;
reg rst_n=0,job_v=0,ready=0;reg[2:0] cn=0;reg[9:0] rank=0;
reg[9215:0] rows=0;wire jr,v,done,fault;wire[2:0]take;wire[3:0]mask;wire[16959:0]words;wire[1:0]fc;
ot_chip_v41x_ckv_stream_merge #(.K(512)) dut(.clk(clk),.rst_n(rst_n),.job_v(job_v),.job_ready(jr),.window_count(8'd0),.n_sel(10'd512),.w_v(1'b0),.w_ready(),.w_m(4'd0),.w_rows(16896'd0),.c_n(cn),.c_take(take),.c_rank(rank),.c_rows(rows),.kv_v(v),.kv_ready(ready),.kv_m(mask),.kv_w(words),.done(done),.fault(fault),.fault_code(fc));
wire final_done,lfault;wire[3:0]lfc;wire[10:0]lb;wire[15:0]gen;reg engine_idle=1;
integer finish_due=0;reg merger_retired=0;
ot_chip_v41x_attn_desc_lifecycle #(.L0_ONLY(0)) lifecycle(.clk(clk),.rst_n(rst_n),.desc_v(job_v),.desc_user(10'd0),.desc_pos(21'd1048575),.desc_tiles(21'd1),.desc_k(21'd512),.desc_nout(21'd16),.desc_wbase(30'd0),.desc_ts(30'd512),.desc_ks(30'd512),.desc_js(30'd0),.desc_hg(2'd0),.desc_mmode(1'b1),.desc_accept(),.desc_gen(gen),.desc_rows(),.stage_v(cycle==9),.stage_gen(gen),.stage_rows(11'd4),.beat_v(v),.beat_ready(ready),.beat_gen(gen),.beat_mask(mask),.issue_v(cycle==11),.engine_idle(engine_idle),.service_fault(fault),.wrap_drained(1'b1),.issue_ok(),.done(final_done),.fault(lfault),.fault_code(lfc),.beats_accepted(lb));
integer cycle=0,accepted=0,mode=0,last_stall=0;reg[2:0] sampled_take;
initial begin if($value$plusargs("MODE=%d",mode))begin end end
always @(posedge clk)begin
 if(rst_n===1'b1)begin
  if(fault!==1'b0)$fatal(1,"consumer fault or unknown");
  if(v!==1'b0 && v!==1'b1)$fatal(1,"unknown output valid");
  if(v===1'b1 && ready===1'b1)begin
   if(mask!==4'hf)$fatal(1,"bad output mask");accepted=accepted+1;if(accepted==128)finish_due=cycle+7;
  end
  sampled_take=take;
  if(^sampled_take===1'bx || sampled_take>cn)$fatal(1,"invalid row acceptance");
  #1;
  if(done!==1'b0 && done!==1'b1)$fatal(1,"unknown completion");
  if(done===1'b1)begin
   if(accepted!==128 || rank+sampled_take!==512 || v!==1'b0 || jr!==1'b1)$fatal(1,"early consumer completion");
   merger_retired=1;
  end
  if(lfault!==1'b0)$fatal(1,"lifecycle fault");
  if(final_done!==1'b0 && final_done!==1'b1)$fatal(1,"unknown final consumer done");
  if(final_done===1'b1)begin
   if(!merger_retired || accepted!==128 || lb!==11'd128 || engine_idle!==1'b1)$fatal(1,"early final consumer completion");
   $display("PASS_CONSUMER_RETIRED rows=512 beats=128 mode=%0d last_stall=%0d actual_desc_done=1",mode,last_stall);$finish;
  end
  rank=rank+sampled_take;
 end
end
always @(negedge clk)begin
 cycle=cycle+1;
 if(cycle==5)rst_n=1;
 job_v=(cycle==7);
 if(cycle==12)engine_idle=0;
 if(finish_due!=0 && cycle>=finish_due && mode!=3)engine_idle=1;
 cn=(cycle>7 && rank<512)?4:0;
 ready=(mode!=1 && cycle>40 && (cycle%3!=0));
 if(mode==2 && accepted==127 && last_stall<20)begin ready=0;last_stall=last_stall+1;end
 if(cycle==600)$fatal(1,"finite consumer drain failed rows=%0d beats=%0d mode=%0d merger=%0d",rank,accepted,mode,merger_retired);
end
endmodule
'''
def main(out):
 raw=subprocess.check_output(['git','show',PIN+':'+PATH],cwd=ROOT)
 lifecycle=subprocess.check_output(['git','show',PIN+':'+LIFECYCLE],cwd=ROOT)
 cases={}
 with tempfile.TemporaryDirectory(prefix='w17-consumer-retire-',dir='/home/ubuntu') as tmp:
  d=pathlib.Path(tmp);(d/'rtl.sv').write_bytes(raw);(d/'tb.sv').write_text(BENCH);(d/'lifecycle.sv').write_bytes(lifecycle)
  c=subprocess.run(['iverilog','-g2012','-s','tb','-o',str(d/'gate'),str(d/'rtl.sv'),str(d/'lifecycle.sv'),str(d/'tb.sv')],capture_output=True,text=True,timeout=30)
  if c.returncode:raise RuntimeError(c.stderr)
  for name,mode in [('stalled_then_drained',0),('permanent_output_stall_rejected',1),('final_beat_stall_then_drained',2),('engine_not_retired_rejected',3)]:
   r=subprocess.run(['vvp',str(d/'gate'),f'+MODE={mode}'],capture_output=True,text=True,timeout=30);log=r.stdout+r.stderr
   if mode in (1,3):
    signature='rows=8 beats=0 mode=1 merger=0' if mode==1 else 'rows=512 beats=128 mode=3 merger=1'
    good=(r.returncode==1 and log.count('FATAL:')==1 and f'finite consumer drain failed {signature}' in log and 'Time: 6000000 Scope: tb' in log)
   else:
    good=(r.returncode==0 and f'PASS_CONSUMER_RETIRED rows=512 beats=128 mode={mode}' in log and (mode!=2 or 'last_stall=20' in log))
   cases[name]=dict(returncode=r.returncode,log=log,matched_expectation=good)
 result=dict(status='PASS_UNCHANGED_K512_CONSUMER_RETIREMENT' if all(x['matched_expectation'] for x in cases.values()) else 'FAIL_UNCHANGED_K512_CONSUMER_RETIREMENT',source=dict(commit=PIN,path=PATH,sha256=hashlib.sha256(raw).hexdigest()),lifecycle_source=dict(commit=PIN,path=LIFECYCLE,sha256=hashlib.sha256(lifecycle).hexdigest()),bench_sha256=hashlib.sha256(BENCH.encode()).hexdigest(),cases=cases,scope='actual fullK512 merger two-buffer drain and final emit handshake only; synthetic zero payload, actual descriptor DRAIN-to-IDLE exercised with fixture engine_idle delayed7cycles (test-only, NOT actual engine service bound); no attention arithmetic/storage-provider, peertransport, wholeprelease, fulltoken or physical qualification',hardware_admission=False)
 assert not out.exists();out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(cases,indent=2));return result['status'].startswith('PASS')
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--out',required=True,type=pathlib.Path);args=a.parse_args();raise SystemExit(0 if main(args.out) else 1)
