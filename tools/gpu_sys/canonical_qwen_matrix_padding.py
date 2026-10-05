"""Source-only canonical-zero proof and exact64-leaf MATRIX successor.

Original refusal/implementation files remain unchanged. This admits lowering,
not execution/physical qualification; no numerical oracle or inference runs.
"""
from dataclasses import dataclass,asdict
from tools.gpu_sys import canonical_qwen_matrix_loop as M
from tools.gpu_sys import canonical_qwen_service_calendar as C

PROOF_SOURCES=(C.SOURCE,'rtl/hdc/ot_hdc_fp32_add_lat.sv','rtl/hdc/ot_hdc_fpu.sv',
 'rtl/gpu/ot_gpu_sm_q.sv','rtl/gpu/ot_gpu_tc_col.sv','rtl/gpu/ot_gpu_tree.sv')


def padding_proof(root=C.ROOT):
    raw=(root/C.SOURCE).read_bytes();C.need(C.sha(raw)==C.SOURCE_SHA,'original870 canonical-zero source')
    source=raw.decode();adder=(root/PROOF_SOURCES[1]).read_text()
    mul=(root/PROOF_SOURCES[2]).read_text();sm=(root/PROOF_SOURCES[3]).read_text()
    # Bind the actual branches used by the argument, not a generic IEEE
    # assertion. The value domain is every fault-free canonical finite FP32.
    for marker in ("at.get('canonical_zero',True)","v=poszero(v)","acc=np.zeros(rn,F)"):
        C.need(marker in source,'source zero invariant '+marker)
    for marker in ('wire bypass = nonfinite || a_zero || b_zero;',
        "nonfinite ? 32'd0 : (a_zero ? (b_zero ? 32'd0 : b) : a)",
        "else if (over) begin y <= 32'd0; err <= E_OVERFLOW; end",
        "(code[30:0] == 31'd0) ? 32'd0 : code"):
        C.need(marker in adder,'selected adder zero/fault invariant '+marker)
    C.need("if (s3_z && !s3_nf) s4_y <= 32'd0;" in mul and "(m == 8'd0) ? 16'd0" in sm,
           'inactive code/x exact positive-zero product')
    return dict(schema='QWEN_SPLIT64_CANONICAL_ZERO_SOURCE_PROOF_R1',
        source_pins={p:C.sha((root/p).read_bytes()) for p in PROOF_SOURCES},
        original='64 consecutive contiguous-K sums, pairwise tree in source leaf order',
        constructed='same first64leaves; last64leaves code=0/x=+0; unchanged default128leaf engine',
        invariant='every accepted source FADD result is finite and canonical +0 when zero',
        adder_specialization=dict(b=0,nonfinite=False,b_zero=True,
            bypass=True,result='0 if a_zero else a',equals_canonical_finite_a=True),
        tree='right64-leaf subtree is +0; left64 subtree unchanged; final add(left,+0) bit-identical',
        fault='original active faults remain ORed; inactive zero lanes create no fault; no faulty result is admitted',
        extra_pipeline_edges=7,source_arithmetic_reordered=False,
        source_correctness=True,numerical_waveform_PASS=False,physical_admission=False)


@dataclass(frozen=True)
class PaddedMatrixTile(M.MatrixTile):
    padding_proof_sha256:str
    @property
    def line_count(self):return self.rows*self.groups*self.chunk
    @property
    def fragments(self):return self.groups*self.chunk
    def _indices(self,group,step):
        return tuple((group*128+l)*self.chunk+step if group*128+l<self.split else None for l in range(128))
    def line(self,index):
        C.need(type(index) is int and 0<=index<self.line_count,'padded line aperture')
        address=index;block,index=divmod(index,self.groups*self.chunk*8)
        group,index=divmod(index,self.chunk*8);step,slot=divmod(index,8)
        row=self.row_start+block*8+slot;ks=self._indices(group,step)
        return dict(line_address=address,source_row=row,source_K_indices=ks,
            source_code_byte_offsets=tuple(None if k is None else row*self.K+k for k in ks),
            dtype='I8',bytes=128,weight_key=self.weight_key,source_PC=self.source_PC,rank=self.weight_rank,
            inactive_lanes=tuple(i for i,k in enumerate(ks) if k is None),padding_proof_sha256=self.padding_proof_sha256)
    def x_fragment(self,index):
        C.need(type(index) is int and 0<=index<self.fragments,'padded fragment aperture')
        group,step=divmod(index,self.chunk)
        return dict(fragment=index,input_version=self.input_version,source_K_indices=self._indices(group,step),
            source_rounding='original bf16 recipe',dtype='BF16',columns=16,bytes=4096,
            layout='column-major; identical128-leaf source vector in each of16columns',
            padding_proof_sha256=self.padding_proof_sha256)


