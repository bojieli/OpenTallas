#!/usr/bin/env python3
"""Add complete verified pin metadata around unchanged 553406375 timing generator.

Writes only a NEW directory. No RTL build or candidate rerun. Numerical model and
its original model_sha256 remain unchanged; wrapper has its own SHA.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
LEGACY='tools/w17_window_epoch9_timing_model.py'
OLD='results/uarch/w17_window_epoch9_timing_prediction_20261001_attempt1'
FIXTURE='results/uarch/w17_window_epoch9_reproducible_prediction_20261001/baseline_fixture.sv'
PRED_COMMIT='553406375'

def sha(b):return hashlib.sha256(b).hexdigest()

def require_pins(expected,read):
    for path,digest in expected.items():
        if sha(read(path))!=digest:raise ValueError('Source selection/hash mismatch: '+path)


def check_event_contract(events,credits):
    if credits not in (1,8):raise ValueError('Unsupported credits: only pinned1/8 arms')
    issued={};received=set();pending=0;current_row=-1
    for e in events:
        row,sec=e['row'],e['sector'];key=(row,sec)
        epoch=row+1 if credits==8 else 0
        expected_tag=65536|((epoch<<5)|sec if credits==8 else sec)
        if e['tag']!=expected_tag:raise ValueError('Wrong owner/epoch/sector tag')
        address=262144+row*17+sec
        mapped=((address>>2)^(address>>7)^(address>>12))&31
        if e['address']!=address or e['pc']!=mapped or not(0<=row<128 and 0<=sec<=16):
            raise ValueError('Wrong address/PC/geometry')
        if e['kind']=='request':
            if row!=current_row:
                if row!=current_row+1 or pending or (current_row>=0 and (current_row,16) not in received):
                    raise ValueError('Row advance without complete drain')
                current_row=row
            if key in issued or (sec and (row,sec-1) not in issued):raise ValueError('Duplicate/out-of-order issue')
            if sec==16 and not all((row,k) in received for k in range(16)):raise ValueError('Scale issued before code drain')
            issued[key]=e['cycle'];pending+=1
            if pending>credits:raise ValueError('Credit limit exceeded')
        elif e['kind']=='reply':
            if key not in issued or key in received or e['cycle']<=issued[key]:raise ValueError('Unissued/duplicate/early return')
            received.add(key);pending-=1
        else:raise ValueError('Unknown event kind')
    if pending or len(issued)!=2176 or len(received)!=2176:raise ValueError('Incomplete transport drain')


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',required=True);args=ap.parse_args()
    old=json.loads((ROOT/OLD/'prediction.json').read_bytes())
    legacy_pin=subprocess.check_output(['git','show',PRED_COMMIT+':'+LEGACY],cwd=ROOT)
    assert (ROOT/LEGACY).read_bytes()==legacy_pin and sha(legacy_pin)==old['model_sha256']
    require_pins(old['source_sha256'],lambda p:subprocess.check_output(['git','show',old['source_commit']+':'+p],cwd=ROOT))
    require_pins(old['source_sha256'],lambda p:(ROOT/p).read_bytes())
    require_pins(old['candidate_added_sha256'],lambda p:(ROOT/p).read_bytes())
    fixture=(ROOT/FIXTURE).read_bytes()
    assert sha(fixture)==old['baseline_fixture_sha256']
    out=(ROOT/args.out).resolve()
    subprocess.run([sys.executable,str(ROOT/LEGACY),'--out',str(out)],cwd=ROOT,check=True)
    path=out/'prediction.json';new=json.loads(path.read_bytes())
    # Reconstruct all owner-added fields from verified inputs; never rewrite old record.
    new.update(source_sha256=old['source_sha256'],candidate_added_sha256=old['candidate_added_sha256'],baseline_fixture_sha256=sha(fixture))
    for credits in (1,8):
        events=out/f'credit{credits}_events.jsonl'
        assert events.read_bytes()==(ROOT/OLD/events.name).read_bytes()
        check_event_contract([json.loads(x) for x in events.read_text().splitlines()],credits)
    difference={k:dict(old=v,new=new.get(k)) for k,v in old.items() if k!='model_wall_seconds' and new.get(k)!=v}
    assert not difference,difference
    new['metadata_generator_sha256']=sha(Path(__file__).read_bytes())
    new['metadata_generator_path']=str(Path(__file__).relative_to(ROOT))
    new['archived_baseline_fixture']=FIXTURE
    new['preserved_prediction_commit']=subprocess.check_output(['git','rev-parse',PRED_COMMIT],cwd=ROOT,text=True).strip()
    new['preserved_prediction_sha256']=sha((ROOT/OLD/'prediction.json').read_bytes())
    new['reproduction_contract']='All old fields identical except measured model_wall_seconds; event files byte-identical; original model_sha256 retained; complete pins generated and verified, wrapper separately hashed.'
    path.write_text(json.dumps(new,indent=2)+'\n')
    receipt=dict(verdict='PASS_COMPLETE_METADATA_REPRODUCTION_AND_TIMING_IDENTITY',prior_failure='FAIL_METADATA_REPRODUCTION_PRESERVED; original generator omitted owner-added pin fields. Parent found numerical/event identity, no numeric mismatch.',
        preserved_prediction_sha256=new['preserved_prediction_sha256'],original_model_sha256=new['model_sha256'],metadata_generator_sha256=new['metadata_generator_sha256'],new_prediction_sha256=sha(path.read_bytes()),
        old_field_differences_except_wall_seconds=difference,event_sha256=new['event_sha256'],build_or_candidate_rerun=False)
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))

if __name__=='__main__':main()
