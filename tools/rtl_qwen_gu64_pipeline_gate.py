#!/usr/bin/env python3
"""Actual GU/RTL-scale/L2-write gate with phase bubbles and finite credits."""
import argparse
import hashlib
import json
import re
from pathlib import Path
import subprocess
import numpy as np
import hdc_golden as G
import rtl_gpu_sm_exact as S
from w19_qwen_hbm_checkpoint import sm_snapshot

ROOT=Path(__file__).resolve().parents[1]
MARKER='COMPLETE GU64_L2 rows=32 epochs=2 trailing=160 negatives=3'


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def prepare(work):
    work.mkdir(parents=True,exist_ok=False)
    snap=sm_snapshot('000ba0898f5120a66d5905ccff333ebbbe28394d')
    sources=[]
    for p,h in snap['source_sha256'].items():
        if p.startswith('rtl/test/'):continue
        data=subprocess.check_output(['git','show',snap['commit']+':'+p],cwd=ROOT)
        assert hashlib.sha256(data).hexdigest()==h
        dst=work/'snapshot'/p;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(data)
        sources.append(str(dst.relative_to(work)))
    rng=np.random.default_rng(640409632)
    codes=rng.integers(-128,128,(32,4096),dtype=np.int16).astype(np.int8)
    x=G.to_bf16(rng.normal(size=4096).astype(np.float32))
    scales=G.to_bf16(rng.normal(size=32).astype(np.float32))
    scales[:5]=np.array([0,1,-1,2**-120,0.3333333],dtype=np.float32)
    scales=G.to_bf16(scales)
    expected=G.bits(G.mul(G.matvec(codes.astype(np.float32),x,64),scales))
    np.save(work/'expected.npy',expected)
    weights=[];xs=[]
    for wave in range(2):
        for t in range(64):
            for slot in range(8):
                rows=codes[wave*16+slot*2:wave*16+slot*2+2]
                weights.append(S.hexw(rows.reshape(2,64,64)[:,:,t].flatten().astype(np.uint8),1024,8))
                xs.append(S.hexw(S.bf16_bits(x.reshape(64,64)[:,t]),1024,16))
    (work/'weights.hex').write_text('\n'.join(weights)+'\n')
    (work/'x.hex').write_text('\n'.join(xs)+'\n')
    (work/'scales.hex').write_text('\n'.join(f'{int(n):04x}' for n in S.bf16_bits(scales))+'\n')
    (work/'tb.sv').write_text(BENCH)
    companions=['rtl/gpu/ot_gpu_qwen_gu64_pair.sv','rtl/gpu/ot_gpu_qwen_gu64_l2.sv']
    for p in companions:(work/Path(p).name).write_bytes((ROOT/p).read_bytes())
    command=['iverilog','-g2012','-s','tb','-o','sim.vvp','tb.sv']+[Path(p).name for p in companions]+sources
    (work/'execute.py').write_text(EXECUTE)
    host_paths=companions+['tools/rtl_qwen_gu64_pipeline_gate.py','tools/hdc_golden.py',
        'results/uarch/qwen_hbm_connected_20261001/GU_pipeline_before_RTL.json',
        'results/uarch/qwen_hbm_connected_20261001/GU_pipeline_sizing_correction_v2.json']
    record=dict(command=command,qualified_snapshot=snap,source_sha256={p:sha(ROOT/p) for p in host_paths},
        input_sha256={str(p.relative_to(work)):sha(p) for p in work.rglob('*') if p.is_file()},
        source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip())
    with (work/'prepared.json').open('x') as f:json.dump(record,f,indent=2);f.write('\n')
    return dict(status='PREPARED',full_token=False,**record)


