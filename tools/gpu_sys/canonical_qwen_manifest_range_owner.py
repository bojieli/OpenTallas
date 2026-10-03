"""Actual source-complete input/output manifest successor of the measured leaf.

No repeated engine GO, invented owner tag or new mutable state: all siblings
retain their distinct child239/range/owner55 in the already protected rows.
The anchor root is captured239; equal high209 binds session/PC/tag/gen/rank/SM.
"""
from pathlib import Path
from collections import defaultdict
from tools.gpu_sys.canonical_qwen_range_owner_rtl import BITS,declarations,meta_ROM
from tools.gpu_sys.canonical_qwen_source_mapping import SourcePlacement


def profiles(p):
 ins=defaultdict(list);outs=defaultdict(list)
 for h in p.rf.values():
  i=h.rank*32+h.sm;vid=p.version_ids[h.version]
  if h.birth>=0:outs[i,h.birth].append(vid)
  for pc in h.consumers:ins[i,pc].append(vid)
 assert max(map(len,ins.values()))<=7 and max(map(len,outs.values()))<=7
 return {k:tuple(sorted(v)) for k,v in ins.items()},{k:tuple(sorted(v)) for k,v in outs.items()}


def count_ROM(p):
 ins,outs=profiles(p);lines=[]
 for name,d in [('source_input_count',ins),('source_output_count',outs)]:
  lines+=['function automatic [3:0] '+name+'(input [10:0] pc);', 'begin '+name+'=0;case(SM_INDEX)']
  for i in range(64):
   lines.append(str(i)+':case(pc)')
   for (sm,pc),values in sorted(d.items()):
    if sm==i:lines.append("11'd%d:%s=4'd%d;"%(pc,name,len(values)))
   lines.append('default:'+name+'=0;endcase')
  lines+=['default:'+name+'=0;endcase end endfunction']
 return '\n'.join(lines)


