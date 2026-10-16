#!/usr/bin/env python3
"""All four literal-SID masters: exact v4 miters, production and meaningful negatives."""
import argparse,hashlib,json,subprocess
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('out',type=Path);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
root=Path(__file__).resolve().parents[2];base=root/'rtl/hbm_accel/generic/collective/p2p';tools=root/'tools/hbm_coll_static'
v4=base/'ot_hgi_coll_static_vmwrite.sv';v6=base/'ot_hgi_coll_static_vmwrite_roots_v6.sv';physical=base/'ot_hgi_coll_static_vmwrite_roots_v7_sid.sv'
rows=[]
def run(name,top,src,params=(),positive=True):
 sim=a.out/(name+'.vvp');b=subprocess.run(['iverilog','-g2012','-s',top,*params,'-o',str(sim),*map(str,src)],capture_output=True,text=True);(a.out/(name+'.build.log')).write_text(b.stdout+b.stderr)
 if b.returncode:raise RuntimeError(name+' build failed: '+b.stderr[-2000:])
 r=subprocess.run(['vvp',str(sim)],capture_output=True,text=True,timeout=180);(a.out/(name+'.log')).write_text(r.stdout+r.stderr)
 ok=(r.returncode==0 and ' PASS ' in r.stdout) if positive else (r.returncode==1 and 'FATAL:' in r.stdout)
 rows.append(dict(name=name,expected_pass=positive,exit_code=r.returncode,gate_pass=ok));print(name,'PASS' if ok else 'FAIL',r.stdout.strip(),flush=True)
 if not ok:raise RuntimeError(name+' unexpected outcome')
for sid in range(4):
 master='ot_hgi_coll_static_vmwrite_roots_v7_sid'+str(sid)
 tb=(base/'tb_hgi_coll_static_vmwrite.sv').read_text().replace('parameter integer MUT=0;',"parameter integer MUT=0;\n parameter integer ROOT_DROP=0;\n wire[15:0] roots={16{clk}} & ~(ROOT_DROP==0 ? 16'd0 : (16'd1 << (ROOT_DROP-1)));")
 tb=tb.replace('ot_hgi_coll_static_vmwrite #',master+' #').replace('.clk(clk),','.clk_rgx_data0(roots[0]),.clk_rgx_data1(roots[1]),.clk_rgx_data2(roots[2]),.clk_rgx_data3(roots[3]),.clk_rgx_ctrl(roots[4]),.clk_tkw(roots[5]),.clk_meta(roots[6]),.clk_body(roots[7]),.clk_bank0(roots[8]),.clk_bank1(roots[9]),.clk_bank2(roots[10]),.clk_bank3(roots[11]),.clk_bank4(roots[12]),.clk_bank5(roots[13]),.clk_bank6(roots[14]),.clk_bank7(roots[15]),').replace('.sid(sid),','')
 tb=tb.replace('.rgx_data(rd)',','.join(f'.rgx_data{k}(rd[{k*512}+:512])' for k in range(4))).replace('.kq(kq)',','.join(f'.kq{k}(kq[{k*281}+:281])' for k in range(8)))
 tb=tb.replace("if(mode==4) sec=sec | 16'h2000;",f"sec=sec | 16'd{sid*8192};\n                if(mode==4) sec=(sec & 16'h9fff) | 16'd{((sid+1)%4)*8192};")
 tb=tb.replace("if(mode==5) sec=sec | 16'h8000;","if(mode==5) sec=(sec & 16'h1fff) | 16'h8000;")
 tb=tb.replace('sid=2;',f'sid={sid};').replace('sid=0;',f'sid={sid};')
 tbp=a.out/f'tb_production_sid{sid}.sv';tbp.write_text(tb)
 miter=(tools/'tb_vmwrite_v6_equiv.sv').read_text().replace('ot_hgi_coll_static_vmwrite_roots_v6_physical dut',master+' dut').replace('.rst_n(rst_n),.sid(sid),.rgx_v(rgx_v)', '.rst_n(rst_n),.rgx_v(rgx_v)',1).replace('sid=$random;',f'sid={sid};').replace('sid=0;',f'sid={sid};')
 mp=a.out/f'tb_miter_sid{sid}.sv';mp.write_text(miter)
 mapping=(tools/'tb_vmwrite_v6_mapping.sv').read_text().replace('ot_hgi_coll_static_vmwrite_roots_v6_physical dut',master+' dut').replace('.sid(sid),','').replace('sid=3;',f'sid={sid};')
 cp=a.out/f'tb_mapping_sid{sid}.sv';cp.write_text(mapping)
 prefix=f'sid{sid}_'
 run(prefix+'sameedge_miter','tb_vmwrite_v6_equiv',[v4,v6,physical,mp])
 run(prefix+'production_exact','tb_hgi_coll_static_vmwrite',[v6,physical,tbp])
 run(prefix+'clock_mapping','tb_vmwrite_v6_mapping',[v6,physical,cp])
 run(prefix+'clock_mapping_mutant','tb_vmwrite_v6_mapping',[v6,physical,cp],['-Ptb_vmwrite_v6_mapping.MAP_MUT=1'],False)
 wrong=a.out/f'tb_wrong_sid{sid}.sv';wrong.write_text(tb.replace(master,'ot_hgi_coll_static_vmwrite_roots_v7_sid'+str((sid+1)%4)))
 run(prefix+'wrong_literal_binding_mutant','tb_hgi_coll_static_vmwrite',[v6,physical,wrong],(),False)
 for m in (1,2,3,4,5):run(prefix+'semantic_mutant_'+str(m),'tb_hgi_coll_static_vmwrite',[v6,physical,tbp],[f'-Ptb_hgi_coll_static_vmwrite.MUT={m}'],False)
 for k in range(1,17):run(prefix+'clock_drop_'+str(k),'tb_hgi_coll_static_vmwrite',[v6,physical,tbp],[f'-Ptb_hgi_coll_static_vmwrite.ROOT_DROP={k}'],False)
(a.out/'summary.json').write_text(json.dumps(dict(scope='Four configured-SID sources only; no die adoption or routed/native qualification',clock_roots=16,configured_sid=[0,1,2,3],source_sha256={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (v4,v6,physical,base/'tb_hgi_coll_static_vmwrite.sv',tools/'tb_vmwrite_v6_equiv.sv',tools/'tb_vmwrite_v6_mapping.sv',Path(__file__))},results=rows),indent=2)+'\n')
