#!/usr/bin/env python3
"""Exact source cuts, retaining real compare/sum capture coupling and output edge."""
import argparse,hashlib,json,re,subprocess,time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('out',type=Path);args=p.parse_args()
r=Path(__file__).resolve().parent;out=args.out.resolve();out.mkdir(parents=True,exist_ok=True)
def cut(text,mode):
 if mode==0:
  a=text.index('    reg [15:0]      gea;');s='    always @(posedge clk) begin g_out <= ga; acc_a <= acca; qa <= q4; end';b=text.index(s,a)+len(s)
  return text[a:b]
 a=text.index('    reg [15:0]      geb;');s='        res_b <= {g_b4, bb}; res_ok <= okb; res_above <= aboveb;';b=text.index(s,a)
 return text[a:b].rsplit('    always @(posedge clk) begin',1)[0]+'    always @(posedge clk) begin\n'+s+'\n    end\n'
def wrap(body,name,mode):
 head=f'''module {name} #(parameter integer QW=11)(input wire clk,input wire [335:0] u,input wire [QW-1:0] q,input wire [20:0] acc,input wire [3:0] tag,output wire [3:0] sel,output wire [20:0] above,output wire [QW-1:0] quota,output wire [3:0] date,output wire valid);
localparam integer XW=21;
integer i,ia,ib;
'''
 if mode==0:
  head+='wire [335:0] s3_r=u; wire [QW-1:0] q3=q; reg [3:0] g_out;\n'
  tail='assign sel=g_out;assign above=acc_a;assign quota=qa;assign date=0;assign valid=0;\n'
 else:
  head+='wire [335:0] u3_r=u;wire [QW-1:0] q_b3=q;wire [20:0] acc_b3=acc;wire [3:0] g_b3=tag;reg [7:0] res_b;reg [20:0] res_above;reg res_ok;\n'
  tail='assign sel=res_b[3:0];assign above=res_above;assign quota=0;assign date=res_b[7:4];assign valid=res_ok;\n'
 return head+body+'\n'+tail+'endmodule\n'
sources={n:(r/'source'/f'{n}.sv').read_text() for n in ['original','ab_r1','ab_r2']}
results=[];cuts={};t=time.time()
for mode in [0,1]:
 bodies=[cut(sources[n],mode) for n in ['original','ab_r1','ab_r2']]
 key='A' if mode==0 else 'B';cuts[key]={n:hashlib.sha256(b.encode()).hexdigest() for n,b in zip(sources,bodies)}
 mut=bodies[-1];start=mut.index('// BEGIN registered'+(' A' if mode==0 else '')+' selector');end=mut.index('// END registered'+(' A' if mode==0 else '')+' selector')
 nx,old=('gea_nx','gea') if mode==0 else ('geb_nx','geb')
 mut=mut[:start]+mut[start:end].replace(nx,old)+mut[end:]
 sv=out/f'cut_{key}.sv';sv.write_text('`timescale 1ps/1fs\n'+''.join(wrap(b,n,mode) for b,n in zip(bodies+[mut],['cut_ref','cut_r1','cut_r2','cut_mut'])))
 for qw in [11,21]:
  exe=out/f'cut_{key}_{qw}.vvp';cl=out/f'compile_{key}_{qw}.log';lg=out/f'run_{key}_{qw}.log'
  with cl.open('w') as f:subprocess.run(['iverilog','-g2012','-s','cut_tb',f'-Pcut_tb.QW={qw}',f'-Pcut_tb.MODE={mode}','-o',str(exe),str(sv),str(r/'cut_tb.sv')],stdout=f,stderr=subprocess.STDOUT,check=True)
  with lg.open('w') as f:proc=subprocess.run(['vvp',str(exe)],stdout=f,stderr=subprocess.STDOUT)
  log=lg.read_text();print(log,flush=True);m=re.search(r'CUT_RESULT mode=(\d+) qw=(\d+) xw=21 edges=(\d+) checks=(\d+) errors=(\d+) masks=(\d+) mutant_errors=(\d+) no_qualify=(\d+)',log)
  d={'mode':key,'QW':qw,'XW':21,'exit':proc.returncode,'pass_gate':proc.returncode==0 and 'BKSEL_SELECTOR_CUT_PASS' in log}
  if m:d.update(zip(['edges','checks','errors','masks','mutant_errors','no_qualify'],map(int,m.groups()[2:])))
  results.append(d)
rec={'schema':'opentallas.s81.actual_selector_cut.v1','status':'PASS' if all(x['pass_gate'] for x in results) else 'FAIL','scope':'Actual production ot_s81ph_sel_su_pipe A+B selector cuts, not full-SU or whole-kit equivalence; normal fresh mapped whole-kit LEC remains required','Q':4,'CB':11,'XW':21,'QW':[11,21],'clock_ps':833,'source_cut_sha256':cuts,'source_sha256':{str(p.relative_to(r)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [r/'source/original.sv',r/'source/ab_r1.sv',r/'source/ab_r2.sv',r/'cut_tb.sv',r/'run_cut.py']},'results':results,'mutants':'Only selector-mask register inputs changed from compare-NEXT to stale gea/geb; capture and output stages unchanged','seconds':round(time.time()-t,3),'adopted':False}
(out/'receipt.json').write_text(json.dumps(rec,indent=2)+'\n');raise SystemExit(0 if rec['status']=='PASS' else 1)
