"""CurrentnativeHCOL h0/h1 forms;HALF0chainseedinternal,DELIVERED_RESETpreserved.
Usesexistingplannamesatthesameoutlines; no arithmetic/pipelinechanges.
"""
from pathlib import Path
import json
root=Path(__file__).resolve().parents[2]
ports=[('input',2,'clk_pair'),('input',1,'rst_col'),('input',1,'qv_b'),('input',568,'q_b'),('input',544,'key'),('input',32,'hid4'),('input',32,'cs_in'),('input',1,'cf_in'),('output',32,'cs_out'),('output',1,'cf_out'),('output',2,'prdy')]
out='`timescale 1ns/1ps\n`default_nettype none\n// No inferrednewmath: nativeHCOL atfixedHALF, samecurrentMUT/DELIVERED_RESET.\n'
for half in [0,1]:
 mod=f'ot_hbm_idx_score_hcol_h{half}';pp=[x for x in ports if not(half==0 and x[2] in ['cs_in','cf_in'])]
 out+=f'module {mod} #(parameter integer MUT=0,DELIVERED_RESET=1)(\n'+',\n'.join(f' {d} wire '+(f'[{w-1}:0] ' if w>1 else '')+n for d,w,n in pp)+'\n);\n'
 out+=f' ot_hidx_score_hcol #(.HALF({half}),.MUT(MUT),.DELIVERED_RESET(DELIVERED_RESET)) u_native (\n'+',\n'.join('.'+n+'('+ ("32'd0" if n=='cs_in' and half==0 else "1'b0" if n=='cf_in' and half==0 else n)+')' for _,_,n in ports)+'\n );\nendmodule\n'
out+='`default_nettype wire\n'
(root/'rtl/hbm_next/bind/ot_hnx_idx_hcol_plan.sv').write_text(out)
Path(__file__).with_name('hcol_wrapper_ports.json').write_text(json.dumps(dict(original='ot_hidx_score_hcol',ports=[dict(direction=d,width=w,port=n) for d,w,n in ports],forms=[dict(module=f'ot_hbm_idx_score_hcol_h{h}',HALF=h,DELIVERED_RESET=1,removed_ports=['cs_in','cf_in'] if h==0 else [],added_cycles=0) for h in [0,1]],hid4='Actual timed hid4 nets: preserve launch registers and timing; no static strap conversion'),indent=2)+'\n')
print('currentHCOL2forms emitted;128HALF0seed33bits internal; hid4 remains timed source nets')
