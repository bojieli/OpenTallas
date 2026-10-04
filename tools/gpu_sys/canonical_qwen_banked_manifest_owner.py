"""Whole-operation source banks separate from the unmodified execution actor.

Static masks are admission requirements, never grants. All banks retain the
same full239 execution association. Physical bank is installed SM_INDEX, not
retagged tuple rank/SM. Euclid owns atomic acceptance across these outputs.
"""
from pathlib import Path
import tempfile
from functools import lru_cache
from tools.gpu_sys.canonical_qwen_manifest_range_owner import generate as base_generate, model as base_model, profiles
from tools.gpu_sys.canonical_qwen_source_mapping import SourcePlacement, uint


@lru_cache(maxsize=4)
def bank_masks(p):
 inputs,outputs=profiles(p)
 masks={pc:0 for pc in range(1737)}
 for bank,pc in set(inputs)|set(outputs):masks[pc]|=1<<bank
 initial={}
 for h in p.rf.values():
  if h.birth<0:
   v=p.version_ids[h.version];initial[v]=initial.get(v,0)|(1<<(h.rank*32+h.sm))
 return masks,initial


def required_banks(p,pc,actor,initial_version=None):
 uint(actor,6,'execution actor');uint(pc,11,'source PC')
 normal,initial=bank_masks(p)
 if pc==2047:
  if initial_version not in initial:raise ValueError('INITIAL immutable version required')
  mask=initial[initial_version]
 else:
  if pc>=1737 or initial_version is not None:raise ValueError('native whole-operation identity')
  mask=normal[pc]
 return mask|(1<<actor)


def mask_rom(p):
 normal,initial=bank_masks(p)
 ins,outs=profiles(p)
 extra=[]
 for name,profile in [('source_input_bank_mask',ins),('source_output_bank_mask',outs)]:
  masks={}
  for bank,pc in profile:masks[pc]=masks.get(pc,0)|(1<<bank)
  extra+=['function automatic [63:0] '+name+'(input [10:0] pc);','begin '+name+'=0;case(pc)']
  for pc,mask in sorted(masks.items()):extra.append(f"11'd{pc}:{name}=64'h{mask:016x};")
  extra+=['default:'+name+'=0;endcase end endfunction']
 lines=['function automatic [63:0] operation_bank_mask(input [10:0] pc,input [10:0] version);',
 'begin operation_bank_mask=0;case(pc)']
 for pc,mask in normal.items():
  if mask:lines.append(f"11'd{pc}:operation_bank_mask=64'h{mask:016x};")
 lines+=['11\'d2047:case(version)']
 for v,mask in sorted(initial.items()):lines.append(f"11'd{v}:operation_bank_mask=64'h{mask:016x};")
 lines+=['default:operation_bank_mask=0;endcase','default:operation_bank_mask=0;endcase end endfunction']
 return '\n'.join(lines+extra)


def model(p=None):
 p=p or SourcePlacement.released();m=base_model(p);normal,initial=bank_masks(p)
 # Upper bound: one actual 11-bit comparator and64 gated output bits per
 # populated immutable normal/INITIAL row, replicated at all64 bank ports.
 entries=sum(bool(v) for v in normal.values())+len(initial)
 m['schema']='canonical-qwen-banked-manifest-owner'
 m['bank_actor_composition']=dict(physical_bank='installed SM_INDEX0..63',execution_actor='unaltered root tuple bits35:30',
  scope='whole operation ALL RF input/output homes, not per tile or per expert subset',
  required_banks='immutable operation/INITIAL-version mask OR execution actor onehot',
  immutable_mask_entries=entries,mask_read_ports=192,additional_mutable_FF=0,
  NAND2_upper_bound=3*64*entries*(5*11+3*64)+64*(5*6+3*64),
  mask_output_bits_per_bank=192,root_actor_decode_fanout=64,root_compare_width=209,
  callback_identity_width=239,child_owner_width=55,query_latency_edges=5,
  external_atomic_GO_terminal_reverse_frame_network='Euclid: all required bank ready AND, valid ANDready gated; no partial acceptance',
  external_network_latency_and_loaded_area_qualified=False,
  full_factory_ready=False)
 import json
 root=Path(__file__).resolve().parents[2]
 facts=json.loads((root/m['source_pins'][0]['path']).read_text())['facts']
 area=facts['NAND2x1_ASAP7_75t_R']['SS']['area_um2']
 m['control_body_estimate_mm2']+=m['bank_actor_composition']['NAND2_upper_bound']*area/1e6
 return m