def lower_matrix(native,source_PC,*,enabled=False):
    C.need(enabled,'complete MATRIX lowering default off')
    C.need(C.sha(C.canonical(native))==C.PROGRAM_SHA,'exact canonical1737')
    C.need(type(source_PC) is int and 0<=source_PC<1737,'source PC aperture')
    return _lower_verified(native,source_PC,padding_proof())


def _lower_verified(native,pc,proof):
    op=native['operations'][pc];C.need(op['opcode']=='MATRIX','actual MATRIX only')
    d=native['source_program']['weight_descriptors'][op['attributes']['weight']]
    if d['split']!=64:return M._lower_verified(native,pc)
    K,R=d['K'],d['rows'];C.need(K%64==0 and R%8==0 and (K//64)*8<=1024,'existing padded engine aperture')
    recipes={k:native['microcode'][k] for k in ('bf16','convert','mul','add')}
    C.need('"canonical_zero": false' not in C.canonical(recipes).decode(),'source add canonical-zero contract')
    return tuple(PaddedMatrixTile(C.PROGRAM_SHA,pc,d['key'],d['die'],op['reads'][0],op['writes'][0],
        tuple(d['checkpoint_sources']),r,min(128,R-r),K,64,K//64,1,C.sha(C.canonical(d)),
        C.sha(C.canonical(recipes)),C.sha(C.canonical(proof))) for r in range(0,R,128))


class MatrixOperatorController(M.MatrixOperatorController):
    def __init__(self,pins,services,native,source_PC,*,enabled=False):
        self.tiles=lower_matrix(native,source_PC,enabled=enabled)
        C.need(all(callable(getattr(services,k,None)) for k in
            ('begin_operator','whole_completion','release_operator')),'actual whole issuer services')
        self.p=pins;self.s=services;self.index=0;self.tile=None;self.origin=None;self.phase='begin'


def price_tiles(tiles,calls):
    # Old model function assumes128active leaves. Preserve it; successor
    # enumerates inactive lanes and the extra source64 padding stages.
    sample=tiles[0];groups=sample.groups;chunk=sample.chunk
    result=M.price_tiles(tiles,calls) if sample.split!=64 else M.price_tiles(
        [M.MatrixTile(**{k:v for k,v in asdict(t).items() if k!='padding_proof_sha256'}) for t in tiles],calls)
    result.update(weight_line_requests=sum(t.line_count for t in tiles),
        xstore_write_beats=sum(t.fragments*16 for t in tiles),
        issue_edges_no_stalls=sum(t.rows*t.groups*t.chunk for t in tiles),
        uncached_gather_code_sector_reads32=sum(t.rows*sum(len({k//32 for k in t.x_fragment(f)['source_K_indices'] if k is not None})
            for f in range(t.fragments)) for t in tiles),
        padded_extra_pipeline_edges_per_tile=7 if sample.split==64 else 0,
        active_source_MACs_per_issue=min(128,sample.split),useful_source_MACs_per_issue=min(128,sample.split),
        gather_live_line_credits=1,gather_host_rounding=False,
        capture='actual64B scratch transactions; actual RF mirror write/commonACK; protected storage qualification remains unknown')
    result['local_serial_preload_and_issue_floor_edges']=result['xstore_write_beats']+result['issue_edges_no_stalls']
    return result


def compose(native):
    import ast,math
    proof=padding_proof();C.need(C.sha(C.canonical(native))==C.PROGRAM_SHA,'complete1737 identity')
    counts=C.source_demands(native,8191,C.counting_functions((C.ROOT/C.SOURCE).read_bytes()))
    rows=[]
    for op in native['operations']:
        if op['opcode']!='MATRIX':continue
        tiles=_lower_verified(native,op['pc'],proof)
        model=price_tiles(tiles,sum(counts[op['pc']]['native_units'].values()))
        sectors=model['uncached_gather_code_sector_reads32'];nr=sum(t.rows for t in tiles)
        # Phase durations may overlap: gather and internal issue run together.
        # Scratch reread/RFcommit run only AFTER all actual result rows.
        model['finite_service_calendar']=dict(
            host_numeric_operations=0,one_live_gather_line=1,one_live_W2_sector=1,
            W2_sequential_capture_reverse_floor_edges=3*sectors,
            scratch_result_write_floor_edges=2*nr,scratch_result_readback_floor_edges=3*nr,
            RF_write_and_ACK_floor_edges=2*len(tiles),
            exclusive_local_protocol_floor_edges=model['xstore_write_beats']+
                max(model['issue_edges_no_stalls'],3*sectors,2*nr)+3*nr+2*len(tiles),
            weight_consumption='actual engine handshake required before next line, never elapsed completion',
            W2_measured_II19='additional max recurrence on each actual rank/PC/client; no guessed route or19per-request RTT sum',
            exposed_operator_duration_ps=None,route_and_backend_RTT_edges=None,
            actual_GO_and_allpage_ACK_terminal_reverse_edges=None,
            source_RF_lease_retirement='never a tile/issuer-frame completion event')
        rows.append(dict(source_PC=op['pc'],tile_count=len(tiles),weight_rank=tiles[0].weight_rank,
            first_tile=tiles[0].record(),model=model))
    # This is a prospective hardware equivalent of the transport byte splice,
    # NOT a claim the Python buffer is protected ASIC storage or routed logic.
    fields=dict(payload=1024,lane_seen=128,internal_tag=10,line_address=32,
                GO=239,owner55=55,source_addr=34,source_tag=32,source_gen=4,
                rank=1,PC=7,client=3,phase=3)
    raw_bits=sum(fields.values());coded_bits=math.ceil(raw_bits/64)*72
    text=(C.ROOT/'tools/uarch_model.py').read_text();tree=ast.parse(text)
    dff=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign)
             and any(isinstance(t,ast.Name) and t.id=='DFF_UM2' for t in n.targets))
    known_cell=coded_bits*dff
    muxes=128*8*31;assumed_mux_area=muxes*0.2
    paths=set(M.SOURCES+PROOF_SOURCES+(C.PROGRAM,C.SOURCE,
        'tools/uarch_model.py','tools/gpu_sys/canonical_qwen_service_calendar.py',
        'tools/gpu_sys/canonical_qwen_matrix_loop.py','tools/gpu_sys/canonical_qwen_matrix_padding.py',
        'tools/gpu_sys/canonical_qwen_matrix_services.py','tools/gpu_sys/test_canonical_qwen_matrix_padding_services.py',
        'tools/gpu_sys/canonical_qwen_transport.py','tools/gpu_sys/canonical_qwen_rf_ports.py',
        'results/uarch/Euclid_W4_RFACK_identity_contract_20261003/selfcontained-peer-r10/design/ot_gpu_scratch_service.sv'))
    return dict(schema='QWEN_MATRIX_ALL290_FINITE_SERVICES_SOURCE_R1',proof=proof,
        operations=rows,source_MATRIX_PCs=len(rows),complete_source_PC_count=1737,
        split64_PCs=sum(r['first_tile']['split']==64 for r in rows),
        source_MATRIX_primitive_calls=sum(r['model']['baseline_primitive_host_calls'] for r in rows),
        whole_loop_tile_commands_if_enrolled=sum(r['tile_count'] for r in rows),
        no_source_arithmetic_removed=True,EXP_reduction_order_changed=False,
        once_only_resources=dict(existing_scratch_macros_total=64,additional_scratch_macros=0,
            per_active_worker_result_scratch_bytes=8192,actual_exclusive_scratch_lease_required=True,
            existing_engine_ring_and_xstore='reuse source engine slot; no additional global engine selected',
            new_replica_count=None,installed_engine_count=None),
        prospective_hardware_gather=dict(fields=fields,raw_bits=raw_bits,SECDED64plus8_bits=coded_bits,
            retained_cell_lower_bound_um2=known_cell,DFF_unit_area_um2=dff,
            byte_select_mux2_count_upper_estimate=muxes,
            mux_cell_area_um2_assumed=assumed_mux_area,
            register_plus_mux_estimate_um2=known_cell+assumed_mux_area,
            per_worker_placement_estimate_um2_at50pct=2*(known_cell+assumed_mux_area),
            basis='source-pinned DFF0.2916um2; ASSUMED0.2um2/mux2bit; excludes decode/comparator/clock/wires',
            construction='host transport splice implements actual captured bytes; hardware splice/protection not installed',
            boundary_bits=dict(W2_capture=256,engine_response=1024,scratch=512,RF=4096,whole_GO=239,owner=55),
            track_capacity=None,route_length_and_slew=None,clock_reset_and_source_slot_fit=None),
        qualification=dict(source_padding_proof=True,finite_port_transactors_implemented=True,
            actual_connected_engine_run=False,SS_FF=False,physical_admission=False,
            mutable_scratch_capture_protection=False,
            missing='Euclid engine/consume tap +Nash physical input/output/workspace allocator and all-page ACK observer; actual BF16 capture; protected scratch/gather implementation and source-fit/route/corner proof'),
        source_pins={p:C.sha((C.ROOT/p).read_bytes()) for p in sorted(paths)},
        source_RF_lease_lifetime='input/output leases remain hardware-owned until declared last consumer, never workspace or wholeissuer retirement',
        actual_token_latency_ps=None,single_user_tokens_s=None,
        API='MatrixOperatorController(real_engine_pins,MatrixPhysicalServices(actual_authority,scratch_pins,enabled=True),native,PC,enabled=True).step(); attach service as one shared-clock edge hook')


if __name__=='__main__':
    import argparse
    from pathlib import Path
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',required=True,type=Path)
    parser.add_argument('--verify',action='store_true');args=parser.parse_args()
    raw=C.canonical(compose(C.read(C.ROOT/C.PROGRAM)))
    if args.verify:C.need(args.out.read_bytes()==raw,'cold complete MATRIX source/finite-service equality')
    else:
        C.need(not args.out.exists(),'preserve frozen matrix evidence');args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_bytes(raw)
