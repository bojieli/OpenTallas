from pathlib import Path
import re,sys,json,shutil
sys.path.insert(0,'/srv/opentallas-scratch/claude/wt/codex-kv-pc-collar-1029/physical/die_plan/qwen_kvsys/cores/harden')
from kvspc_native_collar import transform,PORT
b=Path(__file__).parent
for kind,module,sourcefile in [('normal','qkd_kvs_pc','current.sv'),('hhp','qkd_kvs_pc_h_head_p','hhp_current.sv')]:
 old=b/('coupon' if kind=='normal' else 'coupon_hhp');out=b/('native_coupon_'+kind);out.mkdir(exist_ok=True)
 wrappers=(old/'wrappers.sv').read_text();adapter_header=wrappers[:wrappers.index(');')+2];ports=PORT.findall(adapter_header);outs=[(w,n) for d,w,n in ports if d=='output']
 original=(b/'parent_native'/sourcefile).read_text();a=re.search(r'\bmodule\s+'+module+r'\b',original).start();end=original.index(');',a);header=original[a:end]
 header+=',\n'+',\n'.join(f'    output wire {w} coupon_{n}' for w,n in outs)+'\n);\n'
 nativeports=PORT.findall(header)
 chain='qkd_kv_pc_chain_station_b'+('_p' if kind=='hhp' else '')
 remap={'ck':'ck','rst_n':'rst_n','pc':'pc__pc','cfg_stack':'pc__cfg_stack','di':'i_next','land_er':'pc__land_er'}
 body='    '+chain+' u_actual_chain (\n'+',\n'.join(f'        .{n}({remap.get(n,"coupon_"+n)})' for d,w,n in ports)+'\n    );\nendmodule\n'
 good,receipt=transform(header+body,module);(out/'native_receipt.json').write_text(json.dumps(receipt,indent=2))
 native=good+good.replace(module,module+'_badbit').replace('pcin_i_next <= i_next[779:0];',"pcin_i_next <= i_next[779:0] ^ 780'd4;")+good.replace(module,module+'_badreset').replace('pcin_rst_n <= rst_n;',"pcin_rst_n <= 1'b1;")
 adapters=[]
 formap={'ck':'ck[0]','hck':'ck[0]','rst_n':'rst_n','hrst_n':'rst_n','pc__pc':'pc','pc__cfg_stack':'cfg_stack','i_next':'di','pc__land_er':'land_er'}
 for name,target,enable in [('pc_chain_collar_good',module,1),('pc_chain_collar_badbit',module+'_badbit',1),('pc_chain_collar_badreset',module+'_badreset',1),('pc_chain_collar_default',module,0)]:
  con=[]
  for d,w,n in nativeports:
   if n.startswith('coupon_'):con.append(f'.{n}({n[7:]})')
   elif d=='input':
    value=formap.get(n,"'0");con.append(f'.{n}({value})')
   else:con.append(f'.{n}()')
  adapters.append(adapter_header.replace('pc_chain_collar_good',name)+'\n'+target+f' #(.KVSPC_INPUT_COLLAR({enable})) u_native ('+', '.join(con)+');\nendmodule\n')
 (out/'wrappers.sv').write_text('`timescale 1ns/1ps\n'+native+'\n'.join(adapters))
 tb=(old/'tb.sv').read_text();decl='\n'.join(f'wire {w} d_{n};' for w,n in outs);con=', '.join(f'.{n}({"clk" if n=="ck" else n if d=="input" else "d_"+n})' for d,w,n in ports)
 tb=tb.replace('integer cyc,',decl+'\npc_chain_collar_default u_default ('+con+');\ninteger cyc,')
 pack=lambda p:'{'+','.join(p+'_'+n for w,n in outs)+'}'
 tb=tb.replace('if(cyc>12)begin','if(cyc>12)begin\n if('+pack('d')+' !== '+pack('g')+')$fatal(1,"DEFAULT_NATIVE_CHANGED");')
 (out/'tb.sv').write_text(tb)
 for fn in [chain+'.sv','ot_kvpc_pin_ff.sv']:shutil.copyfile(old/fn,out/fn)
 print(kind,receipt['flops'],len(ports))
