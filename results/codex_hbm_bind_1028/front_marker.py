"""Remove only the consumed INT8 marker from8exact front interfaces; original bit116 must be zero.
Existing front's reserved-bit faultcheck stays implemented, with its consumed marker internal.
"""
import json,re,sys
from pathlib import Path
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'tools'));import die_port_bind as D
mod='ot_hbm_sm_attn_front_static';variant=mod+'_nomarker';src=root/'rtl/hbm_accel/sm/attn'/f'{mod}.sv';s=src.read_text();a=s.index('module '+mod);z=re.search(r'^\s*\);\s*$',s[a:],re.M).end()+a
h=s[a:z].replace('module '+mod,'module '+variant,1);h,n=re.subn(r'\[191:0\](\s+command\b)',r'[190:0]\1',h);assert n==1
m=next(x for x in D.parse_modules(s,str(src)) if x.name==mod);params=[x for x in m.params if x not in m.localparams]
body='\n '+mod+' #('+','.join('.'+x+'('+x+')' for x in params)+') u_front (\n'+',\n'.join('.'+p+'('+ ("{command[190:116],1'b0,command[115:0]}" if p=='command' else p)+')' for p in m.ports)+'\n );\nendmodule\n'
(root/'rtl/hbm_next/bind/ot_hnx_sm_front_nomarker.sv').write_text('`default_nettype none\n'+h+body+'`default_nettype wire\n')
rules=[]
for i in range(8):rules.append(dict(inst=re.escape(f'sm_NW{i}.u_front'),module=variant,reason='INT8markerconsumedandclearedbytheactualSMparent; exactreserved0sourcebitonly, noaddedcycle',port_bits={'command':[j for j in range(192) if j!=116]},port_bit_constants={'command':{'116':'0'}}))
Path(__file__).with_name('front_marker_substitute_inst.json').write_text(json.dumps(rules,indent=1)+'\n');print('frontmarker8exactinstances;191inputbits;reinsertreservedbit116=0;0cycles')
