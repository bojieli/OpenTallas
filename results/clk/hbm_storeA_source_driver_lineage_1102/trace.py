from pathlib import Path
import re,json,hashlib,collections
R=Path(__file__).resolve().parent;I=Path('/srv/opentallas-scratch/claude/codex-hbm-programme-move-0216/input');C=Path('/srv/opentallas-scratch/claude/wt/codex-hbm-ctl-native-0440/results/hbm_ctl_native_intake_0440/closure_ot_hgi_sfu_core_split3__ctl.sv');closure=C.read_text();ctl=closure.split('endmodule')[0];top=(I/'hbm_arch_B2o_bound_top.sv').read_text();parent=(I/'hbm_arch_q_b113.sv').read_text()
def conns(text):return dict(re.findall(r'\.(\w+)\((.*?)\)(?:,|\s*$)',text,re.S))
def instance(text,mod,inst):
 m=re.search(r'\b'+re.escape(mod)+r'\s+(?:#\([^;]*?\)\s+)?'+re.escape(inst)+r'\s*\((.*?)\);',text,re.S);assert m,(mod,inst);return conns(m[1])
def vector(expr):
 expr=expr.strip()
 if expr.startswith('{')and expr.endswith('}'):return sum((vector(x)for x in expr[1:-1].split(',')),[])
 m=re.fullmatch(r'(\w+)\[(\d+)(?::(\d+))?\]',expr)
 if m:
  a=int(m[2]);b=int(m[3]or m[2]);step=-1 if a>=b else 1;return[(m[1],x)for x in range(a,b+step,step)]
 return[(expr,0)]
store=instance(parent,'ot_hnx_sfu_store_a__da81d76763c9','u_u_sfucore_Q_opstore_a');cp=instance(parent,'ot_hgi_sfu_core_split3__ctl','u_u_sfucore_Q_ctl');assert cp['clk']==store['store0_clk']=='clk'and cp['rst_n']=='rst_n_t22';assert store['store0_rst_n']==cp['u_core_u_rst__rst_n']+'[0]'
for a,b,width in [('store0_sw_d','u_core_u_vm__stage_data',2048),('store0_sw_addr','u_core_u_vm__stage_addr',120),('store0_sw_mask','u_core_u_vm__stage_mask',64)]:assert store[a]==cp[b]+f'[{width-1}:0]'
vm=instance(ctl,'ot_hgi_sfu_vm_static_bridge','m56');assert vm['rst_lg_n']=='{rst_n[0], rst_n[0], rst_n[0], rst_n[0]}'and vm['rst_n']=='{n11363}'
assert "assign stage_mask=64'hffffffffffffffff;"in closure and 'assign stage_v=expect_v&~scalar;'in closure
# Assert exact top net aliases preserve bit ordering through the VM boundary.
assigns=dict((a.strip(),b.strip())for a,b in re.findall(r'assign\s+(.*?)\s*=\s*(.*?);',ctl,re.S))
for a,b,w in [('u_core_u_vm__stage_data','stage_data',2048),('u_core_u_vm__stage_addr','stage_addr',120),('u_core_u_vm__stage_group','stage_group',16),('u_core_u_vm__stage_mask','stage_mask',64),('u_core_u_vm__stage_v','stage_v',8)]:
 vec=list(reversed(vector(vm[b])));assert len(vec)==w
 for j in range(w):assert assigns[f'{a}[{j}]']==vec[j][0],(a,j,vec[j])
local_rr=list(reversed(vector(vm['local_rr'])));qmap=list(reversed(vector(next(k for k,v in assigns.items()if v=='g_compose_m23_q'))));assert local_rr==qmap and len(local_rr)==2056
assert re.search(r'always @\(posedge \{clk\[0\]\} or negedge \{n6\}\)\s*if \(!\{n6\}\) g_compose_m23_q <=',ctl)
for j in range(2056):assert f'u_core_procdff_66926__D[{j}]'in ctl
# Exact five B113 input capture endpoints, then same selected top peer buses.
ports=['xi_u_sfucore_Q_ctl_u_core_procdff_66926_D__2','xi_u_sfucore_Q_ctl_u_core_procdff_66926_D__1','xi_u_sfucore_Q_ctl_u_core_procdff_66926_D__0','L54_i','L127_i'];boundaries={}
for port in ports:
 pattern=r'ot_dp_st\s*#\(\.W\((\d+)\)\)\s+(\w+)\s*\(([^;]*?)\);';matches=[]
 for m in re.finditer(pattern,parent,re.S):
  pins=conns(m[3])
  if pins.get('q')==port+'_q':matches.append((m,pins))
 assert len(matches)==1,port;m,p=matches[0];assert p['clk']=='clk'and p['rst_n']=='rst_n'
 boundaries[port]=dict(instance=m[2],width=int(m[1]),clock=p['clk'],payload_reset='NONE (ot_dp_st q always captures d)',D=p['d'],Q=p['q'],epoch_reset=p['rst_n'],epoch_input=p['ea'],epoch_output=p['eq'])
