#!/usr/bin/env python3
"""GF(2) encoder and exact response checker for ot_scan_edt8to1.

Input JSON: chains, channels, load[cycle][chain] (0/1/null care cube),
optional good_response[cycle][chain] and fault_responses {fault: response}.
Existing gate_sim load.hex/unload.hex/mask.hex may be imported with --gate-dir
--scan and --pattern. Fully filled patterns remain fully constrained; UNSAT
is a failure, never silently converted to don't-care. No fault-coverage claim
is made without actual faulty response streams from the integrated model.
"""
from __future__ import annotations
import argparse
import gzip
import hashlib
import json
from pathlib import Path


def taps(c):
    return (7*c % 64, (7*c+19) % 64, (7*c+43) % 64)


def decompress(words, chains, channels):
    state = [0]*64
    result = []
    for word in words:
        bits = [(word >> j) & 1 for j in range(channels)]
        result.append([state[a]^state[b]^state[d]^bits[c % channels]
                       for c in range(chains) for a,b,d in [taps(c)]])
        state = [state[64-channels+j]^state[32+j]^state[16+j]^bits[j]
                 for j in range(channels)] + state[:64-channels]
    return result


def encode(load, channels):
    """Return one simultaneous input word per scan edge or an UNSAT witness."""
    chains = len(load[0])
    if not 1 <= channels <= 16 or chains < channels:
        raise ValueError('channels must be 1..16; chains >= channels')
    state = [0]*64
    basis = {}
    care = 0
    for t, row in enumerate(load):
        if len(row) != chains or any(v not in (None,0,1) for v in row):
            raise ValueError('bad care cube')
        bits = [1 << (t*channels+j) for j in range(channels)]
        for c, value in enumerate(row):
            if value is None:
                continue
            a,b,d = taps(c)
            lhs = state[a]^state[b]^state[d]^bits[c % channels]
            rhs = value
            care += 1
            while lhs:
                pivot = lhs.bit_length()-1
                if pivot not in basis:
                    basis[pivot] = (lhs,rhs)
                    break
                v,r = basis[pivot]
                lhs ^= v
                rhs ^= r
            if not lhs and rhs:
                return {'encodable':False,'unsat_cycle':t,'unsat_chain':c,
                        'care_bits_processed':care}
        state = [state[64-channels+j]^state[32+j]^state[16+j]^bits[j]
                 for j in range(channels)] + state[:64-channels]
    solution = 0
    for pivot in sorted(basis):
        lhs,rhs = basis[pivot]
        if ((lhs & solution).bit_count() & 1) != rhs:
            solution |= 1 << pivot
    words = [(solution >> (t*channels)) & ((1 << channels)-1)
             for t in range(len(load))]
    actual = decompress(words,chains,channels)
    mismatch = sum(value is not None and actual[t][c] != value
                   for t,row in enumerate(load) for c,value in enumerate(row))
    if mismatch:
        raise RuntimeError('encoder replay mismatch')
    return {'encodable':True,'words':words,'care_bits':care,'rank':len(basis),
            'care_mismatches':mismatch,'shift_edges':len(load),
            'reset_edges':1,'total_shift_edges':len(load)+1,
            'reset_shift_word':0,'channel_ratio':chains/channels}


def compact(response, channels):
    out = []
    for row in response:
        vals = [0]*channels
        known = [True]*channels
        for c,bit in enumerate(row):
            j = c % channels
            if bit is None:
                known[j] = False
            elif bit in (0,1):
                vals[j] ^= bit
            else:
                raise ValueError('response bit must be 0/1/null')
        out.append([v if k else None for v,k in zip(vals,known)])
    return out


def response_check(good, faulty, channels):
    if len(good) != len(faulty) or any(len(a)!=len(b) for a,b in zip(good,faulty)):
        raise ValueError('response dimensions differ')
    cg,cf = compact(good,channels),compact(faulty,channels)
    raw = any(a is not None and b is not None and a != b
              for x,y in zip(good,faulty) for a,b in zip(x,y))
    detected = any(a is not None and b is not None and a != b
                   for x,y in zip(cg,cf) for a,b in zip(x,y))
    return {'raw_detected':raw,'compact_detected':detected,
            'lost_detection':raw and not detected}


def import_gate(path, scanpath, pattern, channels):
    """Use gate_sim's exact polarity/order-converted streams, not new mappings."""
    raw = scanpath.read_bytes()
    scan = json.loads(gzip.decompress(raw) if scanpath.suffix=='.gz' else raw)
    chains = scan['chain_count']
    length = scan['chain_length_max']
    def read(name):
        lines = (path/(name+'.hex')).read_text().splitlines()
        selected = lines[pattern*chains:(pattern+1)*chains]
        if len(selected) != chains:
            raise ValueError('pattern missing from '+name)
        return [int(x,16) for x in selected]
    load,unload,mask = read('load'),read('unload'),read('mask')
    return {'chains':chains,'channels':channels,
            'load':[[((load[c] >> t) & 1) if t>=length-len(scan['chains'][c]['cells'])
                     else None for c in range(chains)] for t in range(length)],
            'good_response':[[((unload[c] >> t)&1) if (mask[c] >> t)&1 else None
                              for c in range(chains)] for t in range(length)],
            'source_sha256':{str(scanpath):hashlib.sha256(raw).hexdigest(),
                             **{str(path/(n+'.hex')):hashlib.sha256((path/(n+'.hex')).read_bytes()).hexdigest()
                                for n in ('load','unload','mask')}},
            'pattern':pattern,'source_format':'existing gate_sim streams'}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--input',type=Path)
    ap.add_argument('--gate-dir',type=Path)
    ap.add_argument('--scan',type=Path)
    ap.add_argument('--pattern',type=int,default=0)
    ap.add_argument('--channels',type=int,default=4)
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args()
    if bool(args.input)==bool(args.gate_dir):
        ap.error('select --input OR --gate-dir with --scan')
    if args.gate_dir and not args.scan:
        ap.error('--gate-dir requires --scan')
    job=json.loads(args.input.read_text()) if args.input else import_gate(args.gate_dir,args.scan,args.pattern,args.channels)
    if not job['load'] or any(len(row)!=job['chains'] for row in job['load']):
        raise ValueError('load dimensions do not match actual chains')
    result=encode(job['load'],job['channels'])
    result['source_pins']=job.get('source_sha256',{})
    result['coverage_status']='UNVALIDATED_NO_FAULT_RESPONSES'
    result['faults']={}
    if 'good_response' in job:
        result['expected_compact']=compact(job['good_response'],job['channels'])
        for fault,response in job.get('fault_responses',{}).items():
            result['faults'][fault]=response_check(job['good_response'],response,job['channels'])
        if result['faults']:
            result['coverage_status']='PASS_SUPPLIED_RESPONSE_SET' if all(x['raw_detected'] and x['compact_detected'] for x in result['faults'].values()) else 'FAIL_SUPPLIED_RESPONSE_SET'
    result['integrated_atpg_coverage']='UNVALIDATED'
    result['edge_protocol']='scan_en1 pattern_reset1 first shift: zero chain inputs and observe captured OLD outputs; clear codec. Then pattern_reset0 and L encoded shifts. Responses begin on the first reset-shift edge; never extra functional capture.'
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    return 0 if result['encodable'] and not result['coverage_status'].startswith('FAIL') else 1

if __name__=='__main__':
    raise SystemExit(main())
