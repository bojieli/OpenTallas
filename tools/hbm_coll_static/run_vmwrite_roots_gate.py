#!/usr/bin/env python3
"""Full-shape v3/v2 miter, production exact bench and real clock/payload/fault negatives."""
import argparse,json,subprocess
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('out',type=Path);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
root=Path(__file__).resolve().parents[2];base=root/'rtl/hbm_accel/generic/collective/p2p';tools=root/'tools/hbm_coll_static'
v2=base/'ot_hgi_coll_static_vmwrite.sv';v3=base/'ot_hgi_coll_static_vmwrite_roots_v3.sv'
tb=(base/'tb_hgi_coll_static_vmwrite.sv').read_text()
tb=tb.replace('parameter integer MUT=0;',"parameter integer MUT=0;\n    parameter integer CLK_MUTE=0;\n    wire [13:0] roots = {14{clk}} & (14'h3fff ^ (CLK_MUTE == 0 ? 14'd0 : (14'd1 << (CLK_MUTE-1))));")
tb=tb.replace('ot_hgi_coll_static_vmwrite #','ot_hgi_coll_static_vmwrite_roots_v3 #').replace('.clk(clk),','.clk_ingress(roots[4:0]),.clk_bank(roots[12:5]),.clk_meta(roots[13]),')
tbpath=a.out/'tb_roots_production.sv';tbpath.write_text(tb);rows=[]
def run(name,top,sources,params=(),positive=True):
 sim=a.out/(name+'.vvp')
 b=subprocess.run(['iverilog','-g2012','-s',top,*params,'-o',str(sim),*map(str,sources)],capture_output=True,text=True)
 (a.out/(name+'.build.log')).write_text(b.stdout+b.stderr)
 if b.returncode:raise RuntimeError(name+' build failed')
 r=subprocess.run(['vvp',str(sim)],capture_output=True,text=True)
 (a.out/(name+'.log')).write_text(r.stdout+r.stderr)
 ok=(r.returncode==0)==positive
 rows.append(dict(name=name,expected_pass=positive,exit_code=r.returncode,gate_pass=ok))
 print(name, 'PASS' if ok else 'FAIL',r.stdout.strip().splitlines()[-1] if r.stdout.strip() else '')
 if not ok:raise RuntimeError(name+' unexpected outcome')
run('fullshape_miter','tb_vmwrite_roots_equiv',[v2,v3,tools/'tb_vmwrite_roots_equiv.sv'])
run('production_exact','tb_hgi_coll_static_vmwrite',[v3,tbpath])
for m in (1,2,3):run('functional_mutant_'+str(m),'tb_hgi_coll_static_vmwrite',[v3,tbpath],[f'-Ptb_hgi_coll_static_vmwrite.MUT={m}'],False)
for k in range(1,15):run('clock_mutant_'+str(k),'tb_hgi_coll_static_vmwrite',[v3,tbpath],[f'-Ptb_hgi_coll_static_vmwrite.CLK_MUTE={k}'],False)
(a.out/'summary.json').write_text(json.dumps(dict(scope='v3 source-only same-edge clock equivalence; physical/native OPEN',clock_roots=14,results=rows),indent=2)+'\n')