ctlD=list(reversed(vector(cp['u_core_procdff_66926__D'])));assert len(ctlD)==2056
alltop={}
for m in re.finditer(r'^\s*(hbm_arch_\w+)\s+(?:#\([^;]*?\)\s+)?(\w+)\s*\((.*?)\);',top,re.M|re.S):alltop[m[2]]=dict(module=m[1],pins=conns(m[3]),instantiation_header=m[0][:m.start(3)-m.start()])
peerpaths={}
for side in ['NE','NW']:
 part=alltop[side+'_b113'];assert part['pins']['clk']=='clk_stream'
 for port in ports:
  net=part['pins'][port];peers=[]
  for pn,v in alltop.items():
   if pn==side+'_b113':continue
   for outport,expr in v['pins'].items():
    if expr==net:peers.append((pn,v['module'],outport))
  assert len(peers)==1,(side,port,peers);pn,mod,outport=peers[0];s=(R/(mod+'.sv')).read_text();ms=[]
  for m in re.finditer(r'ot_dp_st\s*#\(\.W\((\d+)\)\)\s+(\w+)\s*\(([^;]*?)\);',s,re.S):
   p=conns(m[3])
   if p.get('q','').startswith(outport+'['):ms.append((m,p))
  assert len(ms)==1,(mod,outport);m,p=ms[0];peerpaths[side+':'+port]=dict(peer_part=pn,peer_module=mod,actual_selected_header=alltop[pn]['instantiation_header'],peer_output=outport,die_net=net,output_capture_instance=m[2],width=int(m[1]),clock=p['clk'],payload_reset='NONE',epoch_reset=p['rst_n'],D=p['d'],Q=p['q'],native_source_before_output_capture='Exact peer native SFU/VMS rr output (not assumed registered/reachable); D expression retained')
data=[]
for i in range(2048):
 j=(i//256)*257+i%256;reg,bit=ctlD[j];port=reg[:-2];assert port in boundaries,(reg,port)
 data.append(dict(StoreA_SW_data_bit=i,source_register='u_u_sfucore_Q_ctl.g_compose_m23_q',source_register_bit=j,source_clock='clk[0] = parent clk = TOP.clk_stream',source_reset='n6 = m55.rst_n[2] generated region2 (not StoreA region1)',enable='NONE; capture every rising edge',D_CTL_input=f'u_core_procdff_66926__D[{j}]',D_parent_boundary_register=reg,D_parent_boundary_bit=bit,earlier_parent_input=port,earlier_peer_paths=[side+':'+port for side in ['NE','NW']]))
metadata=[]
for g in range(4):
 for kind,bits in [('address',range(8,38)),('group',range(38,42)),('expect_v',range(42,44)),('scalar',range(6,8))]:
  for bit in bits:metadata.append(dict(kind=kind,group=g,terminal_Q=f'm56.g_lg[{g}].meta[88][{bit}]',D_previous=f'm56.g_lg[{g}].meta[87][{bit}]',two_prior=f'm56.g_lg[{g}].meta[86][{bit}]',three_prior=f'm56.g_lg[{g}].meta[85][{bit}]',clock=f'clk_lg[{g}] = clk[0] = TOP.clk_stream',reset=f'rst_lg_n[{g}] = CTL delivered rst_n[0] = B113 rst_n_t22',enable='NONE; active branch shifts every edge',reset_kind='asynchronous active-low; terminal state reset0'))
assert len(metadata)==152
vcontrols=[dict(StoreA_port=f'comb{32+b}_A',VM_stage_v_bit=b,expression=f'm56.g_lg[{b//2}].meta[88][{42+b%2}] & ~m56.g_lg[{b//2}].meta[88][{6+b%2}]',registered_driver=False,upstream_state_bits=2)for b in range(8)]
for b in range(8):assert store[f'comb{32+b}_A']==cp['u_core_u_vm__stage_v']+f'[{b}]'
for b in range(8):assert store[f'comb{80+b}_A']==cp['u_core_u_vm__stage_group']+f'[{2*b+1}:{2*b}]'
other=(I/'hbm_arch_q_b113__physical_v1.sv').read_text();os=instance(other,'ot_hnx_sfu_store_a__da81d76763c9','u_u_sfucore_Q_opstore_a');oc=instance(other,'ot_hgi_sfu_core_split3__ctl','u_u_sfucore_Q_ctl')
for key in ['store0_sw_d','store0_sw_addr','store0_sw_mask','store0_clk','store0_rst_n']+[f'comb{b}_A'for b in list(range(32,40))+list(range(80,88))]:assert os[key]==store[key],key
for key in ['clk','rst_n','u_core_procdff_66926__D','u_core_u_vm__stage_data','u_core_u_vm__stage_addr','u_core_u_vm__stage_mask','u_core_u_vm__stage_group','u_core_u_vm__stage_v','u_core_u_rst__rst_n']:assert oc[key]==cp[key],key
sourcefiles=[C,I/'hbm_arch_q_b113.sv',I/'hbm_arch_q_b113__physical_v1.sv',I/'hbm_arch_B2o_bound_top.sv',I/'ot_dp_st.sv',R/'selected_preprocessed.sv']+sorted(R.glob('hbm_arch_q_su*.sv'));manifest=[dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest())for p in sourcefiles]
q25=list(reversed(vector(next(k for k,v in assigns.items()if v=='g_compose_m25_q'))));read_controls=[]
for n,outbit in [('comb128_A',0),('comb144_A',1)]:
 assert store[n]==cp['u_core_procdff_66936__Q']+f'[{outbit}]';net=assigns[f'u_core_procdff_66936__Q[{outbit}]'];regbit=q25.index((net,0));assert regbit==400+outbit
 read_controls.append(dict(StoreA_port=n,CTL_output=f'u_core_procdff_66936__Q[{outbit}]',source_register=f'g_compose_m25_q[{regbit}]',D_CTL_input=f'u_core_procdff_66936__D[{regbit}]',D_parent_capture=f'xi_u_sfucore_Q_ctl_u_core_procdff_66936_D_q[{regbit}]',clock='clk[0]=TOP.clk_stream',reset='n0/m55generatedregion3, distinct from native StoreA region1',enable='NONE',physical_reach='UNQUALIFIED;16-bank target bound only, not ignored'))
