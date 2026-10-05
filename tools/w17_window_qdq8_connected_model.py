#!/usr/bin/env python3
"""Compose actual QDQ8 boundary with finite write/read calendar; prepare only."""
import argparse
import hashlib
import inspect
import json
from pathlib import Path
import subprocess
import textwrap
import w17_window_qdq8_arithmetic_model as arithmetic
import w17_window_epoch9_producer_prediction as original
import w17_window_epoch9_producer_log_reanalysis as accounting

ROOT=Path(__file__).resolve().parents[1]
PIN=arithmetic.PIN
BENCH='rtl/test/w17_window_qdq8_connected/tb.sv'
BODY='rtl/test/w17_window_qdq8_connected/transport_body.svh'
ARITH_ROOT=ROOT/'results/uarch/w17_window_qdq8_arithmetic_preparation_20261002'
PRODUCER_ROOT=ROOT/'results/uarch/w17_window_epoch9_producer_prediction_20261001_attempt3'

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def replay(t,retain,calendar):
    """Reuse immutable qualified finite calendar; only add QE admission and pairs.

    Old engine service and backend timing math are unchanged. ACT accounting
    correction was already source-verified on retained transport logs.
    """
    pairs=5 if retain else 3
    text=textwrap.dedent(inspect.getsource(original.replay))
    edits={
      'def replay(t,rows=128,retain=0):':'def connected_replay(t,retain,pairs,calendar):\n    rows=128',
      'writer_start=300':"writer_start=300+calendar['capture_sample'][0]",
      'range(200001)':'range(400001)',
      'c==writer_start+17':"c==300+calendar['issue_sample']+1",
      'if op==1:':'if op%2==1:',
      'if op==0:desc_due=c+1':'if len(op_done)<2*pairs:desc_due=c+1',
      'assert len(op_done)==2':'assert len(op_done)==2*pairs'}
    for a,b in edits.items():
        assert text.count(a)==1,(a,text.count(a));text=text.replace(a,b)
    ns={};exec(compile(text,'<composed QE boundary and drained descriptor repetitions>','exec'),original.__dict__,ns)
    old=original.WriteBackend.schedule;original.WriteBackend.schedule=accounting.corrected_schedule()
    try:summary,events=ns['connected_replay'](t,retain,pairs,calendar)
    finally:original.WriteBackend.schedule=old
    rows=128*pairs*(1 if retain else 2)
    assert summary['final_epoch']==rows%512
    requests=[e for e in events if e['kind']=='request' and not e['we']]
    first_sectors=[e for e in requests if e['sector']==0]
    assert len(first_sectors)==rows
    assert [e['epoch'] for e in first_sectors]==[(n+1)%512 for n in range(rows)]
    wrap=first_sectors[511];after=first_sectors[512]
    # Return path tags carry 9-bit epoch, never owner alias 0x4000.
    assert wrap['tag']==65536 and after['tag']==65568
    assert all((e['tag']&0xc000)==0 for e in requests)
    summary.update(pairs=pairs,descriptors=2*pairs,cold_rows=rows,read_requests=rows*17,
        epoch_wrap_request=wrap,first_postwrap_request=after,
        total_packed_beats=32*2*pairs,local_QE_accept_cycle=300,
        QE_capture_cycles=[300+c for c in calendar['capture_sample']],
        QE_idle_sample=300+calendar['idle_sample'],producer_issue_cycle=300+calendar['issue_sample'])
    return summary,events


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',required=True);a=ap.parse_args()
    arith=json.loads((ARITH_ROOT/'model.json').read_bytes());pred=json.loads((PRODUCER_ROOT/'prediction.json').read_bytes())
    assert sha(ROOT/'tools/w17_window_epoch9_producer_prediction.py')==pred['generator_sha256']
    source_pins=dict(arith['source_sha256'],**pred['source_sha256'])
    for p,h in source_pins.items():
        assert sha(ROOT/p)==h
        assert hashlib.sha256(subprocess.check_output(['git','show',PIN+':'+p],cwd=ROOT)).hexdigest()==h
    for p,h in pred['candidate_sha256'].items():assert sha(ROOT/p)==h
    out=Path(a.out).resolve();out.mkdir(parents=True,exist_ok=False)
    cases={};hashes={}
    for retain in (0,1):
        name='retain'+str(retain);summary,events=replay(pred['params'],retain,arith['edge_calendar'])
        file=out/(name+'_events.jsonl');file.write_text(''.join(json.dumps(e,separators=(',',':'))+'\n' for e in events));hashes[name]=sha(file)
        cases[name]=summary
    for file in (ARITH_ROOT/'fp32_rounding').iterdir():
        if file.is_file():(out/file.name).write_bytes(file.read_bytes())
    producer_prep=json.loads((ROOT/'results/rtl/w17_window_epoch9_producer_prepared_20261002/prepared.json').read_bytes())
    originals={Path(p).name:v for p,v in producer_prep['source_origins'].items() if p.startswith('candidate/') and not p.endswith(('tb.sv','transport_body.svh'))}
    selected=dict(originals,**{Path(p).name:p for p in arithmetic.SOURCES})
    # Candidate source/prefetch must take precedence over original arithmetic non-overlapping source list.
    assert selected['ot_chip_v41x_window_kv_prefetch.sv'].startswith('rtl/test/')
    snapshot=out/'sources';snapshot.mkdir()
    for basename,path in selected.items():(snapshot/basename).write_bytes((ROOT/path).read_bytes())
    for path in (BENCH,BODY):(snapshot/Path(path).name).write_bytes((ROOT/path).read_bytes())
    (out/'connected_calendar.svh').write_text(f'localparam integer QE_GO=300, QE_FIRST_CAPTURE={300+arith["edge_calendar"]["capture_sample"][0]}, QE_IDLE={300+arith["edge_calendar"]["idle_sample"]}, PRODUCER_ISSUE={300+arith["edge_calendar"]["issue_sample"]};\n')
    expected={}
    for retain,c in cases.items():
        sub=out/retain;sub.mkdir()
        (sub/'stages.mem').write_text(''.join(f'{n:08x}\n' for n in c['staged_samples']))
        (sub/'starts.mem').write_text(''.join(f'{n:08x}\n' for n in c['starts']))
        (sub/'done.mem').write_text(''.join(f'{n:08x}\n' for n in c['lifecycle_done_samples']))
        (sub/'refills.mem').write_text(''.join(f'{n:08x}\n' for n in c['refill_counters']))
        command=['/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator','--binary','--timing','--build','-j','2','-Wno-fatal','-Wno-WIDTH','-Wno-PINMISSING','--top-module','tb','-GRETAIN='+retain[-1],'-I'+str(out),'-I'+str(snapshot),'--Mdir',str(out/('obj_'+retain))]+[str(snapshot/b) for b in selected]+[str(snapshot/'tb.sv')]
        expected[retain]=dict(compile=command,runtime=[str(out/('obj_'+retain)/'Vtb')],cwd=str(out))
    r=dict(schema='opentallas.window.qdq8_connected_model_preparation.v1',verdict='MODELED_PREPARED_NO_COMPILE_PENDING_PARENT_GO',source_commit=PIN,
      generator_sha256=sha(Path(__file__)),source_sha256=source_pins,candidate_sha256=pred['candidate_sha256'],
      dependencies_sha256={p:sha(ROOT/p) for p in ('tools/w17_window_qdq8_arithmetic_model.py','tools/w17_window_epoch9_producer_prediction.py','tools/w17_window_epoch9_producer_log_reanalysis.py','tools/w17_window_epoch9_timing_model.py')},
      fixture_sha256={p:sha(ROOT/p) for p in (BENCH,BODY)},cases=cases,event_sha256=hashes,backend_params=pred['params'],
      actual_QE=arith['parameters'],source_edge_calendar=arith['edge_calendar'],
      conditional_first_pair_cost={k:dict(QE_accept_to_QK_stage=v['staged_samples'][0]-300,QE_accept_to_QK_lifecycle_done=v['lifecycle_done_samples'][0]-300,QE_accept_to_PV_lifecycle_done=v['lifecycle_done_samples'][1]-300,QK_refill_counter=v['refill_counters'][0],PV_refill_counter=v['refill_counters'][1],clock_model_ps=1000,full_token_rate=None) for k,v in cases.items()},
      composed_boundary='Single step start299; QE accept300; synchronous reads302..317; captures317..332; wait actualQEidle335; packed issue335/firstblock336. New finite backend replay from same reset, no constantfit/freefloor or calibration adjustment.',
      producer='Original full512 QDQ8 inputs from committed fp32_rounding input.mem; originalQE code/scale direct cap wiring. Oracle files assertions only. 32code/scale write intents total,16codefullstrobe+16scaleonebyte; ownslot127 sentinel55 tailbytes masked unchanged. No synthetic QE output.',
      visibility='Source WR commits model mem immediately at column; physical shadow visibility WRcolumn+CWL6250+BURST1024=7274ps. Ack edge is not physical completion. Source admission lowerbound lastWRcolumn+13000ps, not an addedguard/fitted floor. Exact owncode/scale READcolumns recalculated in cases; no7cycleguard.',
      descriptor_stress='One producer row and one step; actual L0-shaped QK/PV descriptors repeated only after lifecycle/source drain, gen1..6(retain0) or1..10(retain1), QK alwayscold/PVone-usehit only. Descriptor stress is not actualcore PC loop/fulltoken or across-token cache. Wrap epoch511->0->1 entirely from >=512actualrowrefills; no seed/force/reset. Retain0 3pairs768coldrows;retain1 5pairs640coldrows.',
      resources=dict(new_hardware_bits=0,new_added_latency_cycles=0,original_QE_BL16_blockdot=16,dormant_chunk_adders=96,QE_buffer_bits=51072,producer_bits=4338,idx_backing_bytes=264320*32,clock_model_ps=1000,refill_credits=8,backend_NPC=32,backend_LENW=4,backend_BEATW=4,backend_TAGW=17,REFPB=3,retained_stage_bits=542720,window_source_bits=606718,extra_fixture_storage='Oracle/input16x1024/16x256/16x8 plus predicteddescriptor arrays max10 and replybitmap13056. Same 17sector delayedvisibilityshadow/32intent ledger. Simulation storage only; no hardware adoption.',
        whole_run_required_seconds=180,compile_budget_total_seconds=150,runtime_case_budget_seconds=5,runtime_cases=2,supervision_reserve_seconds=20,aggregate_memory_max_bytes=4294967296,swap_max_bytes=0,CPU_count=2,file_cap_bytes=268435456),
      preparation=dict(commands=expected,snapshot_sha256={p.name:sha(p) for p in snapshot.iterdir()},snapshot_origins=selected,source_bytes=sum(p.stat().st_size for p in snapshot.iterdir()),no_compile=True,compiler_footprint_unknown=True),
      arithmetic_PASS_receipt='results/rtl/w17_window_qdq8_arithmetic_single_run_20261002/record.json',
      scope='Bounded actualQE->WINDOW/owner mux/KARB/backend/lifecycle healthy correctness. No HBM physical hardware frequency/drain/faultrecovery, numericalattention arithmetic, actualcore program/token performance or adoption. Backend noB/CKV/RoPE competitor.',
      next_gate='Independent source/model/preparation review before new parent compileGO; then one bounded unchangedfixture run perdeclaredretainmode, no fit/retry.')
    (out/'model.json').write_text(json.dumps(r,indent=2)+'\n')
    (out/'files_sha256.json').write_text(json.dumps({str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file()},indent=2)+'\n')
    print(json.dumps({k:{n:v[n] for n in ('last_write_ack','starts','staged_samples','lifecycle_done_samples','refill_counters','final_epoch','read_requests')} for k,v in cases.items()},indent=2))
if __name__=='__main__':main()
