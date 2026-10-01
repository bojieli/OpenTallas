#!/usr/bin/env python3
"""Bounded accepted-256B resident placement prerequisite; no RTL/model edits.

All expert families stay resident; per-operation descriptors preserve runtime
order and require idle+drain before cfg changes. This tool creates no images,
launches no simulation, and grants no address widening/reload/performance credit.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

import w16_measured_calibration as C

ROOT = Path(__file__).resolve().parents[1]
RECEIPT = 'results/uarch/w16_measured_calibration_20261001/calibration_v2.json'
FETCH = 'rtl/gpu/ot_gpu_expert_fetch.sv'
BENCH = 'rtl/test/tb_w19_fetch_sm.sv'
SELF = 'tools/w16_w19_address_prerequisite.py'
TEST = 'tests/test_w16_w19_address_prerequisite.py'


def descriptor(base, stride, offset, lines, expert, address_bits):
    """Wide host calculation: validate BEFORE narrowing to actual RTL fields."""
    C.require(all(type(v) is int and v >= 0 for v in
                  (base,stride,offset,lines,expert,address_bits)), 'negative/noninteger descriptor')
    C.require(address_bits >= 3 and expert < 384 and lines > 0, 'invalid descriptor geometry')
    C.require(base < 1 << (address_bits-2), 'cfg_base line width overflow')
    C.require(max(stride,offset,lines) < 1 << 16, '16-bit cfg stride/offset/length overflow')
    first = (base + expert*stride + offset)*4
    end = first + lines*4
    C.require(end <= 1 << address_bits, 'sector aperture overflow; no modulo/rebase/reload credit')
    return first, end


def reservations_fit(weight_end, reservations, aperture_bytes):
    """Unknown reservations never qualify a shared stack placement."""
    required = {'constants','embedding','Engram','KV','index'}
    C.require(set(reservations) == required, 'non-SM reservations missing')
    end = weight_end
    for name, region in sorted(reservations.items(), key=lambda p:p[1]['base_bytes']):
        base, size = region['base_bytes'], region['bytes']
        C.require(type(base) is int and type(size) is int and base >= 0 and size > 0,
                  'invalid non-SM reservation: '+name)
        C.require(base % 256 == 0 and size % 32 == 0, 'non-SM reservation alignment')
        C.require(base >= end, 'resident range overlap: '+name)
        C.require(base + size <= aperture_bytes, 'non-SM reservation exceeds aperture')
        end = base+size
    return end


def payload_count(op, rank, sm):
    lo,hi = op['rows'][rank]
    n, k, fmt = hi-lo, op['k'], op['fmt']
    C.require(n >= 0 and fmt in ('fp4','fp8','bf16') and k > 0 and
              (fmt=='bf16' or k%32==0), 'unmatched SM geometry')
    lanes = {'fp4':8,'fp8':4,'bf16':64}[fmt]
    chunks = ((k if fmt=='bf16' else k//32)+7)//8
    groups = (chunks+lanes-1)//lanes
    C.require(groups*8 <= 128, 'XDEPTH issue geometry overflow')
    per_sm = (n+31)//32
    return (min((sm+1)*per_sm,n)-min(sm*per_sm,n))*groups*8


def classify(layer):
    dense, routed = [], []
    for op in layer['ops']:
        if op['kind'] != 'mv':
            continue
        if isinstance(op['w'],list) and isinstance(op['w'][0],int):
            if op['w'][0] == 0:
                routed.append(op)
            elif op['w'][0] == 6:
                dense.append(op)
        else:
            dense.append(op)
    return dense,routed


def placement(program, floorplan):
    """Compressed affine expert runs, all ranks/layers, nearest placed stack.

    Only two endpoint descriptors (expert0/expert383) need checking for each
    affine run: positive stride gives ordered disjoint copies; intra-expert
    segments are constructed consecutively. No 3-billion-record enumeration.
    """
    homes = {sm:int(stack) for stack,sms in floorplan['quadrants'].items() for sm in sms}
    C.require(set(homes)==set(range(32)) and set(homes.values())==set(range(4)),
              'incomplete 32SM/four-stack placement')
    C.require(len(program['layers']) == 41, 'expected40layers+head')
    cursor = [[0]*4 for _ in range(96)] # 128B lines, persistent stack address
    digest = hashlib.sha256()
    checks = {b:dict(passed=0,failed=0,first_failure=None) for b in (24,27)}
    maxima = dict(cfg_exp_lines=0,cfg_off=0,cfg_lines=0,cfg_base=0)
    witness = None
    count = 0
    for layer in program['layers']:
        dense,routed = classify(layer)
        for rank in range(96):
            segments, stride = [[] for _ in range(4)], [0]*4
            # Matches owner host producer's static SM-major resident layout.
            for sm in range(32):
                stack=homes[sm]
                for index,op in enumerate(routed):
                    n=payload_count(op,rank,sm)
                    if not n: continue
                    segments[stack].append((sm,index,stride[stack],n*2))
                    stride[stack]+=n*2
            for stack in range(4):
                begin=cursor[rank][stack]
                for sm,index,off,lines in segments[stack]:
                    entry=dict(rank=rank,stack=stack,layer=layer['layer'],sm=sm,
                               kind='routed',op_index=index,base=begin,stride=stride[stack],
                               offset=off,lines=lines,experts=384)
                    audit_entry(entry,checks,maxima,digest)
                    count+=1
                cursor[rank][stack]+=stride[stack]*384
            for index,op in enumerate(dense):
                for sm in range(32):
                    n=payload_count(op,rank,sm)
                    if not n: continue
                    stack=homes[sm]
                    entry=dict(rank=rank,stack=stack,layer=layer['layer'],sm=sm,
                               kind='dense',op_index=index,base=cursor[rank][stack],
                               stride=0,offset=0,lines=n*2,experts=1)
                    audit_entry(entry,checks,maxima,digest)
                    count+=1
                    cursor[rank][stack]+=n*2
            for stack in range(4):
                if witness is None or cursor[rank][stack]*128 > witness['end_bytes']:
                    witness=dict(rank=rank,stack=stack,through_layer=layer['layer'],
                                 end_bytes=cursor[rank][stack]*128,
                                 last_sector=cursor[rank][stack]*4-1)
    return dict(rank_stack_bytes=[[v*128 for v in row] for row in cursor],
                compressed_descriptor_runs=count, address_checks={str(b):r for b,r in checks.items()},
                cfg_field_maxima=maxima, affine_layout_sha256=digest.hexdigest(),
                highest_resident_address=witness)


def audit_entry(entry,checks,maxima,digest):
    C.require(entry['lines'] % 2 == 0 and entry['offset'] % 2 == 0 and entry['base'] % 2 == 0,
              '256-byte accepted record alignment violated')
    for name,key in [('cfg_base','base'),('cfg_exp_lines','stride'),('cfg_off','offset'),('cfg_lines','lines')]:
        maxima[name]=max(maxima[name],entry[key])
    digest.update((json.dumps(entry,sort_keys=True,separators=(',',':'))+'\n').encode())
    for bits, result in checks.items():
        for expert in set((0,entry['experts']-1)):
            try:
                descriptor(entry['base'],entry['stride'],entry['offset'],entry['lines'],expert,bits)
                result['passed']+=1
            except C.Refusal as exc:
                result['failed']+=1
                if result['first_failure'] is None:
                    result['first_failure']=dict(entry,expert=expert,reason=str(exc))


def build():
    program,floorplan=C.read(C.W19_PROGRAM),C.read(C.W19_FLOORPLAN)
    old=C.read(RECEIPT)
    for path in (C.W19_PROGRAM,C.W19_FLOORPLAN,'tools/w16_measured_calibration.py'):
        C.require(C.sha(path)==old['pins'][path], 'W16 composition input drift: '+path)
    fetch=(ROOT/FETCH).read_text()
    C.require(re.search(r'parameter integer AW\s*=\s*24\s*,',fetch) and
              'input  wire [AW-3:0]' in fetch and 'cfg_base' in fetch and
              all(re.search(r'\[15:0\]\s+cfg_'+name,fetch) for name in ['exp_lines']) and
              '[NSM*16-1:0]' in fetch, 'fetch address/config interface changed; requalify widths')
    p=placement(program,floorplan)
    records,_=C.resident_records(program,floorplan)
    expected=[[n*256 for n in row] for row in records]
    C.require(p['rank_stack_bytes']==expected, 'placement differs from actual256B SM record counts')
    baseline=old['w19_capacity']['padded_baseline']
    C.require(sum(map(sum,expected))==baseline['all_rank_sm_image_bytes'] and
              max(map(max,expected))==baseline['max_resident_stack_bytes'], 'prior accepted256B bound changed')
    paths=(SELF,TEST,'tools/w16_measured_calibration.py',RECEIPT,C.W19_PROGRAM,C.W19_FLOORPLAN,
           FETCH,BENCH,'rtl/hdc/kv/ot_hdc_hbm_model.sv','configs/hardware/technology.json',
           'results/uarch/w16_measured_calibration_20261001/w19_capacity_source_binding.json')
    return dict(schema='opentallas.w16.w19.accepted256.address_prerequisite.v1',
                base_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                layout='256B accepted historical bench baseline:128B weights +8B exponents +120B zero padding',
                scope='Analytical static placement and descriptor representability, all96ranks/40layers+head; not emitted images, golden runtime, transport or physical qualification.',
                placement=p, all_rank_bytes=sum(map(sum,expected)), required_sector_bits=27,
                existing24bit_verdict='FAIL', candidate27bit_verdict=('REPRESENTABLE_WEIGHT_ONLY' if
                    p['address_checks']['27']['failed']==0 else 'FAIL_DESCRIPTOR_FIELDS'),
                full_placement_qualified=False, transport27bit_qualified=False,
                non_sm_reservations={k:None for k in ['constants','embedding','Engram','KV','index']},
                constraints=['nearest-stack SM assignment from placed quadrant ledger',
                             'all384experts resident, dense families once; persistent layer ranges',
                             'per-operation cfg descriptors; idle/drain before config change',
                             'no modulo, rebasing, reload, compact-layout or free whole-expert stream credit'],
                calibration=dict(measured_service_cycles=None,static_config_drain_ns=None,
                                 assumption_from_prior_ledger_ns=340000,headline_adoption=False,
                                 policy='all4 minimumsingleuserdecode;1.2GHzstream/.9serial;SSsetupFFhold60/25'),
                W19_handoff='Qualify accepted256 address path and region transport at computed bounds; obtain non-SM resident allocations and all-family golden opcode-order service before pricing. This tool changes no hardware or model and launches no owner campaign.',
                pins={path:C.sha(path) for path in paths})


def check(record):
    for p,h in record['pins'].items():
        C.require((ROOT/p).is_file() and C.sha(p)==h, 'pin drift: '+p)
    fresh=build();fresh['base_commit']=record['base_commit']
    C.require(fresh==record, 'prerequisite no longer reproduces')


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    mode=ap.add_mutually_exclusive_group(required=True)
    mode.add_argument('--out',type=Path);mode.add_argument('--check',type=Path)
    a=ap.parse_args()
    try:
        if a.check:
            check(json.loads(a.check.read_text())); print('PASS: immutable pins and accepted256 placement audit reproduce; existing24bit FAIL retained')
        else:
            C.require(not a.out.exists(),'output exists; preserve prior verdict')
            result=build()
            with a.out.open('x') as f: json.dump(result,f,indent=2,sort_keys=True);f.write('\n')
            print('Recorded address prerequisite: existing24bit FAIL, candidate27bit '+result['candidate27bit_verdict'])
    except (C.Refusal,FileExistsError) as exc:
        print('REFUSED: '+str(exc));return 1
    return 0


if __name__=='__main__':
    raise SystemExit(main())
