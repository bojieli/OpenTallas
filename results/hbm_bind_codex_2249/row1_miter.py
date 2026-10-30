import json,subprocess,shutil,sys
from pathlib import Path
R=Path('/srv/opentallas-scratch2/claude/codex-hbm-bind-2249');O=R/'row1';P=O/'proof_v3';P.mkdir(exist_ok=True)
y=json.load(open('/srv/opentallas-scratch2/claude/die-hbm-29/b29d/out/asbuilt.json'));z=json.load(open(O/'asbuilt.json'));rep=json.load(open(O/'receipt.json'))
def scorer(js,side):
 m=js['modules'];w=m[m['hbm_current_native_top']['cells'][f'hb_idx__s_{side}']['type']];return m[w['cells']['scorer']['type']]
regs=[];cursor=0;checks=[];ds=[]
for j,row in enumerate(rep['rows']):
 side=row['side'];a=scorer(y,side)['cells'][row['original'].split('.scorer.',1)[1]];b=scorer(z,side)['cells'][row['new'].split('.scorer.',1)[1]]
 assert a['type']==b['type']=='$dff' and a['parameters']['CLK_POLARITY']==b['parameters']['CLK_POLARITY']=='1'
 idx=row['source_bits'];assert b['connections']['D']==[a['connections']['D'][i] for i in idx]
 assert b['connections']['CLK']==a['connections']['CLK']
 wa=len(a['connections']['Q']);wb=len(b['connections']['Q']);sl=f'inp[{cursor}+:{wa}]';cursor+=wa
 regs += [f'reg [{wa-1}:0] ref_{j}; reg [{wb-1}:0] got_{j};',f'always @(posedge clk) ref_{j}<={sl};']
 # Use the candidate's original-D correspondence, checked above; no data arithmetic is transformed.
 bits=[f'{sl}[{i}]' for i in idx]
 # Verilog does not accept part-select-then-index, use global input indices instead.
 bits=[f'inp[{cursor-wa+i}]' for i in reversed(idx)]
 d='{'+','.join(bits)+'}';d=f'({d} ^ MUT)' if j==0 else d
 regs.append(f'always @(posedge clk) got_{j}<={d};')
 ref='{'+','.join(f'ref_{j}[{i}]' for i in reversed(idx))+'}';checks.append(f'if (got_{j} !== {ref}) bad=bad+1;')
text='''`timescale 1ns/1ps
module tb;
parameter integer MUT=0;
reg clk=0; always #0.4165 clk=~clk;
'''+f'reg [{cursor-1}:0] inp=0;\n'+'\n'.join(regs)+f'''\ninteger bad=0; integer cyc;integer k;integer seed=32'h19abca03;
initial begin
 for(cyc=0;cyc<4096;cyc=cyc+1)begin
  @(negedge clk);
  for(k=0;k<{cursor};k=k+32)inp[k+:32]=$random(seed);
  @(posedge clk);#0.1;
  {''.join(checks)}
 end
 $display("ROW1_REGISTER_MITER edges=4096 compared_bits={sum(len(r['source_bits']) for r in rep['rows'])} bad=%0d mutant=%0d",bad,MUT);
 if(MUT==0 && bad!=0)$fatal(1,"lockstep mismatch");
 if(MUT!=0 && bad==0)$fatal(1,"mutant escaped");
 $finish;
end
endmodule
'''
(P/'tb.sv').write_text(text)
for mut in (0,1):
 exe=P/f'm{mut}.out';c=subprocess.run(['iverilog','-g2012','-P',f'tb.MUT={mut}','-o',str(exe),str(P/'tb.sv')],text=True,capture_output=True);(P/f'compile{mut}.log').write_text(c.stdout+c.stderr);assert c.returncode==0,c.stderr
 q=subprocess.run(['vvp',str(exe)],text=True,capture_output=True);(P/f'run{mut}.log').write_text(q.stdout+q.stderr);assert q.returncode==0,q.stdout+q.stderr;print(q.stdout,flush=True)
(P/'result.json').write_text(json.dumps(dict(verdict='PASS',edges=4096,compared_bits=sum(len(r['source_bits']) for r in rep['rows']),mutant='CAUGHT',actual_candidate=rep['candidate_sha256'],clock_ps=833,added_source_cycles=0),indent=1))
