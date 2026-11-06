from pathlib import Path
import re,hashlib
src=Path('root.sv').read_text()
assert hashlib.sha256(src.encode()).hexdigest()=='2214efc605dac6ac80efbb29fe03a38486a272fde801af7e27ad1f48d27c62ff'
s=src[:src.index('endmodule')]
inputs=re.findall(r'^  input (?:\[[^\n]+?\] )?(\\\S+|\w+)\s*;',s,re.M)
s='module phase_actual('+','.join(n+' ' for n in inputs)+', proof_bad);'+s[s.index(');')+2:]
s=re.sub(r'^  output[^\n]+\n','',s,flags=re.M)
s=s.replace('(* keep *)','')
monitor=r'''
output proof_bad;
wire proof_accept = _18340_;
wire proof_precompute = \u.cfg_pipe[0] ;
wire proof_capture = \u.capture ;
wire [7:0] proof_gb = _60234_;
wire [7:0] proof_pf = _60236_[7:0];
reg proof_ready;
reg [7:0] proof_saved_gb,proof_saved_pf;
always @(posedge clk or negedge rst_n)
 if(!rst_n) proof_ready <= 0;
 else if(proof_accept) proof_ready <= 0;
 else if(proof_precompute) proof_ready <= 1;
always @(posedge clk) if(proof_precompute) begin
 proof_saved_gb <= proof_gb;
 proof_saved_pf <= proof_pf;
end
assign proof_bad = rst_n && proof_capture && (!proof_ready || proof_saved_gb!=proof_gb || proof_saved_pf!=proof_pf);
endmodule
'''
strong=monitor.replace('output proof_bad;', 'output proof_bad;\noutput proof_invariant_bad;').replace('assign proof_bad =', 'assign proof_invariant_bad = \\u.busy  && ((!proof_ready && (!proof_precompute || _60260_!=0)) || (proof_ready && (proof_saved_gb!=proof_gb || proof_saved_pf!=proof_pf)));\nassign proof_bad =')
Path('phase_induct.sv').write_text((s.replace(', proof_bad);', ', proof_bad, proof_invariant_bad);'))+strong)
Path('phase_actual.sv').write_text(s+monitor)
Path('phase_mutant.sv').write_text(s+monitor.replace('else if(proof_precompute) proof_ready <= 1;','else if(proof_precompute) proof_ready <= 0;'))
