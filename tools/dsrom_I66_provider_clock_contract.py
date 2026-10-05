#!/usr/bin/env python3
"""Source-clock/provider and whole-program enrollment contract; no cone run."""
import argparse,hashlib,json
from pathlib import Path
import dsrom_I66_PAR2_calendar_join as J
S=J.S
OUT=S.ROOT/'results/uarch/dsrom_I66_provider_clock_contract_20261002'

def provider_model():
    i=OUT/'inputs';phys=S.load(i/'physical_provider.json');composed=S.load(i/'current_composed.json');cad=S.load(J.OUT/'model.json')
    period=1000/1.2;uncertainty=60
    cfg=phys['PG_via_clock']['source_macro_timing']['CFG']
    rom=phys['PG_via_clock']['source_macro_timing']['ROM']
    return dict(schema='opentallas.dsrom.I66.provider-clock-contract.v1',source_actual_sequence=cad['runtime'],target_clock=dict(stream_period_ps=period,serial_period_ps=1000/.9,setup_uncertainty_ps=60,hold_uncertainty_ps=25,headline_qualified=False),configuration=dict(word_bits=48,local_read_ports_per_shard=2048,local_bits_per_native_edge=98304,word_read_edges=[34,58],word_capture_edges=[35,59],field_go=60,last_capture_to_GO_edges=1,SS_macro_clkq_ps=cfg['SS_clk_to_q_ps'],SS_macro_min_period_ps=cfg['SS_min_period_ps'],remaining_single_edge_before_capture_setup_route_clock_ps=period-uncertainty-cfg['SS_clk_to_q_ps'],FF_macro_clkq_ps=cfg['FF_clk_to_q_ps'],actual_capture_setup_route_skew_ps=None,context_hold_slack_ps=None,context_qualified=False),weight_capture=dict(CE_edges=[85,316],capture_edges=[87,318],lane_edges=[88,319],SS_macro_clkq_ps=rom['SS_clk_to_q_ps'],SS_min_period_ps=rom['SS_min_period_ps'],single_edge_residual_before_setup_route_clock_ps=period-uncertainty-rom['SS_clk_to_q_ps'],native_issue_to_capture_edges=2,native_capture_to_lane_edges=1,do_not_replace_two_edge_source_sequence=True,context_qualified=False),broadcast=dict(source_BST=17,full_bus_bits=sum([1,10,3,1,1,1,8,3,2,256,10,256,10,3,3,1,3,4,32,1024]),actual_active_FP4_payload_and_valid_bits=549,source_registered_pipeline_latency_ps_at_target=17*period,source_fanout_compiled_sites=4096,shards=2,physical_wire_clock_delivery_ps=None,added_pipeline_edges=None,existing_BST_not_free_slack=True),root_and_writer=dict(ports_per_shard=64,root_wire_bits_per_port=69,writer_bits_per_port=63,observed_last_root=419,observed_last_VM_visibility=420,one_edge_budget_before_setup_route_clock_ps=period-uncertainty,physical_dest_home=None,root_FF_clkq_ps=None,transport_ps=None,actual_VM_provider_ps=None,added_edges=None),clock_provider_basis=composed['clock'],context_admission=False,wholeprogram_accepted_I66_origin=None,coll_busy_release=None,ROM_ECC_removed=True,imposed_process_limits=[],enrollment_milestone_publishable=True)

REQUIRED=['edge','pc','st','d_unit','qe_mode','X_ROM','FULL_SHAPE','d_skip','waited','unit_ready','q_gate','kv_gate','m0_gate','win_admit','coll_fault','rope_pf_fault','qe_go','rom_q_go','rom_ready','coll_busy']

