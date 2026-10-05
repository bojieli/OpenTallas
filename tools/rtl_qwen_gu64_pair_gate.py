#!/usr/bin/env python3
"""Append-only actual GU64 product/reduction gate; not a connected SM/token."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import numpy as np
import hdc_golden as G
import rtl_gpu_sm_exact as S
from w19_qwen_hbm_checkpoint import sm_snapshot

ROOT=Path(__file__).resolve().parents[1]


def run(work,prepare_only=False):
    work.mkdir(parents=True,exist_ok=False)
    snap=sm_snapshot('000ba0898f5120a66d5905ccff333ebbbe28394d')
    sources=[]
    for p,h in snap['source_sha256'].items():
        if p.startswith('rtl/test/') and not p.endswith('ot_hdc_prefix_sim.sv'):
            continue
        data=subprocess.check_output(['git','show',snap['commit']+':'+p],cwd=ROOT)
        assert hashlib.sha256(data).hexdigest()==h
        dst=work/'snapshot'/p;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(data)
        sources.append(str(dst))
    rng=np.random.default_rng(6404096)
    codes=rng.integers(-128,128,(16,4096),dtype=np.int16).astype(np.int8)
    x=G.to_bf16(rng.normal(size=4096).astype(np.float32))
    expected=G.bits(G.matvec(codes.astype(np.float32),x,split=64))
    weights=[];xs=[]
    for t in range(64):
        for slot in range(8):
            weights.append(S.hexw(np.concatenate([codes[2*slot].reshape(64,64)[:,t],
                codes[2*slot+1].reshape(64,64)[:,t]]).astype(np.uint8),1024,8))
            xs.append(S.hexw(S.bf16_bits(x.reshape(64,64)[:,t]),1024,16))
    (work/'weights.hex').write_text('\n'.join(weights)+'\n')
    (work/'x.hex').write_text('\n'.join(xs)+'\n')
    bench=work/'tb.sv'
    bench.write_text('''
module tb;
reg clk=0;always #5 clk=~clk;
reg rst_n=0,v=0,first=0,last=0;
reg [1023:0] w,x;reg [35:0] rows;reg [5:0] slots;
wire [1:0] ov;wire [63:0] sums;wire [35:0] rr;wire [5:0] rs;wire fault;
reg [1023:0] wm[0:511],xm[0:511]; integer i,n=0,cycle=0;
ot_gpu_qwen_gu64_pair #(.ENABLE_GU64(1)) d(.clk(clk),.rst_n(rst_n),
.v(v),.first(first),.last(last),.weights_i8(w),.x_bf16(x),
.global_rows(rows),.slots(slots),.ov(ov),.sums(sums),
.result_rows(rr),.result_slots(rs),.fault(fault));
always @(posedge clk) begin
#1;cycle=cycle+1;
if(rst_n && fault) $fatal(1,"arithmetic/tag fault");
if(ov[0]) begin $display("RESULT %d %d %h %d",rr[17:0],rs[2:0],sums[31:0],cycle);n=n+1;end
if(ov[1]) begin $display("RESULT %d %d %h %d",rr[35:18],rs[5:3],sums[63:32],cycle);n=n+1;end
end
initial begin
$readmemh("weights.hex",wm);$readmemh("x.hex",xm);
repeat(4) @(negedge clk);rst_n=1;
for(i=0;i<512;i=i+1) begin
v=1;first=i<8;last=i>=504;w=wm[i];x=xm[i];
rows[17:0]=250+2*(i%8);rows[35:18]=251+2*(i%8);
slots[2:0]=i%8;slots[5:3]=i%8;@(negedge clk);
end
v=0;first=0;last=0;repeat(160) @(negedge clk);
if(n!=16) $fatal(1,"missing rows %d",n);
if(fault) $fatal(1,"late arithmetic/tag fault");
$display("COMPLETE GU64 rows=16 trailing=160 fault=0");
$finish;
end
initial begin #20000;$fatal(1,"TIMEOUT");end
endmodule
''')
    companion='rtl/gpu/ot_gpu_qwen_gu64_pair.sv'
    local_companion=work/'companion.sv'
    local_companion.write_bytes((ROOT/companion).read_bytes())
    np.save(work/'expected.npy',expected)
    exe=work/'sim.vvp'
    command=['iverilog','-g2012','-s','tb','-o','sim.vvp','tb.sv','companion.sv']
    command += [str(Path(p).relative_to(work)) for p in sources]
    # Executed on the worker, with actual process return codes retained even
    # when compilation or simulation fails. No host timing is erased here.
    (work/'execute.py').write_text('''import hashlib,json,subprocess,time
from pathlib import Path
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
p=json.load(open('prepared.json'));t=time.monotonic()
with open('compile.log','w') as f:
 c=subprocess.run(p['command'],stdout=f,stderr=f)
rc=None
with open('run.log','w') as f:
 if c.returncode==0: rc=subprocess.run(['vvp','sim.vvp'],stdout=f,stderr=f).returncode
r=dict(compile_rc=c.returncode,run_rc=rc,elapsed_host_seconds=time.monotonic()-t,
 prepared_sha256=sha('prepared.json'),compile_log_sha256=sha('compile.log'),
 run_log_sha256=sha('run.log'),executable_sha256=sha('sim.vvp') if Path('sim.vvp').exists() else None)
with open('execution.json','x') as f:json.dump(r,f,indent=2)
raise SystemExit(c.returncode if c.returncode else (rc if rc is not None else 1))
''')
    prepared=dict(command=command,qualified_snapshot=snap,
        source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
            for p in [companion,'tools/rtl_qwen_gu64_pair_gate.py','tools/hdc_golden.py']})
    prepared['input_sha256']={str(p.relative_to(work)):hashlib.sha256(p.read_bytes()).hexdigest()
        for p in work.rglob('*') if p.is_file()}
    (work/'prepared.json').write_text(json.dumps(prepared,indent=2)+'\n')
    if prepare_only:return dict(status='PREPARED',full_token=False,**prepared)
    subprocess.run(['python3','execute.py'],cwd=work,timeout=1200)
    return verify(work)


def verify(work):
    prepared=json.loads((work/'prepared.json').read_text())
    for p,h in prepared['input_sha256'].items():
        assert hashlib.sha256((work/p).read_bytes()).hexdigest()==h,p
    execution=json.loads((work/'execution.json').read_text())
    for key,p in [('prepared_sha256','prepared.json'),('compile_log_sha256','compile.log'),
                  ('run_log_sha256','run.log'),('executable_sha256','sim.vvp')]:
        assert execution[key]==hashlib.sha256((work/p).read_bytes()).hexdigest(),key
    if execution['compile_rc']!=0 or execution['run_rc']!=0:
        raise ValueError('Nonzero or missing actual compile/run return code')
    log=(work/'run.log').read_text()
    if any(word in log.upper() for word in ('FATAL','TIMEOUT')):
        raise ValueError('Fatal/timeout evidence cannot establish PASS')
    marker='COMPLETE GU64 rows=16 trailing=160 fault=0'
    lines=log.splitlines()
    if lines.count(marker)!=1:
        raise ValueError('Missing or duplicate positive bench completion marker')
    if any(line.startswith('RESULT ') for line in lines[lines.index(marker)+1:]):
        raise ValueError('Results after completion marker')
    expected=np.load(work/'expected.npy',allow_pickle=False)
    seen={}
    for line in lines:
        if line.startswith('RESULT '):
            _,row,slot,bits,cycle=line.split();row=int(row)
            assert row not in seen and int(slot)==(row-250)//2
            seen[row]=int(bits,16)
    mismatches=sum(seen.get(250+i)!=int(expected[i]) for i in range(16))
    return dict(status='PASS' if mismatches==0 and len(seen)==16 else 'FAIL',
        mismatches=mismatches,rows=16,K=4096,golden_split=64,full_token=False,
        scope='Actual INT8 products, ordered circulating sums and two independent64 trees; no row scale, shared service, attention or connected token',
        qualified_snapshot=prepared['qualified_snapshot'],source_sha256=prepared['source_sha256'],
        execution=execution,
        output_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in work.iterdir() if p.is_file()})


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--work',type=Path,required=True)
    ap.add_argument('--prepare-only',action='store_true')
    ap.add_argument('--verify-existing',action='store_true')
    a=ap.parse_args()
    try: record=verify(a.work.resolve()) if a.verify_existing else run(a.work.resolve(),a.prepare_only)
    except Exception as e:
        record=dict(status='FAIL',error=str(e),full_token=False)
        if not a.work.exists(): raise
    name='prepare_receipt.json' if a.prepare_only else 'verdict.json'
    with (a.work/name).open('x') as f:json.dump(record,f,indent=2);f.write('\n')
    raise SystemExit(0 if record['status'] in ('PASS','PREPARED') else 1)
