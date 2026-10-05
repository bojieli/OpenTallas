"""Immutable fullgeometry operands and independent assertion images; no HDL launch."""
import argparse
import hashlib
import json
from pathlib import Path
import random
import struct

ROOT=Path(__file__).resolve().parents[1]
ORIGIN='results/uarch/topk_finite_source_context_20261002/inputs/c429b2732aea08d9f6fa9ddc850afdbd7b4bd6ea/rtl/chip/'
PINS={ORIGIN+'ot_coll_topk_merge.sv':'e56fefef4d92d0de6faa7a583f9e419bcb9178290a1ef74df34c38aee0b509c6',
      ORIGIN+'ot_w15_coll_dma.sv':'0d77baaf7f85a2c4ac7542c39be51d0a360d665496df392738e59d01756ef3ab'}
TEMPLATE='tools/rtl_templates/bench_dsrom_full_selector_dma_prepare.sv'
MODELS=['results/uarch/dsrom_selector_allowed_terminal_model_20261002/model.json',
        'results/uarch/dsrom_balanced_selector_fence_proof_20261002/proof.json']

def sha(b):return hashlib.sha256(b).hexdigest()
def write_json(p,obj):p.write_text(json.dumps(obj,sort_keys=True,indent=2)+'\n')
def cases():
    out=[]
    for n in (512,2048):
        for pattern in ('all_tie','signed_boundaries','random_finite'):
            for k in (1,63,64,65,512,4*n):out.append((n,k,pattern))
        if n==2048:out.append((n,2048,'signed_boundaries'))
    return out

def scores(n,pattern):
    if pattern=='all_tie':return [0x3f800000]*(4*n)
    if pattern=='signed_boundaries':
        special=[0x80000000,0,0x3f800000,0xbf800000,0x7f800000,0xff800000,1,0x80000001,0x7f7fffff,0xff7fffff]
        return [special[i%len(special)] for i in range(4*n)]
    if pattern!='random_finite':raise ValueError('unknown pattern')
    rng=random.Random(20261002+n);out=[]
    for _ in range(4*n):
        w=rng.getrandbits(32)
        if (w>>23)&255==255:w^=1<<23
        out.append(w)
    return out

def pack(words):return sum(x<<(32*i) for i,x in enumerate(words))
def operands(n,words):
    # Native LDW4: every 2048-bit beat holds one16-lane word from each rank.
    return [pack([words[r*n+16*j+i] if half==0 else 16*j+i
                  for r in range(4) for i in range(16)])
            for half in range(2) for j in range(n//16)]

def expected(n,k,words):
    # IEEE numerical comparison, independent of RTL order-key/radix/filter implementation.
    floats=[struct.unpack('!f',struct.pack('!I',w))[0] for w in words]
    if any(x!=x for x in floats):raise ValueError('NaN belongs to a separate fault gate')
    ids=[(i//n)*(2*n)+i%n for i in range(4*n)]
    chosen=sorted(ids[i] for i in sorted(range(4*n),key=lambda i:(-floats[i],ids[i]))[:k])
    chosen += [0]*((-k)%16)
    return [pack(chosen[j:j+16]) for j in range(0,len(chosen),16)]

def prepare(output):
    for p,h in PINS.items():
        if sha((ROOT/p).read_bytes())!=h:raise ValueError('original source pin changed: '+p)
    if output.exists():raise ValueError('fresh output required')
    output.mkdir(parents=True)
    for sub in ('inputs','expected','reference'): (output/sub).mkdir()
    for p,h in PINS.items():(output/'reference'/Path(p).name).write_bytes((ROOT/p).read_bytes())
    (output/'bench_dsrom_full_selector_dma_prepare.sv').write_bytes((ROOT/TEMPLATE).read_bytes())
    records=[];calls=[]
    for idx,(n,k,pattern) in enumerate(cases()):
        raw=scores(n,pattern);beats=operands(n,raw);golden=expected(n,k,raw)
        ip=f'inputs/case_{idx:02d}.mem';ep=f'expected/case_{idx:02d}.mem'
        (output/ip).write_text(''.join(f'{b:0512x}\n' for b in beats))
        (output/ep).write_text(''.join(f'{b:0128x}\n' for b in golden))
        records.append(dict(index=idx,runtime_n=n,k=k,pattern=pattern,input_path=ip,assertion_path=ep,
            input_beats=len(beats),expected_VM_words=len(golden),
            raw_score_sha256=sha(struct.pack('<'+str(len(raw))+'I',*raw)),
            input_image_sha256=sha((output/ip).read_bytes()),assertion_image_sha256=sha((output/ep).read_bytes())))
        calls.append(f'run_case({idx},{n},{k},0);')
    calls += [f'run_case(5,512,2048,{phase});' for phase in range(1,5)]
    (output/'case_calls.svh').write_text('\n'.join(calls)+'\n')
    modelpins={p:sha((ROOT/p).read_bytes()) for p in MODELS}
    plan=dict(schema='opentallas.fullselector.dma.functional-fixture.v1',status='FIXTURE_PREPARED_CANDIDATE_PACKAGE_INCOMPLETE',
        geometry=dict(N=4,NMAX=2048,LDW=4,P=64,PF=64,DIG=8,CB=14,WA=15,FW=512,GW=4),
        model_pins=modelpins,original_pins=PINS,fixture_template_sha256=sha((ROOT/TEMPLATE).read_bytes()),cases=records,
        expected_counts=dict(legal_cases=37,reset_aborts=4),expected_values_assertions_only=True,
        immutable_synthetic_root_inputs=True,actual_field_accepted_trace=False,
        event_calibration=dict(service_increment=142,input=99,return_=99,formed_write=28,total_increment=368,
            exact_absolute_reference_cycles_asserted=False,source_envelope_not_measurement=True),
        first_root_beat_contract=dict(command_to_first_return_falling_ticks=4,
            reason='go sampled then nh_r updated; idle selector wpr captures updated n next edge before loads',
            actual_field_delivery_timing_credit=False),
        write_sampling='pre-NBA posedge VM capture; fault/busy checks after1ps settle',
        reset_regions=['partial load','input station in flight','reference write before candidate','candidate formed writes/drain pending'],
        remaining_functional_gates=['actual candidate balanced selector RTL/package','NaN and bad-command sticky fault gates',
            'busy command refusal','actual HDL mutant explicit DIFF controls','full caller/source dependency review'],
        missing_compile_modules=['ot_w15_coll_dma_balanced_station_prepare','ot_chip_v41x_coll_transpose'],
        compile_admitted=False,simulation_executed=False,RTL_equivalence=False,physical_admitted=False,
        SS_FF_clock_credit=False,full_token_credit=False,
        physical_dependency='Arch/Maxwell legal clock/reset/PG/escape construction including allowed BUFx4 terminals +108DBU width',
        resource_admission='Fresh measured CPU/RAM/disk inventory and reservation; no arbitrary time/FSIZE/per-process AS caps')
    write_json(output/'sourceplan.json',plan)
    manifest={p.relative_to(output).as_posix():sha(p.read_bytes()) for p in sorted(output.rglob('*')) if p.is_file()}
    write_json(output/'artifact_manifest.json',manifest)
    return plan

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();plan=prepare(args.output)
    print(json.dumps(dict(status=plan['status'],cases=len(plan['cases']),compile_admitted=False)))