def generate(out,placement=None):
 p=placement or SourcePlacement.released()
 t=Path(__file__).with_name('canonical_qwen_range_owner_template.sv').read_text()
 t=t.replace('.BASE(z*14)','.BASE(512+z*14)').replace('.BASE(98)','.BASE(610)').replace('.BASE(100)','.BASE(612)').replace('.BASE(106)','.BASE(618)')
 t=t.replace('ot_gpu_qwen_native_range_owner','ot_gpu_qwen_manifest_range_owner').replace('ot_gpu_qwen_source_record','ot_gpu_qwen_manifest_source_record')
 t=t.replace('@SOURCE_META@',meta_ROM(p)+'\n'+count_ROM(p))
 for k,v in BITS.items():t=t.replace('@'+k.upper()+'_BITS@',str(v))
 t=t.replace('@DECLARATIONS@',declarations()+'\n localparam integer B_EMPTY_ACK=250,B_EMPTY_VISIBLE=251,B_EMPTY_PUBLISHED=252;')
 t=t.replace('BB=250','BB=253')
 t=t.replace('input wire go_accepted,input wire [238:0] go_tuple,','input wire go_accepted,input wire [238:0] go_tuple,\n input wire issuer_held_valid,issuer_held_fault,input wire [238:0] issuer_held_tuple,input wire [54:0] issuer_held_owner55,\n input wire workspace_children_drained,output wire workspace_held_valid,workspace_new_admit,\n output wire [238:0] workspace_held_tuple,output wire [54:0] workspace_held_owner55,')
 t=t.replace('output wire [31:0] expected_output_page_mask,','output wire [31:0] expected_output_page_mask,\n output wire [6:0] captured_output_rows,output wire [3:0] required_input_rows,required_output_rows,')
 at=t.index(' // All matches are computed')
 t=t[:at]+'''
 function automatic empty_root(input [238:0] rt);
 begin empty_root=rt[238:175]==g[G_SESSION +:64]&&rt[174:164]<1737&&
  rt[35]==(SM_INDEX/32)&&rt[34:30]==(SM_INDEX%32)&&
  rt[29:19]==11'd2047&&rt[18:10]==0&&rt[9:0]==0&&source_output_count(rt[174:164])==0;end endfunction
 wire issuer_match=issuer_held_valid&&!issuer_held_fault&&issuer_held_tuple==b[B_TUPLE +:239];
 assign workspace_held_valid=all_clean&&b[B_LIVE]&&b[B_GO]&&issuer_match&&
  b[B_TUPLE+35]==(SM_INDEX/32)&&b[B_TUPLE+30 +:5]==(SM_INDEX%32);
 assign workspace_held_tuple=b[B_TUPLE +:239];assign workspace_held_owner55=issuer_held_owner55;
 assign workspace_new_admit=active&&workspace_held_valid;
 function automatic initial_root(input [238:0] rt);
 reg [48:0] m;begin m=source_meta(rt[29:19]);initial_root=m[48]&&m[47]&&rt[174:164]==11'd2047;end
 endfunction
 function automatic root_member(input [238:0] child,input [238:0] root);
 reg [48:0] m;begin m=source_meta(child[29:19]);
 root_member=child[238:30]==root[238:30]&&
 ((initial_root(root)&&child[29:19]==root[29:19])||
 (!initial_root(root)&&m[48]&&!m[47]&&m[30:20]==root[174:164]));end endfunction
 assign required_input_rows=initial_root(bind_tuple)?0:source_input_count(bind_tuple[174:164]);
 assign required_output_rows=(local_tuple(bind_tuple)||initial_root(bind_tuple))?(initial_root(bind_tuple)?1:source_output_count(bind_tuple[174:164])):0;
 reg [6:0] manifest_rows;
 integer input_count,output_count;
 reg complete_outputs;
 assign captured_output_rows=manifest_rows;
''' +t[at:]
 t=t.replace('barrier_ok=1;bind_legal=', 'input_count=0;output_count=0;manifest_rows=0;complete_outputs=1;\n  barrier_ok=1;bind_legal=')
 t=t.replace('if(t==bind_tuple&&!r[i][R_PRODUCER_STARTED])bind_output_row=i;', '''if(t==bind_tuple&&!r[i][R_PRODUCER_STARTED])bind_output_row=i;
    if(root_member(t,bind_tuple))output_count=output_count+1;
    if(b[B_LIVE]&&root_member(t,b[B_TUPLE +:239]))begin
     manifest_rows[i]=1;
     if(!r[i][R_PRODUCER_STARTED]||r[i][R_ACK_BITMAP +:32]!=page_mask(t))complete_outputs=0;
    end''')
 t=t.replace('if(r[i][R_ACK_BITMAP +:32]==page_mask(t)&&r[i][R_PRODUCER_STARTED]&&!r[i][R_ACK_DELIVERED]&&aggregate_row<0)aggregate_row=i;', 'if(b[B_LIVE]&&t==b[B_TUPLE +:239]&&!r[i][R_ACK_DELIVERED])aggregate_row=i;')
 t=t.replace('if(bind_mask[i])begin','if(bind_mask[i])begin\n    input_count=input_count+1;')
 t=t.replace('claim_legal=local_tuple(claim_tuple)&&cm[48]', 'claim_legal=(local_tuple(claim_tuple)||(initial_root(claim_tuple)&&claim_tuple[238:175]==g[G_SESSION +:64]&&claim_tuple[35]==(SM_INDEX/32)&&claim_tuple[34:30]==(SM_INDEX%32)&&page_mask(claim_tuple)!=0))&&cm[48]')
 t=t.replace('page_mask(bind_tuple)!=0;', '(page_mask(bind_tuple)!=0||empty_root(bind_tuple));')
 t=t.replace('bind_tuple[174:164]<1737&&','(bind_tuple[174:164]<1737||initial_root(bind_tuple))&&')
 t=t.replace('if(local_tuple(bind_tuple)&&bind_output_row<0)bind_legal=0;', '''if(input_count!=required_input_rows||output_count!=required_output_rows)bind_legal=0;
  if((local_tuple(bind_tuple)||initial_root(bind_tuple))&&bind_output_row<0)bind_legal=0;
  if(!complete_outputs)aggregate_row=-1;''')
 t=t.replace('query_tuple==t)', 'query_tuple[238:30]==t[238:30])')
 t=t.replace('q[Q_TUPLE +:239]==r[qr][R_PRODUCER_TUPLE +:239]', 'q[Q_TUPLE+30 +:209]==r[qr][R_PRODUCER_TUPLE+30 +:209]')
 t=t.replace('if(output_row>=0)rn[output_row][R_PRODUCER_STARTED]=1;', 'for(n=0;n<7;n=n+1)if(manifest_rows[n])rn[n][R_PRODUCER_STARTED]=1;')
 t=t.replace('if(rf_range_ack_valid&&rf_range_ack_ready)rn[aggregate_row][R_ACK_DELIVERED]=1;', 'if(rf_range_ack_valid&&rf_range_ack_ready)for(n=0;n<7;n=n+1)if(manifest_rows[n])rn[n][R_ACK_DELIVERED]=1;')
 t=t.replace('if(producer_visible_valid&&producer_visible_ready)rn[visible_row][R_PRODUCER_VISIBLE]=1;', 'if(producer_visible_valid&&producer_visible_ready)for(n=0;n<7;n=n+1)if(manifest_rows[n])rn[n][R_PRODUCER_VISIBLE]=1;')
 t=t.replace('if(publish_valid&&publish_ready)rn[pub_row][R_PUBLISHED]=1;', 'if(publish_valid&&publish_ready)for(n=0;n<7;n=n+1)if(manifest_rows[n])rn[n][R_PUBLISHED]=1;')
 t=t.replace('if(retire_row>=0)rn[retire_row][R_PRODUCER_FRAME_RETIRED]=1;', 'for(n=0;n<7;n=n+1)if(manifest_rows[n])rn[n][R_PRODUCER_FRAME_RETIRED]=1;')
 # Whole-visible identity and publication anchor must be the captured root,
 # not an arbitrary child carrying a compatible native prefix.
 t=t.replace('go_match=barrier_ok&&next_source_PC==go_tuple[174:164]', 'go_match=barrier_ok&&(initial_root(go_tuple)?next_source_PC==0:next_source_PC==go_tuple[174:164])')
 t=t.replace('&&(!local_tuple(b[B_TUPLE +:239])||output_row>=0);','&&(empty_root(b[B_TUPLE +:239])||!local_tuple(b[B_TUPLE +:239])||output_row>=0);')
 t=t.replace('assign producer_visible_ready=active&&visible_row>=0;', 'assign producer_visible_ready=active&&visible_row>=0&&b[B_LIVE]&&producer_visible_tuple==b[B_TUPLE +:239];')
 t=t.replace('(producer_visible_valid&&(visible_row<0||', '(producer_visible_valid&&(!b[B_LIVE]||producer_visible_tuple!=b[B_TUPLE +:239]||visible_row<0||')
 t=t.replace('wire unexpected=base_active&&(', 'wire unexpected=base_active&&(')
 t=t.replace('(producer_visible_valid&&(!b[B_LIVE]||producer_visible_tuple!=b[B_TUPLE +:239]||visible_row<0||(visible_row>=0&&(!r[visible_row][R_PRODUCER_STARTED]||r[visible_row][R_PRODUCER_VISIBLE]))))',
 '(producer_visible_valid&&(!b[B_LIVE]||!b[B_GO]||producer_visible_tuple!=b[B_TUPLE +:239]||(empty_root(producer_visible_tuple)?b[B_EMPTY_VISIBLE]:(visible_row<0||(visible_row>=0&&(!r[visible_row][R_PRODUCER_STARTED]||r[visible_row][R_PRODUCER_VISIBLE]))))))')
 t=t.replace('assign rf_range_ack_valid=active&&aggregate_row>=0;', 'assign rf_range_ack_valid=active&&b[B_LIVE]&&b[B_GO]&&issuer_match&&(aggregate_row>=0||(empty_root(b[B_TUPLE +:239])&&!b[B_EMPTY_ACK]));')
 t=t.replace('assign rf_range_ack_tuple=aggregate_row>=0?r[aggregate_row][R_PRODUCER_TUPLE +:239]:0;', 'assign rf_range_ack_tuple=b[B_TUPLE +:239];')
 t=t.replace('assign rf_range_ack_owner=aggregate_row>=0?r[aggregate_row][R_OWNER55 +:55]:0;', 'assign rf_range_ack_owner=issuer_held_owner55;')
 t=t.replace('assign producer_visible_ready=active&&visible_row>=0&&b[B_LIVE]&&producer_visible_tuple==b[B_TUPLE +:239];', 'assign producer_visible_ready=active&&b[B_LIVE]&&b[B_GO]&&producer_visible_tuple==b[B_TUPLE +:239]&&(visible_row>=0||(empty_root(producer_visible_tuple)&&!b[B_EMPTY_VISIBLE]));')
 t=t.replace('assign publish_ready=active&&pub_row>=0&&r[pub_row][R_PRODUCER_VISIBLE]&&r[pub_row][R_ACK_DELIVERED]&&\n  !r[pub_row][R_PUBLISHED]&&publish_page_mask==page_mask(publish_tuple)&&r[pub_row][R_ACK_BITMAP +:32]==publish_page_mask;',
 'assign publish_ready=active&&b[B_LIVE]&&issuer_match&&publish_tuple==b[B_TUPLE +:239]&&publish_owner==issuer_held_owner55&&\n (empty_root(publish_tuple)?(publish_page_mask==0&&b[B_EMPTY_ACK]&&b[B_EMPTY_VISIBLE]&&!b[B_EMPTY_PUBLISHED]):\n (pub_row>=0&&r[pub_row][R_PRODUCER_VISIBLE]&&r[pub_row][R_ACK_DELIVERED]&&!r[pub_row][R_PUBLISHED]&&publish_page_mask==page_mask(publish_tuple)&&r[pub_row][R_ACK_BITMAP +:32]==publish_page_mask));')
 t=t.replace('assign frame_retire_ready=active&&(!local_tuple(frame_retire_tuple)||(retire_row>=0&&r[retire_row][R_PUBLISHED]&&!r[retire_row][R_PRODUCER_FRAME_RETIRED]))&&b[B_LIVE]',
 'assign frame_retire_ready=active&&workspace_children_drained&&issuer_match&&frame_retire_owner==issuer_held_owner55&&\n (empty_root(frame_retire_tuple)?b[B_EMPTY_PUBLISHED]:(!local_tuple(frame_retire_tuple)||(retire_row>=0&&r[retire_row][R_PUBLISHED]&&!r[retire_row][R_PRODUCER_FRAME_RETIRED])))&&b[B_LIVE]')
 t=t.replace('if(rf_range_ack_valid&&rf_range_ack_ready)for', 'if(rf_range_ack_valid&&rf_range_ack_ready)begin if(empty_root(b[B_TUPLE +:239]))bn[B_EMPTY_ACK]=1;end\n   if(rf_range_ack_valid&&rf_range_ack_ready)for')
 t=t.replace('if(producer_visible_valid&&producer_visible_ready)for', 'if(producer_visible_valid&&producer_visible_ready)begin if(empty_root(producer_visible_tuple))bn[B_EMPTY_VISIBLE]=1;end\n   if(producer_visible_valid&&producer_visible_ready)for')
 t=t.replace('if(publish_valid&&publish_ready)for', 'if(publish_valid&&publish_ready)begin if(empty_root(publish_tuple))bn[B_EMPTY_PUBLISHED]=1;end\n   if(publish_valid&&publish_ready)for')
 out=Path(out);out.mkdir(parents=True,exist_ok=True)
 f=out/'ot_gpu_qwen_manifest_range_owner.sv';f.write_text(t);return f


