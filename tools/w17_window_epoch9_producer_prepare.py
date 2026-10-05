#!/usr/bin/env python3
"""Prepare pinned producer fixture snapshots and bounded commands. NEVER builds.

Parent bounded-run GO is required after reviewing this source/model/manifest.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT=Path(__file__).resolve().parents[1]
PIN='4e38326d6f361bc85e660f48c59c355e2bb95274'
PRED='results/uarch/w17_window_epoch9_producer_prediction_20261001_attempt3/prediction.json'
BENCH='rtl/test/w17_window_epoch9_producer/'
COPIES='rtl/test/w17_window_epoch9_candidate/'


def sha(b):return hashlib.sha256(b).hexdigest()

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',required=True);a=ap.parse_args()
    pr=(ROOT/PRED).read_bytes();pred=json.loads(pr)
    assert subprocess.check_output(['git','show','HEAD:'+PRED],cwd=ROOT)==pr
    assert pred['verdict']=='MODELED_PREPARED_NOT_BUILT_PENDING_PARENT_GO'
    for collection in ('source_sha256','candidate_sha256','dependency_sha256','prepared_fixture_sha256'):
        for p,h in pred[collection].items():assert sha((ROOT/p).read_bytes())==h
    prior=json.loads((ROOT/'results/uarch/w17_window_epoch9_timing_prediction_20261001_attempt1/prediction.json').read_bytes())
    paths=[*prior['source_sha256'], 'rtl/hdc/v41x/ot_hdc_v41x_window_kv_blocks.sv',
        'rtl/chip/ot_chip_v41x_window_block_guard.sv','rtl/chip/ot_chip_v41x_attn_desc_lifecycle.sv']
    baseline=json.loads((ROOT/'results/uarch/w17_window_epoch9_baseline_comparison_20261001/baseline_record.json').read_bytes())
    out=Path(a.out).resolve();assert shutil.disk_usage(out.parent).free>1024**3
    out.mkdir(exist_ok=False)
    origins={};snapshots={}
    for arm in ('original','candidate'):
        folder=out/arm;folder.mkdir()
        for p in paths:
            origin=COPIES+Path(p).name if arm=='candidate' and (COPIES+Path(p).name) in pred['candidate_sha256'] else p
            data=(ROOT/origin).read_bytes()
            if origin==p:
                assert data==subprocess.check_output(['git','show',PIN+':'+p],cwd=ROOT)
            (folder/Path(p).name).write_bytes(data)
            origins[arm+'/'+Path(p).name]=origin;snapshots[arm+'/'+Path(p).name]=sha(data)
        for name in ('tb.sv','transport_body.svh'):
            data=(ROOT/BENCH/name).read_bytes();(folder/name).write_bytes(data)
            origins[arm+'/'+name]=BENCH+name;snapshots[arm+'/'+name]=sha(data)
    commands={}
    for retain in (0,1):
        commands['retain'+str(retain)]={
            'compile':[baseline['compile']['command'][0],'--binary','--timing','--build','-j','2',
                '-Wno-fatal','-Wno-WIDTH','-Wno-PINMISSING','--top-module','tb',
                '-GRETAIN='+str(retain),'-I'+str(out/'candidate'),'--Mdir',str(out/('obj_retain'+str(retain))),
                *[str(out/'candidate'/Path(p).name) for p in paths],str(out/'candidate/tb.sv')],
            'runtime':[str(out/('obj_retain'+str(retain))/'Vtb')]}
    r=dict(schema='opentallas.window_epoch9.producer_fixture_preparation.v1',
        verdict='PREPARED_NOT_COMPILED_NOT_RUN_AWAITING_PARENT_GO',source_commit=PIN,
        branch_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        prediction_commit=subprocess.check_output(['git','log','-1','--format=%H','--',PRED],cwd=ROOT,text=True).strip(),
        prediction_sha256=sha(pr),source_origins=origins,snapshot_sha256=snapshots,commands=commands,
        original_snapshot='Preserved only for source audit; not selected in candidate command. No full wrapper/core/tile/QE arithmetic compilation.',
        modeled_expected_cases={k:v for k,v in pred['cases'].items() if k.startswith('L0')},
        checks=['Exactly32WRrequests/32ack/32WRcolumns,16fullcode+16singlebyte scales, complete nonpoison newrow through actual producer and guard, historical127prime rows only',
            'Every fullAW address within264320 sectors; WINDOW backendprefix100; exact request/reply/column cycle/address/tag/WE/strobe versus prior model',
            'Negedge backend head snapshots observe actual tcol; shadow17sector oracle applies bytes at WRtcol+7274ps; every own-row READcolumn follows writevisibility and data/strobe expected; row_valid separately logical',
            'Actual descriptor lifecycle generation1then2, service generation bound to acceptance,32beats per QK/PV, masks/user/provenance, source/engine/producer/backend drain',
            'RETAIN0 epochs1..256; RETAIN1 epochs1..128 with PV hit using freshgen2 and zero extra reads; no epoch force/newreset/stepmutation between jobs',
            'Final perPC reads,writes,refresh,ACT match modeled counters; original/candidate pins checked; failure stays separate, no tuning'],
        caps=dict(workers_max=2,address_space_bytes=4*1024**3,total_wall_seconds=180,max_cycles=200000,generated_file_bytes=256*1024**2),
        finite_sizes=dict(backing_bytes=264320*32,source_declared_bits=606718,producer_bits=4338,lifecycle_bits=280,
            visibility_shadow_bits=17*256+17*64,visibility_descriptor_bits=32*(64+256+32+5+1),
            head_snapshot_bits=32*(1+1+30+17+256+32+64),queue_bound_beats=32*(64+32),
            no_added_visibility_guard_bits=0,no_added_critical_cycles=0),
        scope='Modeled/prepared correctness+timing only; no actual producer arithmetic/checkpoint/fulltoken/physicalclock. No immediate-visible row_valid promise. No fault/reset test or policy, Peirce owns recovery. COUNT1 only static source boundary, not actual L0 legal shape.',
        outstanding='SV fixture has not been compiled or executed. Parent reviews predicted calendar, visibility contract and prepared source before explicit bounded-run GO. Preserve any ensuing model/fixture mismatch FAIL.',
        no_build=True,no_original_or_live_edits=True)
    (out/'prepared.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'verdict':r['verdict'],'prediction_sha256':r['prediction_sha256'],'caps':r['caps']},indent=2))
if __name__=='__main__':main()
