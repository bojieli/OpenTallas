from pathlib import Path
import re,json,subprocess,hashlib
r=Path(__file__).resolve().parent;s=(r/'native_bound.sv').read_text();g=json.loads((r/'native_reset_source_graph.json').read_text());lines=re.findall(r'^\s*(ot_dp_rrelay\s+u_rrl_\d+\s*\(.*?\);)',s,re.M)
wire=set(re.findall(r'\.[dq]\((\w+)\)', '\n'.join(lines)))-{'rst_root_n'}
base='module ot_dp_rrelay(input clk,d,output reg q);always @(posedge clk) q<=d; endmodule\nmodule m(input clk,rst_root_n,output same,output qualified);\nwire '+','.join(sorted(wire))+';\n'+'\n'.join(lines)+'\nreg[6:0] delivered=0; always @(posedge clk) delivered<={delivered[5:0],1\'b1};\nassign qualified=delivered[6];\n'
receipts={}
for mode in ['native','wrong_depth','wrong_polarity']:
 comps=[]
 for q in sorted(g):
  other=q
  if q=='rst_n_t5' and mode=='wrong_depth':other=g[q]['path'][0]['d']
  if q=='rst_n_t5' and mode=='wrong_polarity':other='~'+q
  comps.append('(rst_n_t14 == '+other+')')
 text=base+'assign same='+' && '.join(comps)+';\nalways @* if(qualified) assert(same);\nendmodule\n'
 sv=r/(mode+'_reset.sv');sv.write_text(text)
 cmd=['yosys','-Q','-T','-p',f'read_verilog -formal -sv {sv}; prep -top m -flatten; sat -seq 20 -prove-asserts -verify -show-inputs -show same,qualified -dump_json {r/(mode+"_counterexample.json")}']
 p=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True);(r/(mode+'_reset.log')).write_text(p.stdout)
 receipts[mode]=dict(returncode=p.returncode,expected='PASS' if mode=='native' else 'CAUGHT',observed='PASS' if p.returncode==0 else 'CAUGHT',source_sha256=hashlib.sha256(sv.read_bytes()).hexdigest())
 assert (p.returncode==0)==(mode=='native'),receipts
print(json.dumps(receipts,indent=2));(r/'reset_source_proof.json').write_text(json.dumps(dict(native_bound_sha256=hashlib.sha256(s.encode()).hexdigest(),terminal_count=51,relay_count=180,depth_after_delivered_root_edges=7,root_input='rst_root_n unconstrained each formal cycle, no selected assertion window',pre7='All native flop initial states unconstrained. qualified is an observation flag only; raw same output remains unmasked. No pre7 equality or parent startup claim.',parent_boot_join='HELD',receipts=receipts),indent=2))