def verify(work):
    p=json.loads((work/'prepared.json').read_text());e=json.loads((work/'execution.json').read_text())
    for name,h in p['input_sha256'].items():assert sha(work/name)==h,name
    for key,name in [('prepared_sha256','prepared.json'),('compile_log_sha256','compile.log'),
                     ('run_log_sha256','run.log'),('executable_sha256','sim.vvp')]:
        assert e[key]==sha(work/name),key
    if e['compile_rc']!=0 or e['run_rc']!=0:raise ValueError('Actual compile/run failed')
    log=(work/'run.log').read_text();lines=log.splitlines()
    if any(s in log.upper() for s in ['FATAL','TIMEOUT']):raise ValueError('Fatal/timeout evidence')
    if lines.count(MARKER)!=1:raise ValueError('Missing positive completion marker')
    if any(l.startswith('COMMITTED ') for l in lines[lines.index(MARKER)+1:]):
        raise ValueError('Writes after completion')
    expected=np.load(work/'expected.npy',allow_pickle=False);seen={};stats=[]
    for line in lines:
        if line.startswith('COMMITTED '):
            _,row,epoch,bits,cycle=line.split();row=int(row);epoch=int(epoch)
            index=row-250 if epoch==41 else row-506+16 if epoch==42 else -1
            if index not in range(32) or index in seen:raise ValueError('Unknown/duplicate row or epoch')
            seen[index]=int(bits,16)
        if line.startswith('STATS '):stats.append(line)
    mismatch=sum(seen.get(i)!=int(expected[i]) for i in range(32))
    if len(stats)!=2:raise ValueError('Missing actual stall/wait statistics')
    for epoch,line in zip([41,42],stats):
        counts={k:int(v) for k,v in re.findall(r'([A-Za-z_]+)=\s*(\d+)',line)}
        if counts.get('epoch')!=epoch or counts.get('steps')!=512:
            raise ValueError('Missing complete accepted product schedule')
        if any(counts.get(k,0)<=0 for k in ['memory_bubbles','result_stalls','commit_wait_cycles']):
            raise ValueError('Required bubble/backpressure/commit-wait coverage absent')
    return dict(status='PASS' if mismatch==0 and len(seen)==32 else 'FAIL',mismatches=mismatch,
        rows=32,K=4096,split=64,epochs=2,full_token=False,physical_qualification=False,
        scope='Actual GU products/tree,16 reserved addressed entries,RTL BF16 row-scale multiply,finite backpressured L2 writes and matching commits; no36clientHBM/vector/KV/TP/fulltoken',
        actual_cycle_statistics=stats,execution=e,source_commit=p['source_commit'],
        source_sha256=p['source_sha256'],qualified_snapshot=p['qualified_snapshot'],
        output_sha256={x.name:sha(x) for x in work.iterdir() if x.is_file()})


EXECUTE='''import hashlib,json,subprocess,time
from pathlib import Path
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
p=json.load(open('prepared.json'));t=time.monotonic()
with open('compile.log','w') as f:c=subprocess.run(p['command'],stdout=f,stderr=f)
rc=None
with open('run.log','w') as f:
 if c.returncode==0:rc=subprocess.run(['vvp','sim.vvp'],stdout=f,stderr=f).returncode
r=dict(compile_rc=c.returncode,run_rc=rc,elapsed_host_seconds=time.monotonic()-t,
 prepared_sha256=sha('prepared.json'),compile_log_sha256=sha('compile.log'),
 run_log_sha256=sha('run.log'),executable_sha256=sha('sim.vvp') if Path('sim.vvp').exists() else None)
with open('execution.json','x') as f:json.dump(r,f,indent=2)
raise SystemExit(c.returncode if c.returncode else (rc if rc is not None else 1))
'''

