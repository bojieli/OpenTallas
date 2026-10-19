#!/usr/bin/env python3
"""Mechanical private receiver derivative; public pinned sources remain unchanged."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[2]
D=ROOT/'rtl/qwen_sys/split_20261014'
def sha(s):return hashlib.sha256(s.encode()).hexdigest()
def once(s,a,b):
 assert s.count(a)==1,(a,s.count(a))
 return s.replace(a,b,1)
manifest={'base':'fe8eac3f2','flag_convention':'raw OR, nonzero true; Z0=data31:19 Z1=data31:5 Z[z+1]=word z for z=1..15','scope':'private default-off source only; no physical/native qualification','files':{}}
for stem in ['programme','static_ctl']:
 src=D/f'qkd_native_attention_{stem}.sv';raw=src.read_text();s=raw
 assert sha(raw)=={'programme':'6c6f1e0178d6f0def903fd9f85c96c8450e331f78e2399b496516c17eac46acc','static_ctl':'cdbf22798ae606880ecfcba24ab56220d3c253b3e4148f21ebdd2559ab35113a'}[stem], 'pinned public source changed'
 if stem=='programme':
  s=s[:s.index('\n// KV-ATTNKIT 10-18: qkd_native59_descriptor_producer')]
  s=once(s,'module qkd_native_attention_programme #','module qkd_native_attention_programme_z17 #')
  s=once(s,'parameter integer LAND=0)','parameter integer LAND=0,parameter integer RX_ZERO17=0)')
  s=once(s,'input wire rx_event,input wire [547:0] rx_payload,','input wire rx_event,input wire [547:0] rx_payload,\n input wire [16:0] rx_zero17,')
  s=once(s,'qkd_native_attention_static_ctl #(.MUT(MUT),.LAND(LAND))','qkd_native_attention_static_ctl_z17 #(.MUT(MUT),.LAND(LAND),.RX_ZERO17(RX_ZERO17))')
  s=once(s,'.rx_payload(rx_payload),','.rx_payload(rx_payload),\n  .rx_zero17(rx_zero17),')
 else:
  s=once(s,'module qkd_native_attention_static_ctl #','module qkd_native_attention_static_ctl_z17 #')
  s=once(s,'parameter integer LAND=0','parameter integer LAND=0,\n parameter integer RX_ZERO17=0')
  s=once(s,'input wire rx_event,input wire [547:0] rx_payload,','input wire rx_event,input wire [547:0] rx_payload,\n input wire [16:0] rx_zero17,')
  s=once(s,'qkd_native_attention_record_ld #(.MUT(MUT==5?3:(MUT==6?4:0)))','qkd_native_attention_record_ld_z17 #(.MUT(MUT==5?3:(MUT==6?4:0)),.RX_ZERO17(RX_ZERO17))')
  assert s.count('.rx_expected_kind(rx_kind_expected),')==2
  s=s.replace('.rx_expected_kind(rx_kind_expected),','.rx_zero17(rx_zero17),\n  .rx_expected_kind(rx_kind_expected),',1)
  s=once(s,'module qkd_native_attention_record_ld #','module qkd_native_attention_record_ld_z17 #')
  a=s.index('module qkd_native_attention_record_ld_z17 #');head=s[:a];tail=s[a:]
  tail=once(tail,'parameter integer MUT=0','parameter integer MUT=0,\n    parameter integer RX_ZERO17=0')
  tail=once(tail,'input wire [547:0] rx_payload,','input wire [547:0] rx_payload,\n    input wire [16:0] rx_zero17,')
  tail=once(tail,'reg [547:0] l_pl;','reg [547:0] l_pl;\n    reg [16:0] l_zero17;\n    // Same unreset capture as l_pl: predicates refer to exactly this record.\n    function legal_rx(input [3:0] kind,input [5:0] layer,input [4:0] beat,input [511:0] data);\n        begin\n            legal_rx=layer<36 && ((kind==Q)||(kind==RESULT)||\n                (kind==CMD && beat==0 && (~|{l_zero17[16:2],l_zero17[0]}) && data[18:1]<8192)||\n                (kind==STATUS && beat==0 && (~|l_zero17[16:1])));\n        end\n    endfunction')
  tail=once(tail,'!legal(rk,rl,rb,l_pl[511:0])','!(RX_ZERO17!=0 ? legal_rx(rk,rl,rb,l_pl[511:0]) : legal(rk,rl,rb,l_pl[511:0]))')
  tail=once(tail,'l_pl<=rx_payload;','l_pl<=rx_payload;\n        l_zero17<=rx_zero17;')
  s=head+tail
 out=D/f'qkd_native_attention_{stem}_z17.sv';out.write_text(s)
 manifest['files'][str(src.relative_to(ROOT))]={'public_sha256':sha(raw),'private_path':str(out.relative_to(ROOT)),'private_sha256':sha(s)}
manifest['constructor_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
manifest['public_dependencies']={name:hashlib.sha256((D/name).read_bytes()).hexdigest() for name in ['qkd_native_attention_record.sv','qkd_native_attention_programme.sv','qkd_native59_descriptor_producer.sv','qkd_native59_command_guard.sv']}
out=ROOT/'results/arch/attn_z17_receiver_1019/source_manifest.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(manifest,indent=2)+'\n')
