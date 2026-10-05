#!/usr/bin/env python3
"""ROM PART2 source-bound finite VM proposal, not a hardware grant provider.

Maxwell hook: proposal(root). Compiler hook: compile_frame(reads, writes).
Inputs are literal enabled PRE-edge requests in source order. No activations,
inference, source clock changes, image generation, or authority allocation.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from hdc_isa import decode
from qwen_hbm_activation_vm_realization import physical_address

BOOK = Path('results/rtl/qwen_rom_finite_vm_schedule_20261005')
PINS = {
    'top.sv': '3d5cb792affee962d4f7cd07fc4aaae38cc1d5710d1e39d09201c1ff4790fe81',
    'core.sv': '59492b0f4a1c46b86298fbda105d2c79f2db10ac76fde15f74509099e9a6f97e',
    'array.sv': 'cba4d82b66b9560447650e7e4f96ea0662391319efc0d6311bab80d95d9857c5',
    'part.sv': '2918fc95a2d7bf61f334143dc5682c77398d0c91d5da2970e4989daee41649eb',
    'top.args.f': '3f594f557fe8261053f73a8130e411d534f517c62c7209ce7d068c7cd2fee2de',
}
READ_ORDER = ('VA', 'VB', 'VC', 'COLLECTIVE', 'VX')
WRITE_ORDER = ('ME', 'MX', 'SU', 'REDUCER', 'COLLECTIVE')


def compile_frame(reads, writes):
    """Finite source-order table for one *already captured* native edge.

    Each input has source, seat and scalar address. Enabled requests only.
    Caller owns job/rank/epoch and grants; this function does not create them.
    Writes carry no data here: this is address/mask costing, never an oracle.
    """
    rlimit = dict(VA=64, VB=64, VC=64, COLLECTIVE=16, VX=2048)
    wlimit = dict(ME=768, MX=16, SU=64, REDUCER=1, COLLECTIVE=16)
    for rows, order, limits in ((reads, READ_ORDER, rlimit), (writes, WRITE_ORDER, wlimit)):
        last = (-1, -1)
        for r in rows:
            source, seat = r['source'], r['seat']
            if type(seat) is not int or type(r['address']) is not int:
                raise ValueError('literal integer source seat/address required')
            if source not in limits or not 0 <= seat < limits[source]:
                raise ValueError('not an actual ROM source seat')
            current = (order.index(source), seat)
            if current <= last:
                raise ValueError('source order/repeated request seat')
            last = current
            physical_address(r['address'])  # mandatory scalar bounds, no wrap
    windows = {}
    scan_misses = 0
    previous = None
    for r in reads:
        p = physical_address(r['address'])
        base = p['word'] & ~3
        if base != previous:
            scan_misses += 1
            previous = base
        windows.setdefault(base, []).append(dict(source=r['source'], seat=r['seat'],
            scalar=r['address'], return_scalar_lane=r['address']-16*base))
    # Existing adapter packs only successive equal512-bit words. This preserves
    # later-writer priority, including repeated lanes; no global write reorder.
    batches = []
    for r in writes:
        p = physical_address(r['address'])
        if not batches or batches[-1]['word'] != p['word']:
            batches.append(dict(word=p['word'], bank=p['bank'], row=p['row'],
                group=p['depth_group'], mask=0, scalar_sources=[]))
        batch = batches[-1]
        batch['mask'] |= 1 << p['lane']
        batch['scalar_sources'].append(dict(source=r['source'], seat=r['seat'], lane=p['lane']))
    multiplicity = Counter(r['address'] for r in reads)
    return dict(read_seats=len(reads), write_seats=len(writes),
        distinct_read_scalars=len(multiplicity), maximum_same_scalar_reuse=max(multiplicity.values(), default=0),
        unique_aligned_read_windows=len(windows), current_adapter_window_misses=scan_misses,
        read_windows=[dict(base_word=base, physical_bank_words=list(range(base,base+4)),
            destinations=dest) for base,dest in windows.items()],
        ordered_masked_write_batches=batches,
        physical_write_batches=len(batches), bank_write_batches=[sum(b['bank']==i for b in batches) for i in range(4)],
        conservative_current_adapter_edges=4+2256+865+11*scan_misses+30*len(batches),
        source_exact_broadcast_checked_read_edges=9*len(windows),
        postverified_write_service_edges=28*len(batches),
        broadcast_dispatch_implemented=False,
        broadcast_dispatch_mux_fanout_edges_and_area=None,
        calendar_basis='static current controller9/28+slot/flush costs; no observed ROM trace, no mixed-clock conversion')


def static_first_issue(raw, pc):
    d = decode(int(raw[pc],16))
    if d['unit']!=1 or d['me_d_xbase']:
        raise ValueError('example must be literal static compiled ME address base')
    s = 1 << d['me_split']
    reads = [dict(source='VX',seat=i,address=d['me_xbase']+(i&(s-1))*d['me_xcs'])
        for i in range(2048) if (i >> d['me_split']) < (6144 >> d['me_split'])]
    writes = []
    if d['me_oen']:
        if d['me_d_obase'] or d['me_d_nout']:
            raise ValueError('dynamic writer needs literal parent-resolved source tuple')
        for q in range(min(48,6144>>d['me_split'])):
            for lane in range(16):
                # Literal PART2 first round/j0 mask and output address equations.
                if q*(16 if d['me_mmode'] else 128)+lane < d['me_nout']:
                    writes.append(dict(source='ME',seat=q*16+lane,
                        address=(d['me_obase']+q*d['me_ots'])*16+lane))
    result = compile_frame(reads,writes)
    result.update(pc=pc, instruction_sha256=hashlib.sha256(raw[pc].encode()).hexdigest(),
        split=d['me_split'], xbase=d['me_xbase'], xcs=d['me_xcs'],
        scope='compiled first k0/j0/round0 address obligations; not temporal co-issue or arithmetic execution')
    return result


def proposal(root):
    root=Path(root);inp=root/BOOK/'inputs'
    sources={}
    for name,pin in PINS.items():
        payload=(inp/name).read_bytes()
        if hashlib.sha256(payload).hexdigest()!=pin:raise ValueError('selected ROM source mismatch '+name)
        sources[name]=pin
    text={name:(inp/name).read_text() for name in PINS}
    for name,anchor in [('array.sv','.PART(2)'),('core.sv','assign vw_me_we = me_o_we &'),
        ('core.sv','assign vw_mx_we = me_mx_we & me_en;'),
        ('part.sv','xc + ((gb + gi) & ((1 << split_r) - 1)) * xcs_r'),
        ('top.sv','reg [31:0] vm [0:VM_ELEMS-1]')]:
        if anchor not in text[name]:raise ValueError('source boundary missing '+anchor)
    for flag in ('-GG=6144','-GSMIN=7','-GSMAX=11','-GSW=64','-GLV=7','-GXVM=1','-GENABLE_AR256=1'):
        if flag not in text['top.args.f']:raise ValueError('wrong selected geometry '+flag)
    head=(inp/'head_program.hex').read_text().splitlines()
    layer=(inp/'L20_program.hex').read_text().splitlines()
    examples=dict(HEAD_PC3=static_first_issue(head,3),L20_W1_PC20=static_first_issue(layer,20))
    for name in ('head_program.hex','L20_program.hex'):
        sources[name]=hashlib.sha256((inp/name).read_bytes()).hexdigest()
    protection=json.loads((root/'results/uarch/dsrom_native_masked_backend_prepare_20261003/model.json').read_text())['SRAM_protection_candidate']
    seats=(2256+865)*72
    pairs=2256+865+64
    cuts=32*72*5
    control=8192
    # Positive preliminary terms for Maxwell registration, not an area/slot
    # verdict. Output/XVM/control coding, dispatch and mixed-clock hooks pending.
    cell=pairs*protection['pair_cell_body_um2']/1e6
    ff=(seats+cuts+control)*.2916/1e6
    mux=(seats+cuts+control)*.2/1e6
    raw_macro=256*174.120*29.736/1e6
    check_macro=32*174.120*29.736/1e6
    return dict(schema='opentallas.qwen-rom.part2-finite-vm-source-proposal.v1',
        default_enabled=False,RTL_implementation_added=False,adopted=False,
        source_sha256=sources,controller='core.u_me.u_top ot_qwen_w12_matvec_part PART2',
        ports=dict(read=dict(VA=64,VB=64,VC=64,COLLECTIVE=16,VX=2048),
            write=dict(ME_masked_vectors=48,ME_scalar_seats=768,MX=16,SU=64,REDUCER=1,COLLECTIVE=16),
            total_read_seats=2256,total_write_seats=865,
            read_return_bytes=9024,read_address_enable_bits=56400,write_address_data_enable_bits=49305),
        source_priority=dict(read=READ_ORDER,write=WRITE_ORDER,
            read_old_image=True,later_writer_wins=True,MX_top_condition='vw_mx_we, already core-me_en qualified; no extra top me_clk_en condition'),
        adapter_parameters=dict(ENABLE=0,HEAD_CACHE=0,NR=2256,NW=865,VX0=208,NVX=2048,VM_WORDS=177808),
        literal_read_seat_slices=dict(VA=[0,63],VB=[64,127],VC=[128,191],COLLECTIVE=[192,207],VX=[208,2255]),
        literal_write_seat_slices=dict(ME=[0,767],MX=[768,783],SU=[784,847],REDUCER=[848,848],COLLECTIVE=[849,864]),
        backing=dict(reused='one full16 maskedR2+checked controller, no copies',data_macros=256,check_macros=32,
            physical_data_bytes=2097152,check_bytes=262144,retained_bytes=711232,
            scalar_to_word='a>>4',bank='(a>>4)&3',row='(a>>6)&511',group='a>>15',lane='a&15',
            read_window='four aligned consecutive512-bit words, one CAP1 checked response',
            check_layout='current additive checked controller:2macros/group, each pairs2banks; NOT physical adoption of bank-local historical sidecar layout',
            macro_body_mm2=raw_macro+check_macro,checked_read_caller_edges=9,verified_write_caller_edges=28),
        priced_component_terms=dict(encoded_frame_bits=seats,codec_pairs=pairs,codec_body_mm2=cell,
            pipeline_cut_bits=cuts,control_allowance_bits=control,FF_body_estimate_mm2=ff,mux_estimate_mm2=mux,
            preliminary_50pct_placement_mm2=raw_macro+check_macro+2*(cell+ff+mux)*1.05,
            area_before_remaining_output_XVM_control_protection=True,
            loaded_clock_wire_corridor_mm2=None,parent_home_mm2=None,slot_fit=False),
        examples=examples,
        grant_binding=dict(capture='immutable PRE-edge requests+original intended ME enable, before lowering grant',
            raw_write_hooks=['core.me_o_we','core.me_mx_we'],
            source_intent='original scale_ready && (!core.me_idle || core.me_wake); do not derive capture intent from granted me_en',
            ME_grant='existing me_mem_ok_svc AND actual provider release',
            native_capture='qualified existing me_clk_en, including XVM1/weight/scale/tile/tag response capture',
            SU='hold all3operand windows and entire native SU/controller; SU lacks independent active-op ready',
            retirement='ordered writers physically postverified; real owner/address/mask ACK and consumer publication/read-drain before producer release',
            mixed_clock='Goodall/Laplace own exact PART2 data+tag/credit crossing; no new clock split or CDC policy here',
            missing_source_implementation=['ROM-specific raw-write/gating wrapper against generated59492 source',
                'matched multi-domain source/tile/collective hold and finite-credit enrollment',
                'remaining mutable output/XVM/control protection','physical initialization/published extents before reads']),
        scope_guard=dict(HBM_cost_transfer=False,HBM_snapshot_keeps2048_reads_per_edge=False,
            HEAD_cache_added=False,numerical_run=False,new_build=False,source_rate_claim=None,
            physical_admission=False,Maxwell_unified_registration_required_before_RTL=True))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();r=proposal(a.root);a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(r,indent=2)+'\n')
