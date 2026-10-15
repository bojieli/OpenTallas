#!/usr/bin/env python3
"""Source-exact issue_pq control lockstep; seeded payloads are not checkpoint weights."""
import argparse, ast, hashlib, json, subprocess
from pathlib import Path
import compile_hbm_smh_issue_static as C
ROOT=C.ROOT

def production():
    tree=ast.parse((ROOT/'tools/dshbm_matched_sm_seq.py').read_text())
    env={}
    # Evaluate only the immutable sequence definitions, never run generator/simulator.
    for node in tree.body:
        if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id in ('L20','WARM','WG','OTHER','SEQS') for t in node.targets):
            exec(compile(ast.Module(body=[node],type_ignores=[]),'<sequence definitions>','exec'),env)
    return env['SEQS']

def prepare(out):
    out.mkdir(parents=True,exist_ok=True)
    cases=[]
    for gs in (False,True):
        for g in range(1,17):
            for r in (1,7,8,9,17):
                cases.append(dict(rows=r,groups=g,fmt=g%3,gs=gs,c=8,launch_cycle=1+(g+r)%8))
    for name, seq in production().items():
        launch=8; ops=[]
        for tag,fmt,k,r,load in seq:
            op=C.normalize(dict(rows=r,K=k,fmt=fmt,launch_cycle=launch,tag=tag,load=load))
            ops.append(op); cases.append(op)
            launch=list(C.issue_slots(op))[-1]['cycle']+64
        data=C.compile_manifest({'ops':ops})
        (out/(name+'.ops.json')).write_text(json.dumps({'ops':ops,'scope':'immutable priced shapes; no released checkpoint payload'},indent=2)+'\n')
        (out/(name+'.programme83.hex')).write_text(''.join(f'{w:021x}\n' for w in data.pop('commands')))
        data.pop('packets'); (out/(name+'.calendar.json')).write_text(json.dumps(data,indent=2)+'\n')
    for i,o in enumerate(cases):
        ss=list(C.issue_slots(o)); n=ss[-1]['cycle']+4
        expected=[0]*n
        for s in ss: expected[s['cycle']]=(1<<26)|C.control(s)
        (out/f'case{i}.hex').write_text(''.join(f'{w:07x}\n' for w in expected))
    (out/'cases.json').write_text(json.dumps(cases))
    return cases

TB=r'''`timescale 1ns/1ps
module tb;
reg clk=0; always #5 clk=~clk;
reg rst_n=0,start_v=0; wire launch,iss_v,ok,first,last,glast; wire [12:0] row; wire [2:0] slot; wire [6:0] xa;
integer rows,groups,gs,fmt,lc,n,cy,i,mutant; reg [26:0] expected[0:200000]; reg [26:0] got; reg [1023:0] file;
ot_hbm_accel_issue_pq #(.IL(8),.RMAX(4096),.XDEPTH(128),.NOUT(4),.DBF(11),.SLAT(7)) dut(
.clk(clk),.rst_n(rst_n),.start_v(start_v),.launch(launch),.op_rows(13'(rows)),.op_c(16'd8),.op_g(8'(groups)),.op_gs(1'(gs)),.op_bf(fmt==0),
.w_valid(1'b1),.x_rdy(1'b1),.rdone(1'b0),.release_in(1'b0),.iss_v(iss_v),.iss_row_ok(ok),.iss_row(row),.iss_slot(slot),.iss_first(first),.iss_last(last),.iss_glast(glast),.xa(xa));
initial begin
if (!$value$plusargs("FILE=%s",file)) $fatal;
i=$value$plusargs("R=%d",rows); i=$value$plusargs("G=%d",groups); i=$value$plusargs("GS=%d",gs); i=$value$plusargs("F=%d",fmt); i=$value$plusargs("L=%d",lc); i=$value$plusargs("N=%d",n); i=$value$plusargs("M=%d",mutant);
$readmemh(file,expected,0,n-1);
repeat(3) @(negedge clk); rst_n=1;
for(cy=0;cy<n;cy=cy+1) begin
start_v=(cy>=lc-1 && cy<=lc);
#1;
if(launch !== (cy==lc)) $fatal(1,"launch cy%0d got%b",cy,launch);
got=iss_v?{1'b1,ok,first,last,row[11:0],glast,slot,xa}:27'b0;
if(mutant && iss_v) got[0]=~got[0];
if(got !== expected[cy]) $fatal(1,"control cy%0d got%h expected%h",cy,got,expected[cy]);
@(negedge clk);
end
$display("PASS"); $finish;
end
endmodule
'''

