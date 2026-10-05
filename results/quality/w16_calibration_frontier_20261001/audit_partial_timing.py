#!/usr/bin/env python3
"""Bind completed TP4/SU64 stage spans; never price an unfinished product token."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT=Path(subprocess.check_output(['git','rev-parse','--show-toplevel'],cwd=Path(__file__).parent,text=True).strip())
PIN='914c962e21c5508a957273da912899983cd3eedd'
BASE='results/rtl/qwen_rom_w12_runtime/tp4_L9_checkpoint_20261001/'


def sha(b):return hashlib.sha256(b).hexdigest()


def blob(commit,path):return subprocess.check_output(['git','show',commit+':'+path],cwd=ROOT)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=Path(__file__).parent/'partial_timing.json')
    args=parser.parse_args()
    checkpoint=json.loads(blob(PIN,BASE+'checkpoint.json'))
    verification=json.loads(blob(PIN,BASE+'verification.json'))
    parameters=json.loads(blob(PIN,BASE+'build_params.json'))
    pins={}
    for name,h in verification['artifact_sha256'].items():
        b=blob(PIN,BASE+name);assert sha(b)==h
        pins[BASE+name]=h
    assert checkpoint['checkpoint_status']=='bit_exact'
    assert checkpoint['completed_layers']==['L'+str(i) for i in range(10)]
    assert not checkpoint['terminal_record_exists'] and not checkpoint['adoption']
    assert verification['terminal_scientific_results_available'] is False
    checks=checkpoint['checks'];assert len(checks)==40
    for v in checks.values():
        assert v['mismatches']==0 and v['words']==4096
        assert v['actual_sha256']==v['expected_sha256']
    for die in range(4):
        name='L9_die'+str(die)+'_x.hex';b=blob(PIN,BASE+name)
        assert len(b.splitlines())==4096
        assert sha(b)==checks['L9_die'+str(die)]['expected_sha256']
    for path,v in checkpoint['current_source_commit_matches'].items():
        assert sha(blob(v['commit'],path))==v['sha256']==checkpoint['source_sha256_at_capture'][path]
    assert len(checkpoint['current_source_commit_matches'])==33
    text=blob(PIN,BASE+'token_log_snapshot.log').decode()
    rows=[]
    for line in checkpoint['stage_done_lines']:
        assert line in text
        m=re.search(r'STAGE (L\d+) done cycles=(\d+) start_cyc=(\d+) end_cyc=(\d+) me_busy=(\d+)/(\d+)',line)
        assert m and 'seq_fault=0 core_fault=0 coll_fault=0' in line
        layer,cycles,start,end,busy0,busy1=m.groups()
        row=dict(layer=layer,stage_span_cycles=int(cycles),start_cycle=int(start),end_cycle=int(end),
                 reported_me_busy_cycles=[int(busy0),int(busy1)])
        assert row['end_cycle']-row['start_cycle']==row['stage_span_cycles']
        rows.append(row)
    assert [x['layer'] for x in rows]==checkpoint['completed_layers']
    assert rows[-1]['stage_span_cycles']==4668
    total=sum(x['stage_span_cycles'] for x in rows)
    elapsed=rows[-1]['end_cycle']-rows[0]['start_cycle']
    assert elapsed-total==9
    assert '-GD=4' in parameters['die'] and '-GSW=64' in parameters['die']
    assert '-GLV=7' in parameters['die'] and '-GTCUT=7' in parameters['die']
    assert '-GLAT=339' in parameters['coll'] and '-GDEPTH=1024' in parameters['coll']
    result=dict(schema='opentallas.w16.partial-stage-timing.v1',observed_utc=datetime.now(timezone.utc).isoformat(),
                basis=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                owner_receipt_commit=PIN,owner_receipt_path=BASE+'checkpoint.json',evidence_sha256=pins,
                validation=dict(owner_artifact_hashes=len(pins),composite_source_blob_checks=33,
                                paired_owner_checkpoint_checks=40,independent_archived_L9_vectors=4,
                                archived_L9_words=16384,stage_cycle_arithmetic=True,zero_logged_faults=True),
                parameters=parameters,binary_sha256=checkpoint['binary_sha256'],stages=rows,
                completed_stage_span_sum_cycles=total,first_to_last_stage_elapsed_cycles=elapsed,
                between_stage_unattributed_cycles=elapsed-total,
                claim='Completed L0-L9 spans on this TP4/SU64 runtime only. Four archived L9 vectors independently match owner golden hashes; source composite is current capture provenance, not final launch-time stability.',
                reported_busy_scope='The log exposes two ME busy counters; these are not a four-rank timing decomposition or isolated body service. Work can overlap within stage spans.',
                calibration=dict(measured_stage_spans_available=True,measured_body_cycles=None,
                                 measured_collective_service_cycles=None,measured_memory_service_cycles=None,
                                 full_token_cycles=None,product_price=None,baseline_rate=None,transfer_to_su1024=False,
                                 scope='No L9/L0 or TP2/TP4 raw ratio; no multiplication by remaining layers. COLLECTIVE_LAT339 is a link parameter, not all-reduce service; stage gap cycles are unattributed.'),
                completion_dependencies=['Existing owner runtime completes L10..L35 and head with final token/state exactness.',
                    'Final launch/source/binary/vector stability receipt at this exact configuration.',
                    'Matched body/collective/memory-service traces before component calibration.',
                    'Explicit matching product configuration; SU64 cannot price SU1024.',
                    'Contextual SS setup/FF hold at unchanged60ps/25ps uncertainty before hardware qualification.'],
                collectors_reused=True,new_scientific_jobs=False,model_source_changed=False,headlines_changed=False,
                full_token_qualified=False,hardware_adopted=False,full_qcnam_verdict=None,
                generator_sha256=sha(Path(__file__).read_bytes()))
    with args.out.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print('PASS: 9 archive hashes, 33 source blobs, 40 owner paired checks, 4 independent L9 vectors, 10 stage spans; no product pricing')


if __name__=='__main__':main()
