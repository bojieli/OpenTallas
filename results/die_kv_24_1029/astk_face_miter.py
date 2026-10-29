import json,sys
from pathlib import Path
D=Path(sys.argv[1]);m=json.load(open(D/'sources.json'));decl=m['decl'];ins={n:v for n,v in decl.items() if v[0]=='input'};outs={n:v for n,v in decl.items() if v[0]=='output'}
s=['`timescale 1ns/1ps','module tb; reg clk=0; always #0.5 clk=~clk; integer seed=19; integer mism=0, edges=0, tcchanges=0;']
for n,(dr,hi,lo) in ins.items():
 if n=='ck':s.append('wire [0:0] ck={clk};')
 else:s.append(f'reg [{hi}:0] {n}=0;')
for n,(dr,hi,lo) in outs.items():s.append(f'wire [{hi}:0] o_{n},n_{n};')
b='g_phys_fault_u_fault__b';s.append(f'reg [0:0] bprev=0; always @(posedge clk) if (!rst_n) bprev<=0; else bprev<={b};')
for suffix,typ in [('o','kv3_astk_ref'),('n','kv3_astk')]:
 args=[f'.{n}({"bprev" if suffix=="o" and n==b else n})' for n in ins]+[f'.{n}({suffix}_{n})' for n in outs]
 s.append(f'{typ} u_{suffix}('+','.join(args)+');')
vo='{'+','.join('o_'+n for n in outs)+'}';vn='{'+','.join('n_'+n for n in outs)+'}'
s.append(f'always @(negedge clk) if(rst_n) begin edges=edges+1; if({vo} !== {vn}) begin mism=mism+1; if(mism<5)$display("DIFF edge=%0d",edges);end end')
s.append('initial begin for(integer c=0;c<4;c=c+1)begin rst_n=0; strap_corner=c; repeat(12)@(negedge clk);rst_n=1; for(integer k=0;k<1200;k=k+1)begin')
for n,(dr,hi,lo) in ins.items():
 if n in ['ck','rst_n','strap_corner']:continue
 if n==b:s.append(f'{n}=(k>100 && (k%71)==0);')
 elif n.endswith('__cal'):s.append(f'{n}=32\'h0008000f;')
 else:
  for pos in range(0,hi+1,32):s.append(f'{n}[{pos} +: {min(32,hi+1-pos)}]=$random(seed);')
 if n.endswith('__aq'):s.append(f'{n}[0]=(k%180)==0; {n}[21]=0;')
s.append('@(negedge clk); end end $display("ASTK_FACE_MITER %s edges=%0d mismatches=%0d",mism==0?"PASS":"FAIL",edges,mism);$finish;end endmodule')
(D/'tb.sv').write_text('\n'.join(s)+'\n');(D/'files.f').write_text('\n'.join(m['files']+[str(D/'kv3_astk_ref.sv'),str(D/'kv3_astk.sv'),str(D/'tb.sv')])+'\n')
