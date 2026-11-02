from pathlib import Path
import re,json,hashlib,collections
R=Path(__file__).resolve().parent;I=Path('/srv/opentallas-scratch/claude/codex-hbm-programme-move-0216/input');parent=(I/'hbm_arch_q_b113.sv').read_text();top=(I/'hbm_arch_B2o_bound_top.sv').read_text();closure=Path('/srv/opentallas-scratch/claude/wt/codex-hbm-ctl-native-0440/results/hbm_ctl_native_intake_0440/closure_ot_hgi_sfu_core_split3__ctl.sv').read_text();ctl=closure.split('endmodule')[0];P=json.load(open('/home/ubuntu/coord/tmp/codex-hbm-su00-upper-clock-2335/composite_root_PENDING.json'));parts={p['name']:p for p in P['partitions']}
def conns(s):return dict(re.findall(r'\.(\w+)\((.*?)\)(?:,|\s*$)',s,re.S))
def inst(s,mod,name):
 m=re.search(r'\b'+mod+r'\s*(?:#\([^;]*?\)\s*)?'+name+r'\s*\(([^;]*?)\);',s,re.S);assert m,(mod,name);return conns(m[1])
def cells(s):
 return[dict(instance=m[2],width=int(m[1]),pins=conns(m[3]))for m in re.finditer(r'ot_dp_st\s*#\(\.W\((\d+)\)\)\s+(\w+)\s*\(([^;]*?)\);',s,re.S)]
