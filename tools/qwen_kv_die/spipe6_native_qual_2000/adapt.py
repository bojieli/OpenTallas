from pathlib import Path
import re,json,hashlib
lib=Path('libs/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib').read_bytes();assert hashlib.sha256(lib).hexdigest()=='57a0b403485b99ebd676942af4673ac086b86c7c75fbdc3e5c0038501dd22ba3'
s=lib.decode();a=s.index('cell (DFFASRHQNx1_ASAP7_75t_R)');b=s.index('ff (IQN,IQNN)',a);ff=s[b:s.index('\n    }',b)]
for term in ['clear : "!SETN"','preset : "!RESETN"','next_state : "!D"','clocked_on : "CLK"','clear_preset_var1 : L','clear_preset_var2 : L']:assert term in ff,term
raw=Path('models.original.v').read_bytes();text=raw.decode();pat=r'module DFFASRHQNx1_ASAP7_75t_R\(.*?\nendmodule';m=re.search(pat,text,re.S);assert m and 'assign _04_ = RESETN & ~(SETN);'in m.group()
new='''module DFFASRHQNx1_ASAP7_75t_R(CLK,D,QN,RESETN,SETN);
 input wire CLK,D,RESETN,SETN;
 output wire QN;
 reg IQN;
 // Exact Liberty: clear=!SETN, preset=!RESETN, both asserted resolves IQN=L.
 // Mask preset while clear is active; release of clear with preset held must reassert preset.
 wire reset_gate=RESETN | ~SETN;
 always @(posedge CLK or negedge reset_gate or negedge SETN)
  if(!SETN) IQN<=1'b0;
  else if(!reset_gate) IQN<=1'b1;
  else IQN<=~D;
 assign QN=IQN;
endmodule'''
fixed=text[:m.start()]+new+text[m.end():];Path('models.v').write_text(fixed);Path('adapter.v').write_text(new+'\n')
Path('adapter_receipt.json').write_text(json.dumps(dict(liberty_sha256=hashlib.sha256(lib).hexdigest(),ff_contract=ff,original_models_sha256=hashlib.sha256(raw).hexdigest(),adapted_models_sha256=hashlib.sha256(fixed.encode()).hexdigest(),adapter_sha256=hashlib.sha256((new+'\n').encode()).hexdigest(),only_changed_module='DFFASRHQNx1_ASAP7_75t_R',all_other_model_bytes_identical=True,scope='Simulation semantics only; no RTL, mapped cell or physical change'),indent=2)+'\n')
