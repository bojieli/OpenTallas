#!/usr/bin/env python3
"""Real generated native hd_tile numerical/40-FT partition vehicle; run via ot-run."""
import argparse,json,os,re,subprocess
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('native',type=Path);ap.add_argument('images',type=Path);ap.add_argument('out',type=Path);ap.add_argument('--jobs',type=int,default=8);a=ap.parse_args()
a.out.mkdir(parents=True,exist_ok=False)
refs=[]
renames=['ot_s81hd_elemA_cv','ot_s81hd_elemB_cv','ot_s81hd_bundle','ot_s81hd_tile','ot_s81hd_kreg','ot_s81hd_kregr']
for stem in ['ot_s81hd_elem_cv','ot_s81hd_bundle','ot_s81hd_tile']:
 src=Path('rtl/dsrom_sys/s81_head')/(stem+'.sv');text=src.read_text()
 for name in renames:text=re.sub(r'\b'+name+r'\b',name+'_reference',text)
 target=a.out/(stem+'_reference.sv');target.write_text(text);refs.append(str(target))
tb=Path('rtl/dsrom_sys/s81_head/test/tb_head_partition_token.sv').read_text().replace('ot_s81hd_tile #','ot_s81hd_tile_reference #')
ports=[]
for i in range(5):
 for j,n in enumerate(('ck0','ck1','mesh','rst')):
  k=4*i+j;ports.extend([f'.hci{i}_{n}_i(ft_drive[{k}])',f'.hci{i}_{n}_o(ft_out[{k}])'])
tb=tb.replace('integer mutant=0;',"integer mut_ft=0;reg[19:0]ft_pattern=20'h591c7;wire[19:0]ft_out;wire[19:0]ft_drive=ft_pattern^(mut_ft?20'd1:20'd0);integer ft_checks=0;\nalways@(negedge ck)begin if(cyc>2)begin if(ft_out!==ft_pattern)$fatal(1,\"HEAD_NATIVE_FT mismatch\");ft_checks+=20;end ft_pattern<={ft_pattern[18:0],ft_pattern[19]^ft_pattern[16]};end\ninteger mutant=0;")
tb=tb.replace('dut(.clk(ck),','dut('+','.join(ports)+',.clk(ck),')
tb=tb.replace(' if(!$value$plusargs("DIR=%s",dir))',' if($value$plusargs("MUT_FT=%d",mut_ft))begin end\n if(!$value$plusargs("DIR=%s",dir))')
tb=tb.replace('$display("HEAD_PARTITION_TOKEN PASS', '$display("HEAD_NATIVE_FT PASS checks%0d",ft_checks);\n $display("HEAD_PARTITION_TOKEN PASS')
(a.out/'tb_native.sv').write_text(tb)
cmd=['verilator','--binary','--timing','-O1','-Wno-fatal','-Wno-WIDTH','-Wno-TIMESCALEMOD','--top-module','tb_head_partition_token','-f',str(a.native/'native.f'),*refs,str(a.out/'tb_native.sv'),'--Mdir',str(a.out/'obj'),'--build-jobs',str(a.jobs),'-MAKEFLAGS','OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0']
with(a.out/'build.log').open('w')as f:subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
exe=a.out/'obj/Vtb_head_partition_token';results={}
for name,extra,expect in [('positive',[],'HEAD_PARTITION_TOKEN PASS'),('mut_row',['+MUT_ROW=1'],'HEAD_PARTITION lockstep mismatch'),('mut_ft',['+MUT_FT=1'],'HEAD_NATIVE_FT mismatch')]:
 with(a.out/(name+'.log')).open('w')as f:p=subprocess.run([str(exe),'+DIR='+str(a.images),'+OT_ROM_DIR='+str(a.images),*extra],stdout=f,stderr=subprocess.STDOUT)
 log=(a.out/(name+'.log')).read_text();ok=expect in log and ((p.returncode==0) if name=='positive' else p.returncode!=0);results[name]=dict(exit=p.returncode,pass_=ok)
 if not ok:raise SystemExit('native partition '+name+' failed')
result=dict(verdict='PASS_PARTITION_ONLY',rows=128,dims=5120,core_macros=5,infra_ports=40,added_cycles=0,results=results,whole_die=False,production_boot_authority=False)
(a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
