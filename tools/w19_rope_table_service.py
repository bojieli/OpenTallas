#!/usr/bin/env python3
"""GPU-standard resident read-only RoPE coefficient table/service candidate.

Precompute exact golden coefficients OFFLINE, then runtime ordinary SM loads
from finite HBM. No native approximate sin/cos, no runtime host coefficients.
Tables are not emitted here. Address extension is append-only to609 candidate;
actual allocation, wholegraph resources/fit and service admission remain pending.
"""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import hdc_golden_v41 as V
from w19_resident_contract import controller_bytes,map_byte,align

ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/'results/rtl/w19_checkpoint_production_20261001'
CONFIG=ROOT/'compiler/models/deepseek-v4.1-flash/inference_config.json'
POSITIONS=1048577;ROW_BYTES=256


def coefficients(config,variant,positions):
    if variant not in ['plain','yarn']:raise ValueError('actual frequency variants only')
    pos=np.asarray(positions,np.int64)
    if np.any(pos<0) or np.any(pos>=POSITIONS):raise ValueError('position outside frozen table capacity; nevermodulo')
    f=V.rope_freqs(config['rope_head_dim'],config['original_seq_len'] if variant=='yarn' else 0,
                  config['compress_rope_theta'] if variant=='yarn' else config['rope_theta'],
                  config['rope_factor'],config['beta_fast'],config['beta_slow'])
    # Exact golden F32 angle multiply, then F64 NumPycos/sin, then F32.
    # This is an offline constant producer only, never a runtime substitute.
    angle=(pos.astype(np.float32)[:,None]*f[None,:]).astype(np.float32)
    return np.concatenate([np.cos(angle.astype(np.float64)).astype(np.float32),
                           np.sin(angle.astype(np.float64)).astype(np.float32)],axis=1)


