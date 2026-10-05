#!/usr/bin/env python3
"""Prepare (default) or explicitly run a parent-reviewed isolated correctness gate.

No idx_hbm timing replay; the parent owns the connected timed credit1 baseline.
--run-reviewed is for use only after the parent reviews the model/source plan.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
PIN='4e38326d6f361bc85e660f48c59c355e2bb95274'
CONTRACT_COMMIT='df0987b9a705e85bb439359bed2f93eac8994829'
CONTRACT_PATH='results/uarch/w17_window_epoch_contract_20261001/contract_r2.json'
CAND=Path('rtl/test/w17_window_epoch9_candidate')
PF='ot_chip_v41x_window_kv_prefetch.sv'
SOURCE='ot_chip_v41x_window_attn_source.sv'
NAMES=['window_refill_schedule','window_row_codec','window_stage4','window_stream',
       'attn_row_merge','window_retention','kv_reqmux','kv_rope_reqmux','hbm_karb']
COMMON=['rtl/chip/ot_chip_v41x_'+n+'.sv' for n in NAMES]
BENCH=str(CAND/'tb_epoch9.sv')


def sha(b):return hashlib.sha256(b).hexdigest()
def committed(p,commit=PIN):
    return subprocess.check_output(['git','show',commit+':'+p],cwd=ROOT)


def source_plan():
    expected=committed('rtl/chip/'+PF).decode().replace(
        'localparam integer EPOCH_W = TAGW > 5 ? TAGW-5 : 1;',
        '// TEST-ONLY CANDIDATE: reserve two KV/RoPE owner bits; healthy row drain is unchanged.\n    localparam integer EPOCH_W = TAGW > 7 ? TAGW-7 : 1;').replace(
        '(REFILL_CREDITS > 1 && TAGW < 6)', '(REFILL_CREDITS > 1 && TAGW < 8)')
    assert (ROOT/CAND/PF).read_text()==expected
    assert (ROOT/CAND/SOURCE).read_bytes()==committed('rtl/chip/'+SOURCE)
    originals=[*COMMON,'rtl/chip/'+PF,'rtl/chip/'+SOURCE,'tools/uarch_model.py']
    pins={p:sha(committed(p)) for p in originals}
    assert all(sha((ROOT/p).read_bytes())==h for p,h in pins.items())
    new=[str(CAND/PF),str(CAND/SOURCE),BENCH,'tools/w17_window_epoch9_candidate_gate.py']
    return dict(original_sha256=pins,added_sha256={p:sha((ROOT/p).read_bytes()) for p in new},
                original_RTL_and_uarch_byte_identical=True,source_copy_byte_identical=True,
                delta='Candidateonly EPOCH_W TAGW-5 ->TAGW-7 and multi-credit TAGWminimum6->8; comment explains ownerbudget. No otherprefetch logic/sourcebehavior modified.')


def caps():
    os.nice(10)
    os.sched_setaffinity(0,{max(os.sched_getaffinity(0))})
    resource.setrlimit(resource.RLIMIT_AS,(3*1024**3,3*1024**3))
    resource.setrlimit(resource.RLIMIT_CPU,(180,180))
    resource.setrlimit(resource.RLIMIT_FSIZE,(16*1024**2,16*1024**2))


def execute(command,log,timeout):
    begin=time.monotonic()
    with log.open('x') as stream:
        try:
            proc=subprocess.run(command,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,
                                timeout=timeout,preexec_fn=caps)
            status=proc.returncode
        except subprocess.TimeoutExpired:
            status='WALL_TIMEOUT'
    return dict(command=command,status=status,wall_seconds=time.monotonic()-begin,log_sha256=sha(log.read_bytes()))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',required=True,help='new directory; never overwrite failures')
    parser.add_argument('--run-reviewed',action='store_true',help='execute only after parent model/source review')
    parser.add_argument('--review-reference',help='parent approval reference, required with --run-reviewed')
    args=parser.parse_args()
    if args.run_reviewed and not args.review_reference:
        parser.error('--run-reviewed requires --review-reference after actual parent review')
    out=(ROOT/args.out).resolve()
    out.mkdir(parents=True,exist_ok=False)
    plan=source_plan()
    contract=committed(CONTRACT_PATH,CONTRACT_COMMIT)
    c=json.loads(contract)
    assert c['proposed_minimal_encoding']['implementation_model_ready']
    cmds={}
    for arm in ('candidate','original'):
        copies=[str(CAND/PF),str(CAND/SOURCE)] if arm=='candidate' else ['rtl/chip/'+PF,'rtl/chip/'+SOURCE]
        cmds[arm]=['iverilog','-g2012','-s','tb_epoch9','-o',str(out/(arm+'.vvp')),*copies,*COMMON,BENCH]
    cases=[dict(name='healthy_wrap',arm='candidate',args=[],marker='EPOCH9_CORRECTNESS_PASS'),
           *[dict(name=x.lower(),arm='candidate',args=['+'+x],marker='INJECTED_REPLY_REJECTED') for x in ('STALE','DUPLICATE','UNKNOWN_SECTOR','POISON')],
           dict(name='original_epoch512',arm='original',args=['+ORIGINAL_NEGATIVE'],marker='ORIGINAL_EPOCH512_REJECTED')]
    record=dict(schema='opentallas.rtl.window_epoch9_candidate_prepared.v1',
        recorded_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_commit=PIN,
        branch_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        contract=dict(commit=CONTRACT_COMMIT,path=CONTRACT_PATH,sha256=sha(contract)),
        **plan,scope='TEST-ONLY copies selectedexplicitlybynewbench. Syntheticnonpoisoncorrectnessservice, actualnestedowner muxes/directKARB. No actualbackendtiming, latencycredit, payloadcheckpoint/fulltokenqualification, SS/FF or adoption.',
        review=dict(status='REFERENCE_PROVIDED' if args.run_reviewed else 'AWAITING_PARENT_REVIEW_NO_BUILD',reference=args.review_reference),
        compile_commands=cmds,cases=cases,
        modeled_cost=dict(epoch_bits=9,metadata_bits=53,delta_bits=-2,new_payload_bits=0,
                          healthy_wrap_added_cycles=0,fault_drain_interface='NOT_IMPLEMENTED; externalquiescence stillrequired'),
        synthetic_service=dict(PCs=32,length_width=4,beat_width=4,tag_width=17,address_width=30,
            queue_slots_per_PC=8,max_source_outstanding=8,
            queue_descriptor_bits_per_slot=1+32+32+30+17,
            queue_descriptor_bits_total=32*8*(1+32+32+30+17),
            return_register_bits=32*(1+17+4+256),
            behavior='Roundeddue times and largestreadyserialnumber force OOO; eachPCregisteredoffer holdsuntil actualKARB selectsandconsumes it; negedge readystimulus creates refusal; onebit-ownerprefix100 required. No DRAMtimingmodel.',
            data='benchgeneratedbytes1..120 indexedfulladdress; no backingmemory or checkpoint; sourceprime API createsprovenance'),
        assertions=['Healthyseed510 witnesses511,0,1 across128rowfetches;2176requests/responses,68perPC,32chronologicalpackedbeats',
            'PerPCaccepted-consumed equalsqueued+heldreturns; summed equals sourcepending; epochadvance onlypending0 withclearednewrow masks',
            'Publishedrow IDLE requires issued=received=17ones,pending0; scaleafter16codes; fulljobstagebeforestream_go',
            'Refusedrequeststable and heldbackendreturnstable; exactaddr/sector/epoch/owner and stagedpayload bytes',
            'Positivecoverage requires OOO,heldreturn,requestrefusal, sinkhold, maxpending8',
            'Malformedreply faults and suppressespublication/newrequests; no faultcounterdrainclaim',
            'Original11bit source atquiescentepoch511 emits4000 afteradvance; muxfault,ready0,no backendadmission/publication'],
        caps=dict(workers=1,address_space_bytes=3*1024**3,compile_wall_seconds=60,
                  runtime_wall_seconds_per_case=30,cpu_seconds_per_process=180,
                  correctness_simulation_cycles=200000,output_file_bytes=16*1024**2),
        parent_timed_baseline='Parentowned, notincluded orduplicated. BaselineLENW4fixturefix acknowledged; no diagnosisofDUTfault inferred.',
        no_original_edits=True,build_run=args.run_reviewed)
    if args.run_reviewed:
        started=time.monotonic();results=[]
        for arm,cmd in cmds.items():
            result=execute(cmd,out/(arm+'_compile.log'),min(60,max(1,180-(time.monotonic()-started))))
            result.update(kind='compile',arm=arm);results.append(result)
            if result['status']!=0:break
        if all(r['status']==0 for r in results):
            for case in cases:
                remaining=180-(time.monotonic()-started)
                if remaining<=0:
                    results.append(dict(case=case['name'],status='TOTAL_WALL_CAP'));break
                log=out/(case['name']+'.log')
                result=execute(['vvp',str(out/(case['arm']+'.vvp')),*case['args']],log,min(30,remaining))
                result.update(kind='runtime',case=case['name'],marker_present=case['marker'] in log.read_text())
                results.append(result)
                if result['status']!=0 or not result['marker_present']:break
        record['results']=results
        record['verdict']='PASS_BOUNDED_CORRECTNESS_ONLY' if len(results)==8 and all(r['status']==0 and r.get('marker_present',True) for r in results) else 'FAIL_PRESERVED'
    else:
        record['verdict']='PREPARED_NOT_COMPILED_OR_RUN'
    (out/'record.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps({k:record[k] for k in ('verdict','review','build_run')},indent=2))
    return int(record['verdict']=='FAIL_PRESERVED')


if __name__=='__main__':
    sys.exit(main())
