#!/usr/bin/env python3
"""QC-TYPES-11: START transport bench over every writer-START type of plan_qc53v4nS, using the real emitter
(clock_landings._writer_start_rtl) and real ot_dp_landing_relay RTL. Per type: q must equal start delayed by W+1 under an
active start/reset pattern; mutants: skip one stage (bypass) and reset one phase late must be caught."""
import json,re,subprocess,sys,tempfile
from pathlib import Path
S=Path('/srv/opentallas-scratch3/claude/codex-qc-compose-1113/src_fixed')
Q=Path('/srv/opentallas-scratch3/claude/qct11/start')
sys.path.insert(0,str(S/'tools/die_plan'))
from clock_landings import Landings
plan=json.loads((Q/'plan/plan_qc53v4nS.json').read_text())
rep=json.loads((Q/'report.json').read_text())
rtl=Path(sys.argv[1]);out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
cells=[S/'rtl/common/ot_dp_clk_landing_ca.sv',S/'rtl/common/ot_meso_fifo.sv']
land=Landings.__new__(Landings);land.plan=plan;land.types=plan['partition_types'];land.ca_type={};land.reset_placements={}
def run(name,files,expect):
    t=out/name
    p=subprocess.run(['iverilog','-g2012','-s','tb','-o',str(t),*map(str,files)],text=True,capture_output=True)
    if p.returncode: return 'COMPILE-ERR '+p.stderr[-300:]
    p=subprocess.run(['vvp',str(t)],text=True,capture_output=True,timeout=120)
    good=p.returncode==0 and 'PASS' in p.stdout
    t.unlink(missing_ok=True)
    return None if good==expect else f'UNEXPECTED good={good} {p.stdout[-200:]}'
res={};bad=0;nb=0
for n,r in sorted(rep.items()):
    c=plan['partition_types'][n]['clock'];w=c.get('landing_writer_start')
    if not w: res[n]='no writer'; continue
    W=int(w['depth']);phys=W-int(bool(w.get('reuse_relay_origin')))
    sv=rtl/(n+'.sv')
    if not sv.exists(): sv=rtl/(plan['partition_types'][n]['module']+'__'+n+'.sv')
    if not sv.exists(): sv=rtl/(plan['partition_types'][n]['module']+'.sv')
    body=sv.read_text();head=body[:body.index(');')+2];logic=[];faces=[]
    reuse=bool(w.get('reuse_relay_origin'))
    if reuse: land.ca_type[n]={'role':('relay',)}
    origin='wire cland_start; ot_dp_landing_relay u_origin (.clk(clk), .rst_raw_n(raw), .d(cland_start_d), .q(cland_start));\n' if reuse else ''
    br=sorted(w['branches'])
    try:
        for i,bus in enumerate(br):
            prev=land._writer_start_rtl(n,bus,head,body,logic)
            faces.append(f'ot_dp_landing_relay face_{i} (.clk(clk), .rst_raw_n(raw), .d({prev}), .q(q[{i}]));')
    except Exception as e:
        res[n]='EMIT '+repr(e)[:200];bad+=1;continue
    raws=sorted({s['raw_reset'] for b in w['branches'].values() for s in b['stages']})
    mod=f"module candidate(input clk,input start,input raw,output [{len(br)-1}:0] q); wire cland_start_d=start;\n"+origin+'\n'.join(f'wire {x}; assign {x}=raw;' for x in raws)+'\n'+'\n'.join(logic+faces)+'\nendmodule\n'
    D=phys+1+int(bool(w.get('reuse_relay_origin')))
    tb=f'''module tb;
 reg clk=0; always #5 clk=~clk; reg root=0,start=0,raw=0; reg [{D-1}:0] model=0; wire [{len(br)-1}:0] q; integer cycle=0,checked=0;
 candidate dut(clk,start,raw,q);
 always @(posedge clk) begin raw<=root; if(!raw) model<=0; else model<={'{model[%d:0],start}'%(D-2) if D>1 else 'start'};
  #1; if(cycle>{D+3}) begin if(q!=={{{len(br)}{{model[{D-1}]}}}}) $fatal(1,"mismatch %0d",cycle); checked=checked+1; end end
 initial begin repeat(640) begin @(negedge clk);cycle=cycle+1;root=(cycle%160>=10&&cycle%160<150&&cycle%160!=80);start=(cycle%160>=30&&cycle%160<153);end
 if(checked<400)$fatal(1,"no coverage");$display("PASS %0d",checked);$finish; end
 endmodule
'''
    d=out/n;d.mkdir(exist_ok=True)
    (d/'c.sv').write_text(mod);(d/'tb.sv').write_text(tb)
    e=run(n+'_ok',[d/'c.sv',d/'tb.sv',*cells],True)
    # mutant 1: last face of first branch bypasses its last stage
    m1=None
    if phys>=1:
        first=[l for l in faces if 'face_0 ' in l][0]
        pv=re.search(r'\.d\((\w+)\)',first)[1]
        drv=re.search(r'\.d\((\w+)\), \.q\('+re.escape(pv)+r'\)',mod)
        if drv:
            (d/'m1.sv').write_text(mod.replace(first,first.replace(f'.d({pv})',f'.d({drv[1]})')));m1=run(n+'_m1',[d/'m1.sv',d/'tb.sv',*cells],False)
        else: m1='no driver found'
    # mutant 2: raw reset one phase late on every stage
    (d/'m2.sv').write_text(mod.replace('wire cland_start_d=start;','wire cland_start_d=start; reg rawd=0; always @(posedge clk) rawd<=raw;').replace('assign ','assign ').replace('=raw;','=rawd;'))
    m2=run(n+'_m2',[d/'m2.sv',d/'tb.sv',*cells],False)
    nb+=len(br)
    res[n]=dict(W=W,phys=phys,branches=len(br),ok=e,m1=m1,m2=m2)
    if e or m1 or m2: bad+=1
(out/'bench.json').write_text(json.dumps(res,indent=1))
print('TYPES',len(res),'BRANCHES',nb,'BAD',bad)
for k,v in res.items():
    if isinstance(v,str) or v['ok'] or v['m1'] or v['m2']: print(k,v)
