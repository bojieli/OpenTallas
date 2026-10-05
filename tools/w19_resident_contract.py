#!/usr/bin/env python3
"""Bounded resident/service candidate, no checkpoint payload or numerical execution.

All sizes are bytes. Controller addresses are 32-byte sectors; bulk-copy
addresses are 128-byte lines. The two address units must never be conflated.
This fixes a reproducible allocation policy, not hardware qualification.
"""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'results/rtl/w19_checkpoint_production_20261001'


def align(n, unit=256):
    return (n + unit - 1) // unit * unit


def owned_rows(n, rank, block=8):
    cycles, tail = divmod(n, 96 * block)
    return cycles * block + min(block, max(0, tail - rank * block))


def controller_bytes(size, stack):
    lines, tail = divmod(size, 128)
    complete = (lines // 4 + (stack < lines % 4)) * 128
    return complete + (tail if stack == lines % 4 else 0)


def map_byte(region, offset):
    if not 0 <= offset < region['bytes']:
        raise ValueError('family address out of range')
    stack = offset // 128 % 4
    return stack, region['base'][stack] + offset // 512 * 128 + offset % 128


def build():
    names = ['non_SM_source_inventory.json', 'accepted256-prerequisite-r2-main-c066.json']
    inventory, weights = [json.loads((EVIDENCE / n).read_text()) for n in names]
    program_path = ROOT / 'results/rtl/w19_hbm_tp96_program_oreduce.json'
    program = json.loads(program_path.read_text())
    pins = {str((EVIDENCE / n).relative_to(ROOT)): hashlib.sha256((EVIDENCE / n).read_bytes()).hexdigest() for n in names}
    sources = ['tools/w19_hbm_tp96_isa.py', 'tools/hdc_golden_v41.py',
               'tools/rtl_v41_fullshape_layer_campaign.py', 'rtl/gpu/ot_gpu_bulk_copy.sv',
               'rtl/gpu/ot_gpu_sm_v.sv', 'rtl/hdc/v41x/ot_hdc_v41x_hcp.sv',
               'rtl/hdc/hbm/ot_hdc_v41x_hcp_hbm_window.sv',
               'rtl/hdc/v41x/ot_hdc_v41x_su_adapt.sv', 'rtl/hdc/kv/ot_hdc_hbm_model.sv',
               'configs/hardware/technology.json', str(program_path.relative_to(ROOT))]
    pins.update({p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in sources})
    pins['tools/w19_resident_contract.py']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    items = inventory['items']
    constants = [i for i in items if i['group'] != 'embedding' and '.engram.embed.' not in i['tensor']
                 and not i['tensor'].endswith(('attn.attn_sink', 'ffn.gate.bias_vl'))]
    # Full matrices/vectors retained. This is a chosen resident-copy policy,
    # not an inference from the logical rank count or a coefficient subset.
    offsets, cursor = [], 0
    for i in constants:
        cursor = align(cursor)
        offsets.append(dict(tensor=i['tensor'], offset=cursor, bytes=i['stored_bytes'], dtype=i['dtype']))
        cursor += i['stored_bytes']
    classified = {i['tensor'] for i in constants}
    classified.update(i['tensor'] for i in items if i['group']=='embedding' or '.engram.embed.' in i['tensor']
                      or i['tensor'].endswith(('attn.attn_sink','ffn.gate.bias_vl')))
    if classified != {i['tensor'] for i in items}:
        raise ValueError('unallocated checkpoint tensor')
    mv = {}
    for layer in program['layers']:
        for op in layer['ops']:
            if op['kind'] == 'mv':
                mv[op['out']] = max(mv.get(op['out'], 0), op['n'])
    ranks = []
    for rank in range(96):
        end = [align(x) for x in weights['placement']['rank_stack_bytes'][rank]]
        regions = []

        def reserve(name, size, dtype, lifecycle):
            region = dict(family=name, bytes=size, dtype=dtype, lifecycle=lifecycle,
                          base=end.copy(), extent=[align(controller_bytes(size, s)) for s in range(4)])
            regions.append(region)
            for s in range(4):
                end[s] += region['extent'][s]

        embed = next(i for i in items if i['tensor'] == 'embed.weight')
        reserve('embedding', owned_rows(embed['shape'][0], rank, 1) * 10240, 'BF16', 'immutable; proposed rowid%96 owner')
        for i in items:
            if '.engram.embed.' in i['tensor']:
                width = i['stored_bytes'] // i['shape'][0]
                reserve(i['tensor'], owned_rows(i['shape'][0], rank, 1) * width, i['dtype'], 'immutable; actual id%96 owner')
        reserve('consumer_coefficients', cursor, 'mixed original F32/BF16', 'immutable full-copy chosen policy, operator staged')
        reserve('attention_sink', 40 * 4 if rank < 64 else 0, 'F32', 'one scalar/layer/head rank')
        # Preserve even the AR-unused VL biases once; they get no consumer/rate credit.
        reserve('unused_VL_bias_archive', sum(i['stored_bytes'] for i in items if i['tensor'].endswith('ffn.gate.bias_vl')) if rank == 0 else 0,
                'F32', 'immutable archive; no AR service')
        reserve('window.codes', 40 * 128 * 512, 'E4M3', 'per-layer ring replicated96; overwrite only after previous attention drains')
        reserve('window.scales', 40 * 128 * 16, 'UE8M0 per32', 'paired commit with window codes')
        # One user; entering pos1M-1 plus one next decode is explicitly bounded.
        for layer, ratio in [(2, 2), (8, 2), (14, 2), (20, 1)]:
            rows = owned_rows((1048577 + ratio - 1) // ratio, rank)
            for family, rowbytes, dtype in [('ckv.codes',256,'E2M1 low-first'), ('ckv.scales',32,'E4M3 per16'),
                                          ('index.codes',64,'E2M1 low-first'), ('index.scales',4,'UE8M0 per32')]:
                reserve(f'L{layer}.{family}', rows * rowbytes, dtype, 'append capacity through1048577 tokens; publish count only after all paired writes complete')
            reserve(f'L{layer}.open', ratio * 4096 if ratio > 1 else 0, 'F32 kv[512]+score[512] per slot', 'only group owner valid; reserve full group; clear after committed append')
            reserve(f'L{layer}.commit_state',64,'U64 counters/epoch/pending mask', 'proposed 8-word protocol, exact writer missing')
        # Distinct named buffers: no capacity alias, no presumed optimal liveness.
        # Matrix destinations are full materialized F32 vectors, preserving ISA
        # addressing even though an eventual GPU schedule should stage/fuse them.
        for name, n in sorted(mv.items()):
            reserve('activation.'+name, n * 4, 'F32', 'matrix destination; reuse only after layer barrier')
        local = {'h':20480, 'x':5120, 'qr':1280, 'o':32768, 'o_own':512, 'z':8192,
                 'yf':5120, 'router':384, 'route_w':6, 'ea':16128, 'iqf':4096,
                 'eg_rows':6144, 'engram_h':20480, 'new_ik':128, 'new_ckv':512,
                 'win_new':512,'q_own':512,'iw':32,'pre':4,'attn_x':5120,'ffn_x':5120,
                 'argmax_v':1}
        for which in ['attn','ffn']:
            local.update({which+'_res':20480,which+'_pre':4,which+'_post':4,which+'_comb':16})
        for e in range(7): local['ea'+str(e)] = 2304
        for name,n in sorted(local.items()): reserve('local.'+name,n*4,'F32','named local result, drain before reuse')
        reserve('route_ids',6*8,'I64','router-selected IDs, RTL producer required')
        reserve('argmax_i_and_token',16,'I64','final reduction input and current token output')
        maxrows = owned_rows(1048577, rank)
        blocks = (maxrows + 7)//8
        # Retain reference F64/I64 storage widths instead of silently narrowing.
        for name,n,dt in [('is_i',maxrows,'I64'),('is_v',maxrows,'F64 BF16-valued'),
                          ('cand_blocks',blocks,'I64'),('cand_block_scores',blocks,'F64'),
                          ('cand_v',2048,'F64'),('cand_i',2048,'I64'),
                          ('cand_mv',2048,'F64'),('cand_mi',2048,'I64'),
                          ('sel_v',512,'F64'),('sel_i',512,'I64'),
                          ('sel_mv',512,'F64'),('sel_mi',512,'I64'),('sel',512,'I64')]:
            reserve('selection.'+name,n*8,dt,'candidate state persists L20-39; score reuse after ordered merge')
        reserve('candidate_keep',blocks,'U8','L20-39 persistent block mask')
        for src in [2,8,14,20]:
            reserve(f'selected_rows.{src}',512*512*4 if rank<64 else 0,'F32 QDQ','head ranks; source rows persist until replacement gather')
        reserve('collective.candidate_merge',96*2048*16,'F64+I64','bounded whole merge input; drain before next merge')
        reserve('collective.selection_merge',96*512*16,'F64+I64','bounded whole merge input; drain before next merge')
        reserve('collective.argmax_merge',96*16,'F32 padded+I64','final head, no hidden host merge')
        reserve('attention.scores_and_exp',2*(128+512)*4 if rank<64 else 0,'F32','one head, golden ordered softmax')
        reserve('attention.window_decode',128*512*4 if rank<64 else 0,'F32 QDQ','one current layer; exact window decoder/staging bridge required')
        reserve('compressor.scratch', (8*512+128)*4,'F32','max ratio2 pooling/projection; owner only valid')
        reserve('hc.operator_staging',1966080,'F32','one complete fn; no overlap credit; HCP bank layout bridge missing')
        reserve('hc.scalar_scratch', (24*8+20480)*4,'F32','HC norm/mixes/Sinkhorn, one operator at a time')
        reserve('hc.activation_staging',20480*2,'BF16','8 HCP term banks, caller barrier before command')
        reserve('state.partial_sector_rmw',4*32,'raw bytes','one pending32B sector/controller; serialize masked scale writes and fence')
        ranks.append(dict(rank=rank, weight_end=weights['placement']['rank_stack_bytes'][rank], regions=regions, stack_end=end))
    high=max(e for r in ranks for e in r['stack_end'])
    sector_bits=((high-1)//32).bit_length()
    ports={
      'controller':dict(module='ot_hdc_hbm_model', proposed=dict(NPC=32,QD=64,RQD=32,RW=16,MAXSKIP=16,CLK_PS=833),
                        request='one valid/ready request/controller/cycle; reads up to16 sectors, writes one32B sector',
                        response='32 independent valid/ready32B sectors/controller/cycle',
                        write_completion='MISSING externally visible write completion/fence port; request acceptance is not commit'),
      'bulk_copy':dict(module='ot_gpu_bulk_copy', descriptor_queue=4, ring_lines=1024, max_outstanding=512,
                       descriptor_unit='128B line', request='valid/ready tagged', response='tagged without ready; credit reservation mandatory',
                       bridge='MISSING stripe/gather4sector line assembly + persistent tags across4controllers'),
      'HCP':dict(module='ot_hdc_v41x_hcp', policy='full coefficients locally resident; prefetch one operator before cmd_valid',
                 read='8 banks x W F32 coefficients/cycle; W model-selected, not default-assumed',
                 missing='fullshape bank layout bridge, staging macro ports/area and qualified clock/cycles'),
      'SU':dict(module='ot_hdc_v41x_su_adapt', N=16, read_bits_cycle=4*16*32,
                read='64 F32 reads/cycle without ready; requires staged operands before go',
                write='16x32b vm +16x32b kv +2x32b reduction ports; arbitration required',
                missing='packed decode/encode, staging banks, F64/I64 selection bridge, append acknowledgment'),
      'SM':dict(module='ot_gpu_sm_v', weight_response_bits=1088, activation_write_bits=2048,
                missing='accepted256 assembly + activation/result routing; router-produced IDs; qualified32SM composition')}
    technology=json.loads((ROOT/'configs/hardware/technology.json').read_text())
    # Read the repository calibration without introducing a new device claim.
    hbm=technology['hbm']['hbm3e']
    hcp=dict(module='ot_hdc_v41x_hcp', policy='existing FP32 vector lanes/tree organization, W32 candidate',
             W=32, TL=7, ML=2, clock_hz=900000000, lanes=256, outputs=24, K=20480,
             chunks=2560, runs=80, norm_tasks=80, coefficient_tasks=1920,
             issue_cycles=2000, pipeline_tail_cycles=31+2+3*5+3*7,
             total_cycles=None, reason='norm rsqrt/scaling/output drain and subsequent sigmoid/Sinkhorn are not included in issue cycles',
             coefficient_read_bits_cycle=8*32*32,activation_read_bits_cycle=8*32*16,
             staging_coefficient_bytes=1966080,staging_activation_bytes=40960,
             coefficient_bank_words=24*80,coefficient_bank_word_bits=32*32,
             bank_layout='bank k, word o*80+r, lane l: fn[o][8*(r*32+l)+k]',
             activation_bank_layout='bank k, word r, lane l: flat[8*(r*32+l)+k]',
             rounding='FP32 multiply; eight contiguous products summed sequentially from+0; padded pairwise chunk tree; golden norm and mix rounding',
             qualification='source defines chunk8 order; no fullshape RTL, SS/FF or composition claim')
    service=dict(controller_ingress='one request/controller/cycle; up to16x32B read sectors or one32B write',
                 policy='serialize nonSM prefetch, compute and dependent matrix-weight phases; no overlap credit',
                 arbitration='proposed four finite class queues per controller: weight, coefficient/table, state read, state write; oldest eligible round-robin at phase owner; do not bypass same-sector pending write',
                 max_read_bytes_request=512, hc_read_requests_controller_operator=960,
                 hc_ingress_floor_cycles_operator=960, hc_ingress_floor_ns_operator=960*833/1000,
                 hc_bandwidth_floor_ns_operator=1966080/(4*hbm['stack_bandwidth_bytes_s']['value'])*1e9,
                 floor_is_not_latency=True,
                 barriers=['drain prior weight/collective consumers before workspace reuse',
                           'issue HCP only when all coefficient and activation staging writes complete',
                           'issue SU go only after all fixed-latency read operands staged',
                           'publish KV/index/window valid count only after paired data+scale writes commit',
                           'do not issue read after write until controller fence acknowledgment'],
                 state_update_protocol='single owner; read-modify-write partial32B sectors because controller has no write mask; preserve neighboring rows; fence before paired code/scale count publication',
                 missing=['finite class arbiter and credit routing not instantiated',
                          'controller write-commit and drain acknowledgment absent',
                          'coalesced stripe reader/tag-to-bank scatter bridge absent',
                          'packed runtime codecs/Engram response/exact indexer wk and pooling absent from composed GPU path',
                          'measured shared controller competition, HCP fullshape and SU/SFU complete cycles',
                          'unified-model area, routes and composed latency owner review'])
    return dict(schema='opentallas.w19.resident-service-candidate.v1', status='ALLOCATION_POLICY_FIXED_MODEL_REVIEW_PENDING',
                source_pins=pins, user_count=1, initial_context=1048576, capacity_tokens=1048577,
                stripe=dict(line_bytes=128,controllers=4,phase=0,base_alignment=256,
                            mapping='controller=(v//128)%4; byte=base[controller]+(v//512)*128+v%128'),
                chosen_policies=['embedding rowid%96, localrowid//96','full consumer coefficient copies per rank; no inferred subsets',
                                 'all source state ownership preserved','F64/I64 reference selection storage retained',
                                 'no double-buffer prefetch overlap credit; no host numerical service'],
                coefficient_offsets=offsets,ranks=ranks,max_stack_end=high,required_sector_bits_candidate=sector_bits,
                checkpoint_tensor_coverage=len(classified),checkpoint_stored_bytes=inventory['stored_bytes'],
                required_bulk_line_bits_candidate=((high-1)//128).bit_length(),
                hc_service=dict(bytes_rank_token=157286400,bytes_controller_token=39321600,products_rank_token=39321600,
                                operator_bytes=1966080,operator_read_sectors=61440,scheduled_overlap=False),
                ports=ports,hc_compute=hcp,service_schedule=service,
                stack_capacity_bytes_calibration=hbm['stack_capacity_bytes']['value'],
                allocation_proof='disjoint aligned extents with bounded admission; not operational fit',
                full_stack_address_width=None,model_critical_cycles=None,model_area_and_routes=None,
                full_resident_qualified=False,full_token_rtl=False,physical_qualified=False)


def validate(c):
    assert c['checkpoint_tensor_coverage']==542
    assert c['hc_compute']['outputs']*c['hc_compute']['K']*4==c['hc_compute']['staging_coefficient_bytes']
    assert c['hc_compute']['runs']*c['hc_compute']['W']==c['hc_compute']['chunks']
    for rank in c['ranks']:
        last=rank['weight_end'].copy()
        for region in rank['regions']:
            for s in range(4):
                assert region['base'][s] % 256 == 0
                assert region['base'][s] >= last[s]
                assert region['extent'][s] >= controller_bytes(region['bytes'],s)
                last[s]=region['base'][s]+region['extent'][s]
            if region['bytes']:
                for offset in {0,region['bytes']-1, min(127,region['bytes']-1),min(128,region['bytes']-1),min(511,region['bytes']-1),min(512,region['bytes']-1)}:
                    s,a=map_byte(region,offset)
                    assert region['base'][s]<=a<region['base'][s]+region['extent'][s]
                    assert a//32 < 1<<c['required_sector_bits_candidate']
        assert last==rank['stack_end']
        assert max(last)<=c['stack_capacity_bytes_calibration']
    assert c['full_stack_address_width'] is None


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    if args.out.exists(): parser.error('refuse overwrite: preserve prior evidence')
    contract=build();validate(contract)
    args.out.write_text(json.dumps(contract,separators=(',',':'))+'\n')
    print(json.dumps({k:contract[k] for k in ['status','max_stack_end','required_sector_bits_candidate','required_bulk_line_bits_candidate']}))