def enrollment_gate(provenance):
    """Verify real source and program artifacts before consuming trace callbacks.
    Enrollment proves static identity only; a PASS does not invent runtime.
    """
    i=OUT/'inputs'
    expected=dict(FULL_SHAPE=1,X_ROM=1,ROM_PHW=10,ROM_R=128,ROM_BST=17,logical_NP=4096,NBF=724,ROM_FBW=1632)
    if any(provenance['parameters'].get(k)!=v for k,v in expected.items()):raise ValueError('source/geometry mismatch; PHW6 historical observer cannot bind PHW10')
    binary=Path(provenance['binary_path'])
    if S.sha(binary)!=provenance['binary_sha256']:raise ValueError('binary hash mismatch')
    if provenance['binary_sha256']=='6e2258f81e9d3027157a08a7911c27e848e030621f5659487f9638d63a16e1b3':raise ValueError('known retained PHW6 binary cannot qualify current source')
    compile_record=S.load(Path(provenance['compile_manifest_path']))
    if compile_record['binary_sha256']!=provenance['binary_sha256'] or compile_record['parameters']!=provenance['parameters']:raise ValueError('binary/parameter compile receipt mismatch')
    for key,archive in [('core','core.sv.txt'),('spine','runtime_spine.sv.txt'),('wrapper','runtime_wrapper.sv.txt')]:
        actual=Path(provenance['source_paths'][key])
        if S.sha(actual)!=S.sha(i/archive):raise ValueError('source hash mismatch: '+key)
        if compile_record['source_sha256'][key]!=S.sha(actual):raise ValueError('compiled source mismatch: '+key)
    wanted=S.load(i/'I66_current_patched_word.json')
    verified=[]
    for rank in range(4):
        p=Path(provenance['program_paths'][str(rank)])
        if S.sha(p)!=provenance['program_sha256'][str(rank)]:raise ValueError('program hash mismatch')
        words=[line.strip() for line in p.read_text().splitlines() if line.strip()]
        if len(words)<=66:raise ValueError('program does not contain actual I66')
        word=int(words[66],16)
        if word!=int(wanted['word_hex'],16):raise ValueError('I66 current descriptor mismatch (wbase/stride or other field)')
        directory_arg='+DIR='+str(p.parent)
        if directory_arg not in provenance['enrolled_plusargs'][str(rank)]:raise ValueError('intended program not enrolled in native loader')
        field_arg='+OT_ROM_DIR='+provenance['field_image_paths'][str(rank)]
        if field_arg not in provenance['enrolled_plusargs'][str(rank)]:raise ValueError('field image directory not enrolled separately')
        field_dir=Path(provenance['field_image_paths'][str(rank)])
        for name,h in provenance['field_image_sha256'][str(rank)].items():
            if S.sha(field_dir/name)!=h:raise ValueError('field image hash mismatch')
        for mandatory in ['spine_phase.hex','spine_keys.hex','spine_stream.hex']:
            if mandatory not in provenance['field_image_sha256'][str(rank)]:raise ValueError('missing current field image identity '+mandatory)
        verified.append(dict(rank=rank,program_sha256=S.sha(p),I66_patched_word_sha256=hashlib.sha256(word.to_bytes(256,'little')).hexdigest()))
    return dict(static_identity='PASS',verified_programs=verified,actual_runtime_invoked=False,accepted_origin=None,coll_busy_release=None)

def bind_program_origin(samples,provenance):
    """Require actual adjacent preedge core callback samples, never D1HBM stand-in.
    The existing source issues qe_go by NBA, then the adapter accepts it on the
    following edge. No direct coll_busy predicate exists on normal QE issue.
    Actual callbacks are not present in the isolated I66 cone journal.
    """
    enrollment_gate(provenance)
    for sample in samples:
        missing=set(REQUIRED)-sample.keys()
        if missing:raise ValueError('missing actual callbacks: '+','.join(sorted(missing)))
    found=[]
    for pre,nxt in zip(samples,samples[1:]):
        if not (pre['pc']==66 and pre['st']==6 and pre['d_unit']==3):continue
        if pre['X_ROM']!=1 or pre['FULL_SHAPE']!=1 or pre['qe_mode']!=0:raise ValueError('wrong provider/source selection; D1HBM cannot bind DSROM origin')
        legal=not pre['d_skip'] and not pre['coll_fault'] and not pre['rope_pf_fault'] and all(pre[k] for k in ['waited','unit_ready','q_gate','kv_gate','m0_gate'])
        if not legal:continue
        if nxt['edge']!=pre['edge']+1:raise ValueError('missing next-edge sample')
        if not (nxt['st']==7 and nxt['pc']==66 and nxt['qe_go'] and nxt['rom_q_go'] and nxt['rom_ready']):raise ValueError('registered go/admission identity mismatch')
        found.append(dict(core_issue_edge=pre['edge'],native_adapter_accept_edge=nxt['edge'],coll_busy_at_issue=pre['coll_busy'],coll_busy_is_not_direct_QE_issue_gate=True,conditional_cone_calendar=J.insert_at(S.load(J.OUT/'model.json'),nxt['edge']),actual_coll_busy_release=None,physical_or_fulltoken_credit=False))
    return found