def model(p=None):
 from tools.gpu_sys.canonical_qwen_range_owner_controls import control_model
 p=p or SourcePlacement.released();m=control_model(p);ins,outs=profiles(p)
 entries=len(ins)+len(outs);nand=entries*(5*11+3*4)
 import json
 root=Path(__file__).resolve().parents[2]
 facts=json.loads((root/m['source_pins'][0]['path']).read_text())['facts']
 area=facts['NAND2x1_ASAP7_75t_R']['SS']['area_um2']
 m['schema']='canonical-qwen-manifest-range-owner'
 m['immutable_manifest_counts']=dict(input_entries=len(ins),output_entries=len(outs),count_width=4,NAND2_budget=nand,additional_FF=0,max_inputs=max(map(len,ins.values())),max_outputs=max(map(len,outs.values())))
 base=m['immutable_case_ROM'];by_sm=base['rows_per_SM'];ce=base['consumer_rows_per_SM']
 # Actual CURRENT parallel queries: seven rowconsumer compares and up to10
 # metadata roots/children. Price replication; a single-port ROM is not free.
 extra_nand=9*sum(n*(5*11+3*49) for n in by_sm)+6*64*ce*(5*20+3*12)+7*(209*5+32*3)
 m['immutable_manifest_counts']['parallel_metadata_ports']=10
 m['immutable_manifest_counts']['parallel_consumer_ports']=7
 m['immutable_manifest_counts']['replication_and_root_compare_NAND2_budget']=extra_nand
 m['control_body_estimate_mm2']+=(nand+extra_nand)*area/1e6
 m['required_native_ports']='Full239 root plus source-owned allinputs and alloutputs. Initial RF sources need legitimate cold initializer root and positive allpage mirrors/fullvisibility; no-reset proof. No-RF-output operations still require separate typed provider completion ABI.'
 m['full_factory_ready']=False
 m['source_seal_namespace']=dict(word_index_begin=512,word_index_end=624,PC_seal_dimension='source SMindex0..63',distinct_from_W2_219words=True,additional_FF=0)
 m['cold_initializer']=dict(command_PC=2047,actual_native_PC_preserved=True,source_class_from_immutable_initial_home=True,claim_initial_required=True,next_native_PC=0,actual_initializer_caller_enrolled=False)
 m['typed_empty_RF']=dict(output_version_sentinel=2047,range_begin=0,range_end=0,ACK_mask=0,source_predicate='only source_output_count(PC)==0 for actual indexed actor',mandatory_whole_visible_and_terminal_reverse=True,additional_payload_bits=3,additional_physical_FF=0,existing_padding_used_only_after_sealed_geometry_update=True,issuer_r2_accepts=False,required_issuer_successor=True)
 m['workspace_context_reuse']=dict(issuer_coded_holder_reused=True,additional_FF=0,witness_input_bits=1+1+239+55,drain_input_bits=1,output_bits=1+1+239+55,root_compare_bits=239,root_match_fanout=7,whole_operator_exclusive_bytes=65536,tile_release_does_not_clear_source_or_operator=True,source_children_drained_required_before_frame_retire=True,client_mux_state_priced_by_Euclid=True)
 m['control_body_estimate_mm2']+=(5*239+3*55)*64*area/1e6
 for bank in m['state_banks']:
  if bank['name']=='accepted_input_binding':bank['fields']=dict(bank['fields'],empty_ACK=1,empty_visible=1,empty_published=1);bank['payload_bits']+=3
 return m

if __name__=='__main__':
 import argparse
 a=argparse.ArgumentParser();a.add_argument('--out',required=True);print(generate(a.parse_args().out))