def allocate(resident):
    ranks=[]
    for r in resident['ranks']:
        end=r['stack_end'].copy();regions=[]
        for variant in (['plain','yarn'] if r['rank']<64 else ['yarn']):
            size=POSITIONS*ROW_BYTES
            region=dict(family='rope.coefficients.'+variant,bytes=size,base=[align(x) for x in end],
                        extent=[align(controller_bytes(size,s)) for s in range(4)],
                        dtype='F32 row[COS32,SIN32]',readonly=True)
            regions.append(region);end=[b+e for b,e in zip(region['base'],region['extent'])]
        ranks.append(dict(rank=r['rank'],historical_stack_end=r['stack_end'],regions=regions,stack_end=end))
    high=max(max(r['stack_end']) for r in ranks)
    return dict(ranks=ranks,max_stack_end=high,required_sector_bits=((high-1)//32).bit_length(),
                required_bulk_line_bits=((high-1)//128).bit_length(),
                added_allocated_bytes=sum(sum(x['extent']) for r in ranks for x in r['regions']))


def requests(region,position):
    if not 0<=position<POSITIONS:raise ValueError('position exceeds capacity')
    result=[]
    for line in range(2):
        virtual=position*256+line*128;stack,byte=map_byte(region,virtual)
        if byte%32:raise ValueError('sector alignment')
        result.append(dict(stack=stack,sector=byte//32,sectors=4,bytes=128,coefficient_half='COS' if line==0 else 'SIN'))
    return result


def build():
    p=EVIDENCE/'resident-service-candidate-r1.json';resident=json.loads(p.read_text())
    config=json.loads(CONFIG.read_text());program_path=ROOT/'results/rtl/w19_hbm_tp96_program_oreduce.json'
    g=json.loads(program_path.read_text());binding=[]
    for l in g['layers']:
        for o in l['ops']:
            if o['kind']!='local' or o['fn'] not in ['q_rope','attend','index_q','compressor']:continue
            fn=o['fn'];variant='yarn' if fn in ['index_q','compressor'] or config['compress_ratios'][o['layer']]>0 else 'plain'
            binding.append(dict(layer=l['layer'],op=o['id'],function=fn,variant=variant,owners=o['ranks'],
                                row_position='currenttokenpos+1-compressratio onlywhen group closes' if fn=='compressor' else 'currenttokenpos',
                                runtime_read_bytes=256,cache_hit_credit=False))
    paths=['tools/w19_rope_table_service.py','tools/w19_resident_contract.py',str(p.relative_to(ROOT)),
           str(CONFIG.relative_to(ROOT)),str(program_path.relative_to(ROOT)),'tools/hdc_golden_v41.py']
    a=allocate(resident)
    count_rank=[]
    for rank in range(96):
        n=0
        for b in binding:
            spec=b['owners']
            if spec=='all' or (spec=='heads' and rank<64) or (isinstance(spec,list) and rank in spec):n+=1
        count_rank.append(n)
    return dict(schema='opentallas.w19.gpu-rope-resident-service.v1',status='ALLOCATION_SERVICE_CANDIDATE_NOT_ADMITTED',
        source_pins={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},
        format=dict(positions=POSITIONS,position_min=0,position_max=POSITIONS-1,variants=2,rowsize=256,
                    columns='COS32 followedbySIN32 exactF32bits',unique_logical_bytes=2*POSITIONS*256),
        ownership=dict(plain_full_replicas=64,yarn_full_replicas=96,
                       reason='plain q_rope/attend onlyheadowners0..63; yarn index_q all96 and compressor cyclicowner across96',
                       raw_replica_bytes=(64+96)*POSITIONS*256,chosen_policy=True,no_wholeembedding_orEngram_replication=True),
        allocation=a,source_graph_binding=binding,
        runtime=dict(requester='existing SM0 ordinaryGPU load/DMA client, not inventedextraendpoint',
                     row_commands=2,sectors_per_command=4,bytes_per_lookup=256,length_limit=16,
                     request='immutable typedvariant +currenttokenposition,tagged two128B loads routed toactualfourstack addresses',
                     client_count='32SM baseline; no +4injector inference',
                     coefficient_cache='proposed two256B rows +32Bvalid/tag ownership in SM0shared;544B explicitlyreserved, no cachehitlatency credit',
                     private_coefficient_staging='256BperconsumerSM explicitlyreserved inshared, notfreeRF/L2',
                     ordinary_warp_reads=2,shared_read_bytes=256,shared128B_cycle_floor=2,
                     RF_read_latency_cycles=2,coefficient_RF_words_per_pair=2,
                     register_demand='cos/sin heldlane-local acrossfourFMUL/twoFADD; shared ports compete withallotherloads',
                     NoC_tail_consumers='q_rope/inverseattend fourSMtailgroups,64B each=>256B delivery',
                     NoC_index_consumers='32indexheadSMs,256B each=>8192B delivery; nocfreebroadcast',
                     fetch_count=len(binding),read_bytes_rank_token_upper_candidate=len(binding)*256,
                     actual_source_graph_lookup_count_rank=count_rank,
                     actual_source_graph_read_bytes_rank=[n*256 for n in count_rank],
                     service_wait_cycles=None,
                     events=['boundscheckposition+actualvariant beforeissue','bothsectorcommands acceptedwithreserved landingcredit',
                             'all8sectorpayloads returnedwith matchingtag/address','bothcoefficienthalves staged+writevisibility',
                             'actualfiniteNoC+CDC deliveries acknowledged','consumer RFloads finish',
                             'allreaderconsumerdone before cache/staging slot reuse']),
        offline_producer=dict(recipe='F32(position)*F32freq thennumpyF64cos/sin thenF32; fullrange128/640proofcoeffinputs bindthisdefinition',
                              generator_source_pinned=True,full_images_emitted=False,
                              producer_platform_must_be_pinned='NumPy version/ufunc ELF+CPU ISA configuration for immutable emittedtable hash',
                              production_host_arithmetic=False,native_GPU_sin_cos=False),
        alternatives='exactGPUsoftware sin/cos backend is UNPRICED/UNQUALIFIED; no approximate SFU substitute adopted',
        prerequisites=['Ram accepts actualconsumer policy/newfamily and correctedfullresident aperture/traffic',
                       'sourcebound offlinewhole-table content identity beforeimagesemit, boundedlogicalsource proof nowonly',
                       'commoncontroller finitecoalescer/landing/NoC/CDC+readerepoch waits priced andconnected',
                       '544Bcache+256Bconsumer staging against64KB shared schedule/ports inclHC overlap','full composedarea/routes/floorplan admission'],
        full_token_cycles=None,physical_qualified=False,adopted=False)


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    if a.out.exists():ap.error('refuse overwrite')
    a.out.write_text(json.dumps(build(),indent=2)+'\n')