def bind_indexed_read(samples,origin,provider_stage):
    """Actual registered EID response -> exact existing owner table entry.
    No synthetic EID, modulo phase alias, or local-stage fallback on key miss.
    This checks callbacks only; it does not implement cross-stage dispatch.
    """
    node=S.load(J.OUT/'inputs/I66_node_binding.json')
    byedge={x['edge']:x for x in samples}
    read=byedge[origin+1];response=byedge[origin+2]
    if not read['rom_vre'] or read['rom_vaddr']!=node['selector_VM_element_address']:raise ValueError('wrong accepted indexed read')
    eid=response['rom_vq']
    if not 0<=eid<384:raise ValueError('invalid EID; no masked owner alias')
    choice=next(p for p in node['phase_choices'] if p['expert']==eid)
    if provider_stage!=choice['stage']:raise ValueError('runtime owner dispatch missing for selected EID')
    phase=byedge[origin+5]
    if not phase['phase_accept'] or phase['phase']!=choice['phase'] or phase['key_word']!=choice['source_key_word']:raise ValueError('selected phase/key mismatch')
    return dict(EID=eid,read_edge=origin+1,response_sample_edge=origin+2,owner_stage=choice['stage'],phase=choice['phase'],key_word=choice['source_key_word'],accepted_phase_edge=origin+5,actual_dispatch_implementation_qualified=False)

def source_hook_contract():
    core=(OUT/'inputs/core.sv.txt').read_text();die=(OUT/'inputs/die.sv.txt').read_text()
    assert 'wire rom_q_go = qe_go && qe_rom;' in core
    assert "qe_go <= (d_unit == 3'd3)" in core
    assert 'waited && unit_ready && q_gate && kv_gate && m0_gate' in core
    assert 'S_COLL_WAIT: if (!coll_busy)' in core
    assert '.busy(coll_busy), .fault(dma_fault)' in die
    wrapper=(OUT/'inputs/runtime_wrapper.sv.txt').read_text()
    assert '$value$plusargs("DIR=%s", dir)' in wrapper and '$readmemh({dir, "/prog.hex"}, dut.u_tile.prog)' in wrapper
    return dict(required_preedge_fields=REQUIRED,source_clock='native core clk/gclk, identical source/program/shape binding required',pc66='sourcepatchedL0.I66; require programSHA/templatewordSHA and indexedEID provenance from traceowner before adoption',coll_busy_provider='actualdie.u_cdma.busy, not ROMadapteridle',coll_busy_terminal_callbacks=['CDMA mode/topk/GW','vm_we/vm_we4 accepted addresses and masks','postNBA destination words','transpose tr_done/commit_wait or topk tk_done','busy pre/postNBA','collfault/era/seq'],observed_program_origin=None,actual_coll_busy_release=None,fullscheduler_unqualified=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path);p.add_argument('--enrollment',type=Path);p.add_argument('--trace',type=Path);a=p.parse_args()
    if a.enrollment:
        prov=S.load(a.enrollment)
        print(json.dumps(bind_program_origin(S.rows(a.trace),prov) if a.trace else enrollment_gate(prov),indent=2,sort_keys=True))
    else:
        if not a.out:p.error('--out or --enrollment required')
        m=provider_model();m['source_hook_contract']=source_hook_contract();m['input_sha256']={x.name:S.sha(x) for x in sorted((OUT/'inputs').iterdir()) if x.is_file()};a.out.write_text(json.dumps(m,indent=2,sort_keys=True)+'\n')