alltop={m[2]:dict(module=m[1],pins=conns(m[3]))for m in re.finditer(r'^\s*(hbm_arch_\w+)\s+(?:#\([^;]*?\)\s+)?(\w+)\s*\((.*?)\);',top,re.M|re.S)}
cp=inst(parent,'ot_hgi_sfu_core_split3__ctl','u_u_sfucore_Q_ctl');pcells=cells(parent);m56=inst(ctl,'ot_hgi_sfu_vm_static_bridge','m56');assert 'assign local_rq[b*17+:17]={prefetch_v[b],prefetch_sector[b*16+:16]};'in closure
source_ff=[dict(kind='c_rq',CTL_Q='u_core_procdff_66916__Q[135:0]',register='g_compose_m21_q[135:0]',D='VM m56.local_rq[135:0]',VM_expression='for b0..7 {prefetch_v[b],prefetch_sector[16*b+:16]}',clock='clk[0]',reset='n6/m55generatedregion2',enable='NONE'),dict(kind='c_wq',CTL_Q='u_core_procdff_66921__Q[2247:0]',register='g_compose_m22_q[2247:0]',D='VM m56.local_wq[2247:0]',VM_expression='fourg_lg[g].write_q[561:0] registers',clock='clk[0]',reset='n6/m55generatedregion2',enable='NONE',preceding_VM_stage=dict(register='m56.g_lg[g].write_q[561:0]',clock='clk_lg[g]=clk[0]',reset='NONE',update='write_q<=0 each edge, selected281-bit packets overwrite {1,drain_sector16,round_sector(drain_data256,round_q),8hff}',source_cone='actual drain_expected/drain_sector_q/drain_round_q and drain_data; not free or constant'))]
# Stage counts below come from exact source cells, separately compared to plan.
forward=[]
for side in ['NE','NW']:
 for g,suf in enumerate(['su00','su11','su20','su31']):
  bname=side+'_b113';dest=side+'_'+suf;sm=(R/(alltop[dest]['module']+'.sv')).read_text();leaf=inst(sm,'ot_hgi_sfu_lg_pair_tap_leaf',f'u_u_sfu_Q{g}');entry={}
  for kind in ['c_rq','c_wq']:
   ex=leaf[kind];v=re.fullmatch(r'(\w+)_q\[(\d+):(\d+)\]',ex);assert v,ex;port=v[1];bc=next(c for c in cells(sm)if c['pins'].get('q')==port+'_q');node=dest;bus=port;chain=[];seen=set()
   while node!=bname:
    assert(node,bus)not in seen;seen.add((node,bus));net=alltop[node]['pins'][bus];drivers=[]
    for pn,d in alltop.items():
     if pn==node:continue
     for out,wire in d['pins'].items():
      if wire==net and(out.endswith('_o')or out.startswith('xo_')):drivers.append((pn,out))
    assert len(drivers)==1,(node,bus,net,drivers);src,out=drivers[0];chain.append(dict(src_part=src,src_port=out,dst_part=node,dst_port=bus,actual_top_net=net))
    if src==bname:node=src;bus=out;break
    source=(R/(alltop[src]['module']+'.sv')).read_text();slot=out.removesuffix('_o');regcells=[c for c in cells(source)if c['instance'].startswith('u_ft_'+out+'_')];assert regcells,(src,out)
    first=regcells[0]['pins']['d'];im=re.fullmatch(r'(\w+)\[\d+:0\]',first);assert im,first;ti=P['partition_types'][parts[src]['type']];plan_slot=next((s for s in ti['ft_slots']if s['name']==slot),None);chain[-1]['upstream_transit_stage']=dict(part=src,module=alltop[src]['module'],slot=slot,source_payload_FF_stage_count=len(regcells),source_cells=regcells,planned_stations=plan_slot['stations']if plan_slot else None,planned_fixed_positive_banks=len(plan_slot.get('bit_sites_um',[]))if plan_slot else None,source_vs_plan='MATCH'if plan_slot and len(regcells)==plan_slot['stations']else'MISMATCH_OR_MISSING',home_scope='plan fixed positivebanks; no source-mapped current ODB placement/clock phase')
    node=src;bus=im[1]
   output=bus;src=next(c for c in pcells if c['pins']['q'].startswith(output+'['));ptype=P['partition_types'][parts[bname]['type']];dtyp=P['partition_types'][parts[dest]['type']];pb=next((x for x in ptype['buses']if x['name']==output),None);db=next((x for x in dtyp['buses']if x['name']==port),None)
   entry[kind]=dict(leaf_connection=ex,destination_input=port,destination_capture=bc,source_output=output,source_output_capture=src,source_payload_width=src['width'],planned_source_bus=pb,planned_destination_bus=db,chain=list(reversed(chain)),leaf_input_payload_slice=dict(high=int(v[2]),low=int(v[3])),source_CTL_Q_slice=dict(high=34*g+33 if kind=='c_rq' else 562*g+561,low=34*g if kind=='c_rq' else 562*g),native_source_pin_and_FF_home='Not supplied for exact current source ABI; no actual mapped/fixed boundary FF home inferred')
  forward.append(dict(side=side,quarter=g,source_CTL='u_u_sfucore_Q_ctl',destination_part=dest,destination_native_leaf=f'u_u_sfu_Q{g}',destination_native_module='ot_hgi_sfu_lg_pair_tap_leaf',paths=entry))
res=dict(status='ACTUAL_SOURCE13_REQUEST_LINEAGE_NO_DATE_PRICING',source_top_sha256=hashlib.sha256(top.encode()).hexdigest(),source_CTL_ff=source_ff,request_quarters=forward,summary=dict(Q0='L47 packedrq34+wq562 source596 versus plan664: explicitABI mismatch',Q1='Two directxo/xi native links34/562; absentnamed current typeports/FT',Q2='L731 packed596 through B012L731x1 source6=plan6 thenB002L731x2 source9 versusplan10, thenSU20inputcapture',Q3='Two directxo/xi native links34/562; absentnamed current typeports/FT'),scope='exact source nets/cells/widths/reset roles, no read-return/write-return dates inferred or cycles inserted',holds=['Actual request transport/interface must be reconciled to current source/provider/plan event','L731x2 missing source stage is not automatically a newlypriced cycle if modelalreadyincludes10; exact proposednativeevent must showmatch','L47samebusname doesnotgrant664to596 mapping/padding equivalence','No current nativepin/FFhome/clock/reset physicalqualification or source/default activation'])
(R/'request_lineage.json').write_text(json.dumps(res,indent=2)+'\n');print('QUARTERS',len(forward),'PATHS',2*len(forward))
