from pathlib import Path
import json,re,hashlib
p=Path(__file__).parent
source=p/'production_snapshot.sv'
if not source.exists():source=Path('/srv/opentallas-scratch2/claude/wt/codex-bodyctl-off4-1106/rtl/hbm_accel/cores_split/reform_1105s/q3/ot_hfd_coll_q3_body_ctl.sv')
s=source.read_text();audit=json.loads((p.parent/'capture_binding/capture_binding_audit.json').read_text())
raw=sorted({x['capture_D_scalar'] for x in audit['scalar_rewinds']});assert len(raw)==80
blocks=list(re.finditer(r'`ifdef OT_Q3CTL_OFF4_RT\n(.*?)`endif',s,re.S))
helperblocks=[m for m in blocks if 'ot_bodyctl_off32_split_d ot_q3_off4_' in m[1]];assert len(helperblocks)==1
hb=helperblocks[0][0];assert '`else' not in hb;assert len(re.findall(r'^ot_bodyctl_off32_split_d ',hb,re.M))==3
assert set(re.findall(r'\\[^\s]+',hb))==set(raw)
caps=[]
for reg in ['_237566_','_237567_','_237568_']:
 b=[m for m in blocks if re.search(re.escape(reg)+r' <= ot_q3_off4_',m[1])];assert len(b)==1
 truepart=b[0][1].split('`else',1)[0]
 assert re.fullmatch(r'  always @\(posedge clk_control\)\n    '+re.escape(reg)+r' <= ot_q3_off4_\w+;\n',truepart)
 caps.append(truepart)
ports=['input wire clk_control']+['input wire '+x+' ' for x in raw]+['output reg [31:0] '+r for r in ['_237566_','_237567_','_237568_']]
text='`default_nettype none\nmodule hook_only(\n'+',\n'.join(ports)+'\n);\n'+hb+'\n'+''.join(caps)+'endmodule\n`default_nettype wire\n'
(p/'hook_only.sv').write_text(text)
(p/'extraction_manifest.json').write_text(json.dumps({'production_source_sha256':hashlib.sha256(s.encode()).hexdigest(),'raw_D_scalar_inputs':raw,'helper_snippet_literal':hb,'actual_output_capture_snippets':caps,'new_output_registers':3,'namespace_input_count':80,'compile_flag':'OT_Q3CTL_OFF4_RT'},indent=2)+'\n')