BENCH='''
module tb;
reg clk=0;always #5 clk=~clk;
reg rst_n=0,reserve_v=0,step_v=0,l2_ready=0,commit_v=0;
reg [2:0] rslot=0,sslot=0;reg [35:0] rrows=0;
reg [31:0] scales=0;reg [15:0] repoch=41;
reg [1023:0] w=0,x=0;reg [3:0] cid=0;reg [17:0] crow=0;reg [15:0] cep=0;
wire [2:0] phase;wire rready,sready,lv,fault;wire [3:0] lid;
wire [17:0] lrow;wire [15:0] lep;wire [31:0] ld;wire [4:0] credits;
ot_gpu_qwen_gu64_l2 #(.ENABLE_GU64_L2(1)) d(.clk(clk),.rst_n(rst_n),
.issue_phase(phase),.reserve_v(reserve_v),.reserve_ready(rready),.reserve_slot(rslot),
.reserve_rows(rrows),.reserve_scales_bf16(scales),.reserve_epoch(repoch),
.step_v(step_v),.step_ready(sready),.step_slot(sslot),.weights_i8(w),.x_bf16(x),
.l2_v(lv),.l2_ready(l2_ready),.l2_id(lid),.l2_row(lrow),.l2_epoch(lep),.l2_data(ld),
.commit_v(commit_v),.commit_id(cid),.commit_row(crow),.commit_epoch(cep),
.free_row_credits(credits),.fault(fault));
reg [1023:0] wm[0:1023],xm[0:1023];reg [15:0] sm[0:31];
reg [3:0] qid[0:15];reg [17:0] qrow[0:15];reg [15:0] qep[0:15];reg [31:0] qdata[0:15];
reg [31:0] actual_l2[0:31];integer counts[0:7];
integer wave,i,j,ix,cycle=0,steps,accepted,committed,age,bubbles,stalls,waits;
reg positive=1,held=0;reg [69:0] held_packet;
task tick;begin @(posedge clk);#1;@(negedge clk);end endtask
always @(posedge clk) begin
cycle=cycle+1;
if(rst_n && positive) begin
 if(lv && l2_ready) begin
  if(accepted>=16) $fatal(1,"too many L2 sends");
  qid[accepted]=lid;qrow[accepted]=lrow;qep[accepted]=lep;qdata[accepted]=ld;
  accepted=accepted+1;
 end
 if(commit_v) begin
  // These are real writes of the accepted RTL-scaled packet, not fixtures.
  ix=(cep==41) ? crow-250 : crow-506+16;
  if(ix<0 || ix>=32) $fatal(1,"bad actual L2 address");
  actual_l2[ix]=qdata[15-committed];
  $display("COMMITTED %d %d %h %d",crow,cep,actual_l2[ix],cycle);
  committed=committed+1;
 end
end
#1;if(rst_n && positive && fault) $fatal(1,"phase/credit/scale fault");
end
initial begin
$readmemh("weights.hex",wm);$readmemh("x.hex",xm);$readmemh("scales.hex",sm);
repeat(4) tick;rst_n=1;
for(wave=0;wave<2;wave=wave+1) begin
 steps=0;accepted=0;committed=0;age=0;bubbles=0;stalls=0;waits=0;held=0;
 repoch=41+wave;
 for(i=0;i<8;i=i+1) begin
  counts[i]=0;rslot=i;rrows[17:0]=(wave==0?250:506)+2*i;
  rrows[35:18]=(wave==0?251:507)+2*i;
  scales={sm[wave*16+2*i+1],sm[wave*16+2*i]};
  reserve_v=1;if(!rready) begin #1;if(!rready) $fatal(1,"reservation missing");end
  tick;reserve_v=0;
 end
 if(credits!=0) $fatal(1,"credits not reserved before first");
 while(committed<16) begin
  step_v=0;commit_v=0;sslot=phase;
  if(counts[phase]<64) begin
   // A missing memory return creates a real clock bubble, not tag advancement.
   if(cycle%11==3 || cycle%37<8) bubbles=bubbles+1;
   else begin
    j=wave*512+counts[phase]*8+phase;w=wm[j];x=xm[j];
    step_v=1;#1;if(!sready) $fatal(1,"phase issue not ready");
    counts[phase]=counts[phase]+1;steps=steps+1;
   end
  end
  if(steps==512) age=age+1;
  // Fill all16 result entries before releasing this output backpressure.
  l2_ready=(age>100 && cycle%13>=3);
  if(lv && !l2_ready) begin
   if(held && held_packet!={lid,lrow,lep,ld}) $fatal(1,"unstable stalled result");
   held=1;held_packet={lid,lrow,lep,ld};stalls=stalls+1;
  end else held=0;
  if(accepted==16 && committed==0 && credits!=0) $fatal(1,"send released credit before commit");
  // Finite actual L2 write pipeline: delay, reorder and backpressure writes.
  if(accepted==16 && age>130 && cycle%7>=2) begin
   cid=qid[15-committed];crow=qrow[15-committed];cep=qep[15-committed];commit_v=1;
  end else if(accepted>committed) waits=waits+1;
  tick;
 end
 step_v=0;commit_v=0;l2_ready=0;tick;
 if(credits!=16) $fatal(1,"credits did not follow both actual commits");
 $display("STATS epoch=%d steps=%d memory_bubbles=%d result_stalls=%d commit_wait_cycles=%d final_cycle=%d",repoch,steps,bubbles,stalls,waits,cycle);
end
repeat(160) tick;if(fault) $fatal(1,"late fault");
positive=0;
// A caller cannot issue before it owns both result credits.
rst_n=0;repeat(3) tick;rst_n=1;sslot=phase;step_v=1;tick;step_v=0;
if(!fault) $fatal(1,"missing reservation accepted");
rst_n=0;repeat(3) tick;rst_n=1;reserve_v=1;rslot=0;rrows={18'd901,18'd900};tick;reserve_v=0;
sslot=phase^1;step_v=1;tick;step_v=0;
if(!fault) $fatal(1,"wrong actual clock phase accepted");
rst_n=0;repeat(3) tick;rst_n=1;reserve_v=1;tick;reserve_v=0;
commit_v=1;cid=0;crow=900;cep=repoch+1;tick;commit_v=0;
if(!fault) $fatal(1,"stale/premature L2 commit accepted");
$display("COMPLETE GU64_L2 rows=32 epochs=2 trailing=160 negatives=3");$finish;
end
initial begin #60000;$fatal(1,"TIMEOUT");end
endmodule
'''


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--work',type=Path,required=True)
    ap.add_argument('--prepare-only',action='store_true');ap.add_argument('--verify-existing',action='store_true')
    a=ap.parse_args();work=a.work.resolve()
    try:
        if a.verify_existing:record=verify(work)
        else:
            record=prepare(work)
            if not a.prepare_only:
                subprocess.run(['python3','execute.py'],cwd=work,timeout=1200);record=verify(work)
    except Exception as e:
        if not work.exists():raise
        record=dict(status='FAIL',error=str(e),full_token=False)
    name='prepare_receipt.json' if a.prepare_only else 'verdict.json'
    with (work/name).open('x') as f:json.dump(record,f,indent=2);f.write('\n')
    raise SystemExit(0 if record['status'] in ('PASS','PREPARED') else 1)