def run(out):
    cases=prepare(out); (out/'tb.sv').write_text(TB)
    subprocess.run(['iverilog','-g2012','-s','tb','-o',str(out/'sim'),str(out/'tb.sv'),str(ROOT/C.PINNED[0])],check=True)
    original=(ROOT/C.PINNED[0]).read_text()
    needle='assign xa = gs_q ? gs_xb + ti[XW-1:0] : xa_r;'
    assert original.count(needle)==1
    (out/'issue_mutant.sv').write_text(original.replace(needle, 'assign xa = (gs_q ? gs_xb + ti[XW-1:0] : xa_r) ^ 1;'))
    subprocess.run(['iverilog','-g2012','-s','tb','-o',str(out/'mutsim'),str(out/'tb.sv'),str(out/'issue_mutant.sv')],check=True)
    for i,o in enumerate(cases):
        n=list(C.issue_slots(o))[-1]['cycle']+4
        args=['vvp',str(out/'sim'),f'+FILE={out}/case{i}.hex',f'+R={o["rows"]}',f'+G={o["groups"]}',f'+GS={int(o["gs"])}',f'+F={o["fmt"]}',f'+L={o["launch_cycle"]}',f'+N={n}']
        p=subprocess.run(args,capture_output=True,text=True)
        if p.returncode: raise RuntimeError(f'case{i} {o}: {p.stdout} {p.stderr}')
        if i==0:
            m=subprocess.run([args[0],str(out/'mutsim')]+args[2:],capture_output=True,text=True)
            (out/'mutant.log').write_text(m.stdout+m.stderr)
            if m.returncode==0: raise RuntimeError('address mutant survived')
    hazard_tb=TB.replace('integer rows,groups,gs,fmt,lc,n,cy,i,mutant;', 'integer rows,groups,gs,fmt,lc,n,cy,i,mutant,lc2,ng,nf;')
    hazard_tb=hazard_tb.replace('$readmemh(file,expected,0,n-1);', 'i=$value$plusargs("L2=%d",lc2); i=$value$plusargs("NG=%d",ng); i=$value$plusargs("NF=%d",nf); $readmemh(file,expected,0,n-1);')
    hazard_tb=hazard_tb.replace('start_v=(cy>=lc-1 && cy<=lc);', 'if(cy==lc+1) begin groups=ng; fmt=nf; end start_v=(cy>=lc-1 && cy<=lc)||(cy>=lc+1 && cy<=lc2);')
    hazard_tb=hazard_tb.replace('(cy==lc))', '(cy==lc || cy==lc2))')
    (out/'hazard_tb.sv').write_text(hazard_tb)
    subprocess.run(['iverilog','-g2012','-s','tb','-o',str(out/'hazsim'),str(out/'hazard_tb.sv'),str(ROOT/C.PINNED[0])],check=True)
    hazards=0
    for pf,pg,nf,ng in [(0,g,1,1) for g in range(1,17)]+[(1,16,0,1),(2,16,1,2),(1,1,0,16)]:
        prev=dict(rows=1,groups=pg,fmt=pf,gs=True,launch_cycle=8)
        end=list(C.issue_slots(prev))[-1]['cycle']
        need=max(0,C.DBF*((pf==0)-(nf==0)),C.DBF*(pf==0)+C.SLAT*(pg-1).bit_length()-C.DBF*(nf==0)-C.SLAT*(ng-1).bit_length())
        lc2=end+need+2
        nxt=dict(rows=1,groups=ng,fmt=nf,gs=True,launch_cycle=lc2)
        data=C.compile_manifest({'ops':[prev,nxt]})
        n=len(data['commands'])+4; expected=[0]*n
        for slot in data['slots']: expected[slot['cycle']]=(1<<26)|C.control(slot)
        f=out/f'hazard{hazards}.hex'; f.write_text(''.join(f'{v:07x}\n' for v in expected))
        args=['vvp',str(out/'hazsim'),f'+FILE={f}','+R=1',f'+G={pg}','+GS=1',f'+F={pf}','+L=8',f'+N={n}',f'+L2={lc2}',f'+NG={ng}',f'+NF={nf}']
        result=subprocess.run(args,capture_output=True,text=True)
        if result.returncode: raise RuntimeError(f'hazard {pf,pg,nf,ng}: {result.stdout} {result.stderr}')
        # Compiler must reject one-cycle-early launch, including zero-gap setup exclusion.
        nxt['launch_cycle']-=1
        try: C.compile_manifest({'ops':[prev,nxt]})
        except ValueError: pass
        else: raise RuntimeError('early hazard accepted')
        hazards+=1
    verdict=dict(pass_=True,cases=len(cases),hazard_pairs=hazards,mutant_rejected=True,mutant_source_sha256=hashlib.sha256((out/'issue_mutant.sv').read_bytes()).hexdigest(),sources={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in C.PINNED},scope='actual issue_pq control only; no arithmetic or released checkpoint qualification')
    (out/'verdict.json').write_text(json.dumps(verdict,indent=2)+'\n'); print(json.dumps(verdict))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--prepare-only',action='store_true');a=p.parse_args()
    prepare(a.out) if a.prepare_only else run(a.out)