def generate(out,p=None):
 p=p or SourcePlacement.released()
 with tempfile.TemporaryDirectory(prefix='nash-banked-owner-') as d:t=base_generate(d,p).read_text()
 def replace(a,b):
  nonlocal t
  if a not in t:raise ValueError('source anchor absent: '+a[:100])
  t=t.replace(a,b)
 replace('ot_gpu_qwen_manifest_range_owner','ot_gpu_qwen_banked_manifest_range_owner')
 replace('ot_gpu_qwen_manifest_source_record','ot_gpu_qwen_banked_manifest_source_record')
 replace('output wire [6:0] captured_output_rows,','output wire [63:0] required_bank_mask64,required_input_bank_mask64,required_output_bank_mask64,\n output wire [6:0] captured_output_rows,')
 replace(' function automatic empty_root',mask_rom(p)+'''\n assign required_input_bank_mask64=initial_root(bind_tuple)?0:source_input_bank_mask(bind_tuple[174:164]);
 assign required_output_bank_mask64=initial_root(bind_tuple)?operation_bank_mask(11'd2047,bind_tuple[29:19]):source_output_bank_mask(bind_tuple[174:164]);
 assign required_bank_mask64=operation_bank_mask(bind_tuple[174:164],bind_tuple[29:19])|(64'h1<<bind_tuple[35:30]);
 function automatic bank_has_initial(input [10:0] version);
 reg [48:0] meta;begin meta=source_meta(version);bank_has_initial=meta[48]&&meta[47];end endfunction
 function automatic bank_participates(input [238:0] rt);
 reg [63:0] mask;begin mask=operation_bank_mask(rt[174:164],rt[29:19])|(64'h1<<rt[35:30]);bank_participates=mask[SM_INDEX];end endfunction
 function automatic empty_root''')
 # Bank-local zero-output proof is from immutable counts, not from the root's
 # anchor version/range (which can belong to a different physical bank).
 replace("rt[174:164]<1737&&","(rt[174:164]<1737||rt[174:164]==2047)&&")
 replace('rt[35]==(SM_INDEX/32)&&rt[34:30]==(SM_INDEX%32)&&\n  rt[29:19]==11\'d2047&&rt[18:10]==0&&rt[9:0]==0&&source_output_count(rt[174:164])==0;',
         'bank_participates(rt)&&(rt[174:164]==2047?!bank_has_initial(rt[29:19]):source_output_count(rt[174:164])==0);')
 replace("initial_root=m[48]&&m[47]&&rt[174:164]==11'd2047;",
         "initial_root=(operation_bank_mask(11'd2047,rt[29:19])!=0)&&rt[174:164]==11'd2047;")
 replace('assign required_output_rows=(local_tuple(bind_tuple)||initial_root(bind_tuple))?(initial_root(bind_tuple)?1:source_output_count(bind_tuple[174:164])):0;',
         'assign required_output_rows=initial_root(bind_tuple)?(bank_has_initial(bind_tuple[29:19])?1:0):source_output_count(bind_tuple[174:164]);')
 replace('t[35]==(SM_INDEX/32)&&t[34:30]==(SM_INDEX%32)&&page_mask(t)!=0;',
         'bank_participates(t)&&page_mask(t)!=0;')
 replace('claim_tuple[35]==(SM_INDEX/32)&&claim_tuple[34:30]==(SM_INDEX%32)&&page_mask(claim_tuple)!=0',
         'bank_participates(claim_tuple)&&page_mask(claim_tuple)!=0')
 # A local child keeps its own lower30/range/owner; bind/GO/publish root is the
 # enclosing captured execution root. Never relabel child physical bank as actor.
 replace('if(t==b[B_TUPLE +:239])output_row=i;', 'if(root_member(t,b[B_TUPLE +:239])&&output_row<0)output_row=i;')
 replace('if(t==bind_tuple&&!r[i][R_PRODUCER_STARTED])bind_output_row=i;',
         'if(root_member(t,bind_tuple)&&!r[i][R_PRODUCER_STARTED]&&bind_output_row<0)bind_output_row=i;')
 replace('if(t==producer_visible_tuple)visible_row=i;', 'if(root_member(t,producer_visible_tuple)&&visible_row<0)visible_row=i;')
 replace('if(t==publish_tuple&&r[i][R_OWNER55 +:55]==publish_owner)pub_row=i;', 'if(root_member(t,publish_tuple)&&pub_row<0)pub_row=i;')
 replace('if(t==frame_retire_tuple&&r[i][R_OWNER55 +:55]==frame_retire_owner)retire_row=i;', 'if(root_member(t,frame_retire_tuple)&&retire_row<0)retire_row=i;')
 replace('if(b[B_LIVE]&&t==b[B_TUPLE +:239]&&!r[i][R_ACK_DELIVERED])aggregate_row=i;',
         'if(b[B_LIVE]&&root_member(t,b[B_TUPLE +:239])&&!r[i][R_ACK_DELIVERED]&&aggregate_row<0)aggregate_row=i;')
 replace('if((local_tuple(bind_tuple)||initial_root(bind_tuple))&&bind_output_row<0)bind_legal=0;',
         'if(!bank_participates(bind_tuple)||(required_output_rows!=0&&bind_output_row<0))bind_legal=0;')
 # ACK mask identifies the captured enclosing root; completeness is still ALL
 # actual local child bitmaps, never compare a remote child range to root range.
 replace('assign rf_range_ack_page_mask=aggregate_row>=0?r[aggregate_row][R_ACK_BITMAP +:32]:0;',
         'assign rf_range_ack_page_mask=empty_root(b[B_TUPLE +:239])?0:page_mask(b[B_TUPLE +:239]);')
 replace('publish_page_mask==page_mask(publish_tuple)&&r[pub_row][R_ACK_BITMAP +:32]==publish_page_mask',
         'publish_page_mask==page_mask(publish_tuple)&&complete_outputs')
 replace('!local_tuple(frame_retire_tuple)||(retire_row>=0',
         '(!local_tuple(frame_retire_tuple)&&!initial_root(frame_retire_tuple))||(retire_row>=0')
 out=Path(out);out.mkdir(parents=True,exist_ok=True)
 f=out/'ot_gpu_qwen_banked_manifest_range_owner.sv';f.write_text(t);return f

if __name__=='__main__':
 import argparse
 a=argparse.ArgumentParser();a.add_argument('--out',required=True);print(generate(a.parse_args().out))