res=dict(status='SOURCE_AUTHORITATIVE_LINEAGE_PREP_NO_RTL_CHANGE',source_files=manifest,caller_sha256=hashlib.sha256(parent.encode()).hexdigest(),top_sha256=hashlib.sha256(top.encode()).hexdigest(),physical_variant_caller_sha256=hashlib.sha256(other.encode()).hexdigest(),both_caller_critical_bindings_identical=True,CTL_closure_sha256=hashlib.sha256(closure.encode()).hexdigest(),selected_modules=dict(CTL='u_u_sfucore_Q_ctl',StoreA='u_u_sfucore_Q_opstore_a'),data_lineage=data,additional_16bank_read_controls=read_controls,boundary_stages=boundaries,peer_stage_paths=peerpaths,metadata_terminal_chain=metadata,stage_v_controls=vcontrols,mask=dict(StoreA_port='store0_sw_mask[63:0]',source='VM stage_mask=64hffffffffffffffff',kind='SOURCE_CONSTANT_ALL1',FF_cost=0,hold='Native general-mask ABI may not be silently replaced by ties; requires exact selected caller/source event proof'),prospective_private_copy_model=dict(strict_existing_Q_copy_state_per_complete_region=2200,breakdown=dict(data=2048,address=120,group=16,expect_scalar=16),local_combinational_ANDs_per_region=8,constant_mask_outputs=64,new_cycles='NONE ASSUMED; same-edge equality must be proved',stage_relocation_options=['Data last3 existing stages: peer u_bout payload FF -> B113 u_bin payload FF -> CTL g_compose_m23_q','Metadata last3 existing stages: meta[86] ->meta[87] ->meta[88] (meta85 also available)'],earlier_stage_cost='Conditional per regional copy: additional2048 resetless payloadFF for each cloned peer/boundary data stage, additional152 async-reset metadataFF for each cloned earlier metadata stage; no originals removed/allused outputs preserved',new_native_port_obligations=['Expose exact rawD data2048 and previous-meta152 signals at chosen split, never a dummyQ alias','Retain exact generated-region2 data reset and deliveredt22 metadata reset as distinct native input roles; existing StoreA region1 reset is insufficient','Exact mapped current clock roots/phase and physical inputs+fanout clock load for every regional copy','Explicit source/model/provider ABI and keep/dont_touch replication identity so synthesis cannot merge physical copies']),holds=['No source modifications/build/proof/placement or clone region count selected','All D sources and earlier peer native endpoints still require coherent physical reach/clock/reset qualification','Same-edge copy does not make D free; last2–3 existing stages may need distributed replicated placement','Original used outputs/epoch companion behavior and warm/reset protocol must remain bit-exact','Constant-folding mask needs selected caller source qualification; no general native ABI assumption'])
(R/'source_lineage.json').write_text(json.dumps(res,indent=2)+'\n');print('DATA',len(data),'METADATA',len(metadata),'BOUNDARY',len(boundaries),'PEERPATHS',len(peerpaths))
