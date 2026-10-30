from pathlib import Path
import subprocess,json
root=Path('/srv/opentallas-scratch/claude/wt/codex-ectl-pc-2249')
r=root/'results/codex_ectl_pc_2249/pc_count';r.mkdir(exist_ok=True)
src=(root/'rtl/qwen_sys/static_kv_20261014/ot_qkd_static_kv_timing.sv').read_text()
start=src.index('          if (SQ_COUNT_PARALLEL != 0) begin');end=src.index('          if (s_go) sq_rp',start)
actual=src[start:end]
for mode in [0,1,2]:
 body=actual
 if mode==2: body=body.replace("2'b01: sq_n <= sq_n - 1'b1;","2'b01: sq_n <= sq_n + 1'b1;")
 text='module count(input clk,input [2:0] q,input s_v,s_r,s_go,output reg[2:0] sq_n); parameter SQ_COUNT_PARALLEL='+str(min(mode,1))+'; always @* begin sq_n=q;\n'+body.replace('sq_n <=','sq_n =').replace('sq_n +','q +').replace('sq_n -','q -').replace('sq_n = sq_n;','sq_n = q;')+'end endmodule\n'
 (r/f'count{mode}.v').write_text(text)
# Exhaustively compare actual extracted Verilog, all 8 count states and sv/sr/go (64 rows).
tb='module tb; reg clk=0; reg[2:0]q; reg sv,sr,sg; wire[2:0]a,b,m; integer i,diff=0; count0 a0(clk,q,sv,sr,sg,a);count1 a1(clk,q,sv,sr,sg,b);count2 a2(clk,q,sv,sr,sg,m); initial begin for(i=0;i<64;i=i+1)begin {q,sv,sr,sg}=i;#1;if(a!==b)$fatal(1,"mismatch %d",i);if(a!==m)diff=diff+1;end if(diff==0)$fatal(1,"mutant uncaught");$display("PASS64 actual-extracted fullstate transitions; mutant caught %d",diff);end endmodule'
(r/'tb.v').write_text(tb)
for i in range(3):
 p=r/f'count{i}.v';p.write_text(p.read_text().replace('module count(',f'module count{i}('))
subprocess.run(['iverilog','-g2012','-s','tb','-o',str(r/'test'),*[str(r/f'count{i}.v')for i in range(3)],str(r/'tb.v')],check=True)
p=subprocess.run(['vvp',str(r/'test')],text=True,capture_output=True,check=True);print(p.stdout);(r/'exhaustive.txt').write_text(p.stdout)
