from pathlib import Path
import argparse, json, re, subprocess, os
p=argparse.ArgumentParser();p.add_argument('--prototype',type=Path,required=True);p.add_argument('--loader',type=Path,required=True);p.add_argument('--macro',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
a.out.mkdir(exist_ok=False)
text=(a.prototype/'rtl/s81p_col_h10_r0_p1__t1.sv').read_text()
decl=re.search(r'parameter\s+(P_u_c0_0_INSTANCE)\s*=\s*"[^"]*"',text)
assert decl and '.INSTANCE('+decl[1]+')' in text
mapping=json.load(open(a.loader/'loader_manifest.json'))['mapping']
selected=[mapping[0],next(x for x in mapping if x['image_sha256']!=mapping[0]['image_sha256'])]
for i,s in enumerate(selected):
 rows=[int(w,16) for w in (a.loader/s['loader_file']).read_text().split()]
 assert len(rows)==512
 words=[sum(((rows[addr//8]>>(b*8+addr%8))&1)<<b for b in range(72)) for addr in range(4096)]
 (a.out/f'expect{i}.memh').write_text(''.join(f'{w:018x}\n' for w in words))
first,second=[json.dumps(x['original_cell']) for x in selected]
param=decl[1]
tb=f'''`timescale 1ns/1ps
module selected_image #({decl[0]}) (input wire clk,input wire[11:0] a,output wire[71:0] q);
 ot_rom_4096x72_m8 #(.INSTANCE({param}),.VIAMAP("")) u_rom(.clk(clk),.ce_in(1'b1),.addr_in(a),.rd_out(q));
endmodule
module tb;
 parameter integer MUT=0;
 reg clk=0;always #5 clk=~clk;
 reg[11:0] a=0;wire[71:0] q0,q1;reg[71:0] e0[0:4095],e1[0:4095];integer i,errors=0;
 selected_image #(.{param}({first})) d0(clk,a,q0);
 selected_image #(.{param}(MUT?{first}:{second})) d1(clk,a,q1);
 initial begin
  $readmemh("expect0.memh",e0);$readmemh("expect1.memh",e1);
  for(i=0;i<4096;i=i+1)begin @(negedge clk);a=i;@(posedge clk);#1;
   if(q0!==e0[i])errors=errors+1;if(q1!==e1[i])errors=errors+1;
  end
  $display("ROM_IDENTITY checked=8192 mismatches=%0d",errors);$finish;
 end
endmodule
'''
(a.out/'tb.sv').write_text(tb)
results=[]
env=dict(os.environ);env['PATH']=str(Path.home()/'.local/opentallas-tools/bin')+':'+env['PATH']
for mut in (0,1):
 with (a.out/f'build{mut}.log').open('w') as log:
  subprocess.run(['verilator','--binary','--timing','--top-module','tb','-Wno-fatal',f'-GMUT={mut}','--Mdir',f'obj{mut}','-j','2',str(a.out/'tb.sv'),str(a.macro)],cwd=a.out,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
 run=subprocess.run([str(a.out/f'obj{mut}/Vtb'),'+OT_ROM_DIR='+str(a.loader)],cwd=a.out,text=True,capture_output=True)
 (a.out/f'run{mut}.log').write_text(run.stdout+run.stderr)
 match=re.search(r'ROM_IDENTITY checked=8192 mismatches=(\d+)',run.stdout)
 assert run.returncode==0 and match,run.stdout+run.stderr
 results.append(dict(mutant=mut,mismatches=int(match[1]),checked=8192))
assert results[0]['mismatches']==0 and results[1]['mismatches']>0,results
rec=dict(verdict='PASS',scope='Actual emitted parameter declaration and real ROM primitive image selection only; no carve/token claim',selected=selected,results=results)
(a.out/'result.json').write_text(json.dumps(rec,indent=1)+'\n');print(json.dumps(rec))
