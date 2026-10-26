#!/usr/bin/env python3
"""Source-only v6 clock partition: actual v4 miter, scheduled production and negatives."""
import argparse,hashlib,json,subprocess
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('out',type=Path);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
root=Path(__file__).resolve().parents[2];base=root/'rtl/hbm_accel/generic/collective/p2p';tools=root/'tools/hbm_coll_static'
v4=base/'ot_hgi_coll_static_vmwrite.sv';v6=base/'ot_hgi_coll_static_vmwrite_roots_v6.sv';physical=base/'ot_hgi_coll_static_vmwrite_roots_v6_physical.sv'
tb=(base/'tb_hgi_coll_static_vmwrite.sv').read_text().replace('parameter integer MUT=0;',"parameter integer MUT=0;\n parameter integer ROOT_DROP=0;\n wire[15:0] roots={16{clk}} & ~(ROOT_DROP==0 ? 16'd0 : (16'd1 << (ROOT_DROP-1)));")
tb=tb.replace('ot_hgi_coll_static_vmwrite #','ot_hgi_coll_static_vmwrite_roots_v6_physical #').replace('.clk(clk),','.clk_rgx_data0(roots[0]),.clk_rgx_data1(roots[1]),.clk_rgx_data2(roots[2]),.clk_rgx_data3(roots[3]),.clk_rgx_ctrl(roots[4]),.clk_tkw(roots[5]),.clk_meta(roots[6]),.clk_body(roots[7]),.clk_bank0(roots[8]),.clk_bank1(roots[9]),.clk_bank2(roots[10]),.clk_bank3(roots[11]),.clk_bank4(roots[12]),.clk_bank5(roots[13]),.clk_bank6(roots[14]),.clk_bank7(roots[15]),')
tb=tb.replace('.rgx_data(rd)',','.join(f'.rgx_data{k}(rd[{k*512}+:512])' for k in range(4))).replace('.kq(kq)',','.join(f'.kq{k}(kq[{k*281}+:281])' for k in range(8)))
tbp=a.out/'tb_production.sv';tbp.write_text(tb);rows=[]
def run(name,top,src,params=(),positive=True):
 sim=a.out/(name+'.vvp');b=subprocess.run(['iverilog','-g2012','-s',top,*params,'-o',str(sim),*map(str,src)],capture_output=True,text=True);(a.out/(name+'.build.log')).write_text(b.stdout+b.stderr)
 if b.returncode:raise RuntimeError(name+' build failed: '+b.stderr[-2000:])
 r=subprocess.run(['vvp',str(sim)],capture_output=True,text=True,timeout=180);(a.out/(name+'.log')).write_text(r.stdout+r.stderr)
 ok=(r.returncode==0 and ' PASS ' in r.stdout) if positive else (r.returncode==1 and 'FATAL:' in r.stdout)
 rows.append(dict(name=name,expected_pass=positive,exit_code=r.returncode,gate_pass=ok));print(name,'PASS' if ok else 'FAIL',r.stdout.strip().splitlines()[-1] if r.stdout.strip() else '',flush=True)
 if not ok:raise RuntimeError(name+' unexpected outcome')
run('sameedge_miter','tb_vmwrite_v6_equiv',[v4,v6,physical,tools/'tb_vmwrite_v6_equiv.sv'])
run('production_exact','tb_hgi_coll_static_vmwrite',[v6,physical,tbp])
run('clock_mapping','tb_vmwrite_v6_mapping',[v6,physical,tools/'tb_vmwrite_v6_mapping.sv'])
run('clock_mapping_mutant','tb_vmwrite_v6_mapping',[v6,physical,tools/'tb_vmwrite_v6_mapping.sv'],['-Ptb_vmwrite_v6_mapping.MAP_MUT=1'],False)
for m in (1,2,3,4,5):run('semantic_mutant_'+str(m),'tb_hgi_coll_static_vmwrite',[v6,physical,tbp],[f'-Ptb_hgi_coll_static_vmwrite.MUT={m}'],False)
for k in range(1,17):run('clock_drop_'+str(k),'tb_hgi_coll_static_vmwrite',[v6,physical,tbp],[f'-Ptb_hgi_coll_static_vmwrite.ROOT_DROP={k}'],False)
(a.out/'summary.json').write_text(json.dumps(dict(scope='v6 source-only same-edge equivalence and per-root logical ownership; physical phi-R/grants/native remain OPEN',clock_roots=16,source_sha256={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (v4,v6,physical,base/'tb_hgi_coll_static_vmwrite.sv',tools/'tb_vmwrite_v6_equiv.sv',tools/'tb_vmwrite_v6_mapping.sv',Path(__file__))},results=rows),indent=2)+'\n')
