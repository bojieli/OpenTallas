#!/usr/bin/env python3
"""Read-only actual VM source clock-path census; no elaboration/physical claim.
Snapshots source bytes, all sequential owner boundaries and proposed outer root
vector indices. Existing phase-related source ports remain scalar-tied at top.
"""
import argparse,collections,hashlib,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools'))
import die_port_bind as D

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--source-root',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
 assert not a.out.exists(),'use immutable fresh output directory'
 files={p.name:p.read_text() for p in a.source_root.glob('*.sv')}
 mods={}
 for name,text in files.items():
  for m in D.parse_modules(text,name):mods[m.name]=(name,m)
 eps=[]
 def add(cat,path,mod,pin,domain,reset,upstream,notes='',params=None,reset_kind='async low, local2floprelease then valid/control reset'):
  name,m=mods[mod];assert pin in m.ports,(mod,pin)
  eps.append(dict(category=cat,instance=path,module=mod,source=name,clock_pin=pin,domain=domain,reset_consumer=reset,reset_kind=reset_kind,current_outer_clock='cks[0]' if domain=='stream' else 'ck[0]',current_upstream_connection=upstream,notes=notes,parameters=params or {},native_delivery_status='NOT_IMPLEMENTED_AT_OUTER_PORT_SCALAR_TIE',source_sha256=hashlib.sha256(files[name].encode()).hexdigest()))
 base='dsfd_sp_vm.u_core.u_mem'
 # 328 actual memory leaves; 48 of them have request and response root pins.
 for s in range(4):
  sp=f'{base}.slice[{s}].u_slice'
  for b in range(32):add('memory_bank',f'{sp}.bank[{b}].u_bank','dsfd_vm_static_bank128','ck','stream','rst_n <- rss','u_core.u_mem.ck_bank[32*s+b] <- {128{ck}}',notes='Includes internal u_sram.clk on same bank root; not an additional delivery root.')
 for pin in ['ck_req','ck_rsp']:
  for s in range(4):
   sp=f'{base}.slice[{s}].u_slice'
   for kind,num,offset,master in [('bridge',4,0,'dsfd_vm_static_relay128_b8'),('quarter',8,4,'dsfd_vm_static_relay128_b4')]:
    for g in range(num):add('memory_relay_'+('req' if pin=='ck_req' else 'rsp'),f'{sp}.{kind}[{g}].u_hop',master,pin,'stream','rst_n <- rss',f'u_mem.ck_relay_{"req" if pin=="ck_req" else "rsp"}[12*{s}+{g+offset}] <- {{48{{ck}}}}',notes='Wrapper forwards root to u_relay.'+pin+'; shared raw rst_n, independent req/rsp two-flop release.')
 for s in range(4):add('memory_read_fsr',f'{base}.slice[{s}].u_slice.u_r','dsfd_vm_static_suhc_fsr','ck','stream','rst_n <- rss',f'u_mem.ck_rscatter[{s}] <- {{4{{ck}}}}')
 for s in range(4):add('memory_return',f'{base}.slice[{s}].u_return','dsfd_vm_static_return','ck','stream','rst_n <- rss',f'u_mem.ck_return[{s}] <- {{4{{ck}}}}',params={'NROW':32})
 for s in range(4):
  for q in range(4):
   for b in range(8):add('memory_write_capture',f'{base}.slice[{s}].u_slice.write_group[{q}].capture[{b}].u_capture','dsfd_vm_static_write_capture128','ck','stream','rst_n <- rss',f'u_mem.ck_wcapture[{32*s+8*q+b}] <- {{128{{ck}}}}')
 for s in range(4):
  for q in range(4):add('memory_b8_scatter_out',f'{base}.slice[{s}].u_slice.write_group[{q}].u_w','dsfd_vm_static_scatter_b8_out','ck','stream','rst_n <- rss',f'u_mem.ck_wscatter[{4*s+q}] <- {{16{{ck}}}}',params={'BANK_BASE':8*q})
 assert len(eps)==376
 ws='dsfd_sp_vm.u_core.u_ws'
 add('write_control',ws+'.u_control','dsfd_vm_static_wcontrol','ck_control','stream','rst_n <- rss','u_ws.ck_control <- ck')
 add('write_header',ws+'.u_header','dsfd_vm_static_w0_header','ck','stream','rst_n <- rss','u_ws.ck_header <- ck',params={'NSRC':53})
 for s in range(4):add('write_payload',f'{ws}.w0_payload[{s}].u_payload','dsfd_vm_static_w0_payload','ck','stream','rst_n <- rss',f'u_ws.ck_payload[{s}] <- {{4{{ck}}}}',params={'NSRC':53})
 for s in range(4):
  for q in range(4):add('write_dispatch',f'{ws}.slice[{s}].quarter[{q}].u_d','dsfd_vm_static_wdispatch128','ck','stream','rst_n <- rss',f'u_ws.ck_dispatch[{4*s+q}] <- {{16{{ck}}}}',params={'NSRC':53,'NBANK':8,'BANK_BASE':8*q})
 for s in range(4):
  for b in range(32):add('write_storage',f'{ws}.slice[{s}].bank[{b}].u_w','dsfd_vm_static_wstage128','ck','stream','rst_n <- rss',f'u_ws.ck_stage[{32*s+b}] <- {{128{{ck}}}}',params={'DEPTH':3})
 assert len(eps)==526
 add('core_direct_control_and_outputs','dsfd_sp_vm.u_core','dsfd_vm_static_core','cks','stream','rss','u_core.cks <- cks[0]',notes='UNHARDENED parent:25600declared outputdataFF +47valid+14control=25661. Target split50row roots; this endpoint becomes residual15FFcontrol.',reset_kind='rss async to rr2; rn resets valids/control; dataFF unreset')
 for inst,mod,rpin in [('u_rs','dsfd_vm_static_rsched','rst_n'),('u_seq','dsfd_vm_seq_static','rst'),('u_land','dsfd_vm_static_landing','rst_n')]:add('core_'+inst,'dsfd_sp_vm.u_core.'+inst,mod,'ck','stream',rpin+' <- rss','u_core.ck=cks',notes='Real source module; native physical hardening/own root delivery not proved.',params={'NSLOT':8,'VQD':8} if inst=='u_seq' else {})
 add('shell_control','dsfd_sp_vm','dsfd_sp_vm','cks','stream','rss[0]','cks[0]',notes='UNHARDENED wrapper owns p_bad/e_flt two async-reset stickyFF. Must move to actual shellcontrolleaf.',reset_kind='direct async low rss; no local two-floprelease in this parent')
 for inst,mod in [('u_wfc','dsfd_vm_static_wfc'),('u_xio','dsfd_vm_static_xio')]:add('edge_direct_control','dsfd_sp_vm.'+inst,mod,'cks','stream','rss','cks[0]',notes='UNHARDENED dual-domain parent: direct stream decode/metadata/return/assertionFF need real hardleaf boundary.')
 # Serial owner boundaries:16 assembly leaves plus capture/WFC/XIO parent controls.
 for g in range(16):add('capture_assembly',f'dsfd_sp_vm.u_cap.lane[{g}].u_l','dsfd_vm_static_cap_leaf','ck','serial','rn <- u_cap.rq[1] <- rst[0]','u_cap.ck <- ck[0]',notes='Hard lane includes inner capl.ck on same root. rn is parent-generated synchronous release, NOT raw rst_n.',params={'E':8},reset_kind='synchronous rn from capturecontrol root; no local async reset-release in capleaf')
 add('capture_control','dsfd_sp_vm.u_cap','dsfd_vm_static_cap','ck','serial','rst','ck[0]',notes='UNHARDENED captureparent owns rq2,status_q64,dr_q/armed/s_flt3=69declaredFF; shared rn/flush fanout16lanes.')
 for inst,mod in [('u_wfc','dsfd_vm_static_wfc'),('u_xio','dsfd_vm_static_xio')]:add('edge_direct_control','dsfd_sp_vm.'+inst,mod,'ck','serial','rst','ck[0]',notes='UNHARDENED parent serial output/status/assertionFF; separate from x43 serial roots.')
 cdc34=[(f'dsfd_sp_vm.u_cap.lane[{g}].u_x',542) for g in range(16)]+[('dsfd_sp_vm.u_xsel',514),('dsfd_sp_vm.u_xcol',514),('dsfd_sp_vm.u_xsw',1026),('dsfd_sp_vm.u_wfc.u_xi',560)]
 cdc43=[('dsfd_sp_vm.u_wfc.u_xo',1026),('dsfd_sp_vm.u_xio.u_xq',512),('dsfd_sp_vm.u_xio.u_xg',511)]
 for paths,mod,cat in [(cdc34,'ot_s81_vm_x34','x34'),(cdc43,'ot_s81_vm_x43','x43')]:
  for path,width in paths:
   for pin,domain,rpin in [('t_ck','stream','t_rst_n'),('s_ck','serial','s_rst_n')]:add(cat,path,mod,pin,domain,rpin+(' <- rss' if domain=='stream' else ' <- rst'),'cks[0]' if domain=='stream' else 'ck[0]',params={'W':width},notes='Real dual-domain related-clock storage; two independent native roots required, not asynchronous clocks. Native hardening/phase-specific STA still OPEN.',reset_kind='direct async epoch reset; phase counters start on FIRST local edge, no two-floprelease in x34/x43')
 actual=collections.Counter(e['domain'] for e in eps);assert actual==dict(stream=556,serial=42),actual
 indices=collections.Counter()
 for e in eps:
  d=e['domain'];e['proposed_outer_clock_pin']=f'ck_vm_{"t" if d=="stream" else "s"}[{indices[d]}]';indices[d]+=1
 outputs=[]
 for kind,count,out,rhs,v,extra in [('su',16,'t_su_rs','nat_d','t_su_rsv','nat_v[p]'),('hc',2,'t_hc_rs','nat_d','t_hc_rsv','nat_v[16+p]'),('pq',4,'t_pqx','grp_d','t_pqx[0]','oneSHAREDvalidfrom aux_exp[0] and grp_v20/52/84/116'),('edge',8,'x_rd','grp_d','x_rv','aux_exp[4+p] and four slice grp_v[24+p+32*s]'),('mix',20,'t_mx_rs','grp_d','t_mx_rsv','mx_exp[p]')]:
  for p in range(count):
   outoff=512*p+(1 if kind=='pq' else 0)
   srcoff=512*(p+(16 if kind=='hc' else 20 if kind=='pq' else 24 if kind=='edge' else 0))
   row=dict(group=kind,row=p,current_instance='dsfd_sp_vm.u_core',clock='cks via ck alias',output_data=f'{out}[{outoff} +: 512]',data_ff_bits=512,valid_register=f'{v}[{p}]' if kind not in ['pq'] else 't_pqx[0] SHARED in residualcontrol',valid_ff_bits=0 if kind=='pq' else 1,current_rhs=f'{rhs}[{srcoff} +: 512]',valid_rhs=extra,native_leaf_status='REQUIRED_NOT_IMPLEMENTED',proposed_outer_clock_pin=f'ck_vm_t[{indices["stream"]}]',age='Existing P+12 outputregister; partition must move sameFF without newstage',leaf_pin_fit='Needs actual data/valid/selector pins; no86.4squarefit claimed')
   if kind=='mix':row.update(current_rhs=f'grp_d[512*mx_sl[{5*p} +: 5] +: 512]',selector='mx_sl = rsched.dxs[11]',source_expression_mux_rows=32,valid_profile_group=(p//4 if p<16 else 5),valid_profile_rows=list(range(4*(p//4 if p<16 else 5),4*(p//4 if p<16 else 5)+4)),profile_fanin_data_bits=2048,profile_select_bits=2,ownership_gap='Cannot claim512input leaf while leaving4:1x512mux in wiresparent. Harden selector with actual2048inputs, or assign existing selectionlogic to separate realboundary; no cyclechange inferred.')
   outputs.append(row);indices['stream']+=1
 assert len(outputs)==50 and indices==dict(stream=606,serial=42)
 snapshots={name:dict(sha256=hashlib.sha256(text.encode()).hexdigest(),text=text) for name,text in files.items() if any(e['source']==name for e in eps) or name in ['dsfd_vm_static_slice128_suhc.sv','dsfd_vm_static512_suhc.sv','dsfd_vm_static_relay128.sv','dsfd_vm_static_capl.sv']}
 result=dict(schema='opentallas.s81.vm-native-outer-clock-abi-audit.v1',status='READ_ONLY_SOURCE_CENSUS_OUTER_ABI_NOT_IMPLEMENTED_OR_PHYSICALLY_QUALIFIED',source_root=str(a.source_root),source_basis='Actual direct-write memory b5f79878e + actual150root writeedge275ea7a11, read from ownercurrenttree; exact consumed snapshot hashes recorded, not an assertion onecommit contains hybrid.',as_built=dict(outer_clock_ports=['ck[0]','cks[0]'],outer_resets=['rst[0]','rss[0]'],clock_endpoints=len(eps),stream=actual['stream'],serial=actual['serial'],distinct_sequential_owner_boundaries=len({e['instance'] for e in eps}),memory_leaf_instances=328,memory_roots=376,write_edge_leaf_instances=150,write_edge_roots=150,all_clock_delivery='Scalar2outerports fanout everylisted boundary; countedports do NOT prove independent native delivery.'),proposed_outer_abi=dict(status='PROPOSAL_UNIMPLEMENTED_PENDING_S_BIND',clock_inputs=[dict(name='ck_vm_t',width=606,domain='stream',nominal_period_ps=1000/1.2),dict(name='ck_vm_s',width=42,domain='serial',nominal_period_ps=1000/.9)],reset_inputs=[dict(name='rss',width=1,domain='stream',polarity='active_low'),dict(name='rst',width=1,domain='serial',polarity='active_low')],total_clock_roots=648,implemented_inner_root_subset=526,not_implemented_extra_row_output_roots=50,other_current_clock_endpoints=72,pll='Singlephase-locked PLL/commondivider; stream=PLL/3,serial=PLL/4 ifPLL3.6GHz; exactly4stream=3serial edges percommon3333.333ps epoch.',delivery_rule='For EACH leafclockpin/domain,arrival_phi = compiler_domain_phase+stage_phase. Deliver parententryphase phi-R using that actual rootcorner insertionR. Each phase/root/reset path must be independently verified at nativepins; no scalarclocktie counts asdelivery.',reset_rule='Keep two logical epochresets. Asyncassert; deassert such that localfirstedges obeycommon3:4epoch and existinglocalrelease depth. x34/x43 startphaseonfirstedge; capleafrn currentlygenerated bycapcontrolrq2 and requires timing toleafclk; never silently replace rn withrawreset/addcycles.',constraints='Relatedclock STA for x34/x43 bank arcs and phase/reset checks. No asynchronous clockgroups/blanketfalsepaths between serial/stream. Any functional multicycle must derive exact implemented bankselection arcs and retain holdchecks; no exception introduced by this audit.'),endpoints=eps,proposed_row_output_partitions=outputs,unhardened_parent_state=[dict(instance='dsfd_sp_vm',state='p_bad,e_flt',domain='stream',declared_bits=2),dict(instance='dsfd_sp_vm.u_core',state='25600data+47valid+14control',domain='stream',declared_bits=25661,nonmix_data_bits=15360,qualification='Source declaration count only; fullshapeincludingMIX exceeds15k and evennonMIXdata alone15360>15k. Split50rowoutputs plusresidual15FFcontrol; pinownership/selectionlogic must be real.'),dict(instance='dsfd_sp_vm.u_cap',state='rq2,status_q64,dr_q,armed,s_flt',domain='serial',declared_bits=69),dict(instance='dsfd_sp_vm.u_wfc',state='streamdecode/metadata/return;serialstatus',domains=['stream','serial']),dict(instance='dsfd_sp_vm.u_xio',state='streamrowissue/return/gathermirror;serialscanstatus',domains=['stream','serial'])],combinational_boundaries_without_clock=[dict(module='dsfd_vm_static_suhc_return_map',instances=4,clock_roots=0,qualification='Realcombinationalreturnselection; clockcensuscannotqualify pin/reach/timing or allowunownedlogicinwiresparent.')],required_before_native_claim=['Expose/route nativeouterrootABI through wrapper/core/cap/WFC/XIO and allCDCports','Actuallypartition/harden parentcontrol/state and50outputrows; no newtimingage without compilerchange','Source-bound mappedFF/pins/rootCTS/insertion/TTFFDRC0/rootresetproof for eachrealhardleaf','Exact3:4epochbankarcs/resetreleaseandnativefaceIOpaths; no genericclock waiver','Fullcanonical2417/BF519/PHW10 geometry, compilerproductioncalendarandthroughput'])
 a.out.mkdir(parents=True);(a.out/'audit.json').write_text(json.dumps(result,indent=2)+'\n');(a.out/'source_snapshot.json').write_text(json.dumps(snapshots,indent=2)+'\n')
 print(json.dumps(dict(as_built=result['as_built'],proposed_roots=648,proposed_stream=606,proposed_serial=42,output_rows=len(outputs),sources=len(snapshots)),indent=2))
if __name__=='__main__':main()
