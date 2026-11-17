"""Production-width minimum depth mechanism; default and reset-aware one-cycle relation, plus bypass control."""
import sys,subprocess,tempfile,shutil,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import frame_colrelay_h9p2 as H
HERE=Path(__file__).resolve().parent

def fixture():
 ports=['input clk,rs','input [1103:0] din','output [282:0] lw6','output [265:0] lw7','output [14:0] lw8','output [1:0] so']+[f'output [275:0] xo{i}' for i in range(4)]
 rows=['    ot_pl_seam_w_plr #(.W(283), .CHUNK_BITS(24), .RSREG(1)) u_lpl_6_w (.ck(clk), .rsi({12{rs}}), .rse(rs), .ir(din[282:0]), .q(lw6));','    ot_pl_seam_w_plr #(.W(15), .CHUNK_BITS(24), .RSREG(0)) u_lpl_8_w (.ck(clk), .rsi(rs), .rse(rs), .ir(din[14:0]), .q(lw8));','    dsfd_rly_2_NW u_y_so_1_0 (.ck(clk), .rs(rs), .i(din[1:0]), .o(so));']
 rows.append('    ot_pl_seam_w_plr #(.W(266), .CHUNK_BITS(24), .RSREG(1)) u_lpl_7_w (.ck(clk), .rsi({12{rs}}), .rse(rs), .ir(din[265:0]), .q(lw7));')
 for i in range(4):
  rows += [f'    wire [275:0] x{i};',f'    ot_s81_rly #(.W(276), .RSREG(1)) u_y_xo{i}_0 (.ck(clk), .rs(rs), .i(din[{i*276}+:276]), .o(x{i}));',f'    ot_s81_rly #(.W(276), .RSREG(1)) u_y_xo{i}_1 (.ck(clk), .rs(rs), .i(x{i}), .o(xo{i}));']
 return 'module col_h9_l4_lp_r0 #(parameter integer MUT = 0, parameter integer DUMMY=0)(\n'+',\n'.join(ports)+'\n);\n'+'\n'.join(rows)+'\nendmodule\n'

def run(out):
 src=fixture();new,ledger=H.transform(src);assert ledger['added_data_ff']==1670
 obs=[('lw6',283),('lw7',266),('lw8',15),('so',2)]+[(f'xo{i}',276) for i in range(4)]
 tb=['module tb; reg clk=0;always #5 clk=~clk;reg rs=0;reg[1103:0]din=0;integer c,k;']
 for n,w in obs:tb += [f'wire[{w-1}:0] b_{n},n_{n},z_{n};reg[{w-1}:0] prev_{n}=0;']
 for mod,pfx,param in [('base','b',''),('candidate','n','#(.COLRELAY_H9P2(1))'),('candidate','z','#(.COLRELAY_H9P2(0))')]:
  tb.append(f'{mod} {param} u_{pfx}(.clk(clk),.rs(rs),.din(din),'+','.join(f'.{n}({pfx}_{n})' for n,w in obs)+');')
 tb.append('initial begin for(c=0;c<4000;c=c+1)begin @(negedge clk);rs=(c%137>3);for(k=0;k<34;k=k+1)din[k*32+:32]=$random;din[1103:1088]=$random;@(posedge clk);#2;')
 for n,w in obs:tb.append(f'if(!rs)prev_{n}=0;if(z_{n}!==b_{n})$fatal(1,"DEFAULT {n} %0d",c);if(n_{n}!==prev_{n})$fatal(1,"DELAY {n} %0d",c);prev_{n}=b_{n};')
 tb.append('end $display("H9P2_COMPONENT_PASS4000 resetbursts30");$finish;end endmodule')
 support='module dsfd_rly_2_NW(input ck,rs,input[1:0]i,output[1:0]o);ot_s81_rly #(.W(2),.RSREG(1)) u(.*);endmodule\n'
 results=[]
 for sliced in [False,True]:
  for mutant in [False,True]:
   candidate=new
   if mutant:
    anchor='COLRELAY_H9P2 ? h9p2_y_xo0_1_extra : h9p2_y_xo0_1_raw'
    assert anchor in candidate
    candidate=candidate.replace(anchor,'h9p2_y_xo0_1_raw',1)
   f=out/f'tb_s{int(sliced)}m{int(mutant)}.sv';f.write_text(src.replace('module col_h9_l4_lp_r0','module base',1)+candidate.replace('module col_h9_l4_lp_r0','module candidate',1)+support+'\n'.join(tb))
   exe=f.with_suffix('.sim');args=['iverilog','-g2012','-s','tb','-o',str(exe)]
   if sliced:args+=['-DOT_S81_RLY_RSSLICE']
   args += [str(HERE.parents[1]/'rtl/dsrom_sys/s81_glue/ot_s81_rly.sv'),str(HERE.parents[1]/'rtl/common/landed_parent/ot_pl_seam.sv'),str(f)]
   r=subprocess.run(args,capture_output=True,text=True);assert r.returncode==0,r.stderr
   r=subprocess.run(['vvp',str(exe)],capture_output=True,text=True)
   (f.with_suffix('.log')).write_text(r.stdout+r.stderr)
   assert (r.returncode!=0) if mutant else (r.returncode==0),r.stdout+r.stderr
   results.append(dict(sliced=sliced,mutant=mutant,returncode=r.returncode,output=r.stdout.strip()))
 return dict(status='COMPONENT_ONLY_PASS_NOT_FRAME_QUALIFIED',edges_per_case=4000,cases=results,ledger=ledger)

def test_production_width_mechanism(tmp_path):
 run(tmp_path)


if __name__=='__main__':
 out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True);r=run(out);(out/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
