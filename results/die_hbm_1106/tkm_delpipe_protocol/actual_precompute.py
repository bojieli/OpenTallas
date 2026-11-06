from pathlib import Path
import re,hashlib
s=Path('delpipe_v2.sv').read_text();assert hashlib.sha256(s.encode()).hexdigest()=='101a04825316ac0e65b53059f74a282a82abf572ac692dc48c033a3a64c91fc0'
s=s[:s.index('endmodule')];inputs=re.findall(r'^  input (?:\[[^\n]+?\] )?(\\\S+|\w+)\s*;',s,re.M)
s='module precompute_actual('+','.join(n+' ' for n in inputs)+',proof_bad);'+s[s.index(');')+2:];s=re.sub(r'^  output[^\n]+\n','',s,flags=re.M).replace('(* keep *)','')
monitor=r'''
output proof_bad;
reg proof_ready;
always @(posedge clk or negedge rst_n)
 if(!rst_n) proof_ready<=0;
 else if(_18340_) proof_ready<=0;
 else if(_60268_[0]) proof_ready<=1;
wire[7:0] expected_product=_60234_*_60236_[7:0];
assign proof_bad = ((\u.busy  || ot_del_cap_q) && ((!proof_ready && (!_60268_[0] || _60260_!=0)) || (proof_ready && (ot_del_gbpf_q!=expected_product)))) || ((\u.capture  || ot_del_cap_q)&&!proof_ready);
endmodule
'''
Path('precompute_actual.sv').write_text(s+monitor)
a='ot_del_gbpf_q <= _60234_ * _60236_[7:0];';assert s.count(a)==1
Path('precompute_mutant.sv').write_text(s.replace(a,"ot_del_gbpf_q <= (_60234_ * _60236_[7:0]) ^ 8'd1;")+monitor)
