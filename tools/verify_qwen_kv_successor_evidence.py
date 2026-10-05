#!/usr/bin/env python3
"""Source/implementation/artifact preservation; never physical qualification."""
import hashlib
import json
from pathlib import Path
import subprocess
from verify_qwen_kv_bank_groups_evidence import verify as predecessor_verify
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/uarch/qwen_rom_kv_successor_20261002'
def verify():
    predecessor_verify()
    def obj(name):return json.loads((OUT/name).read_text())
    def check(path,digest):
        if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=digest:raise ValueError('pin mismatch: '+path)
    artifacts=obj('artifact-sha256-r1.json')
    for p,h in artifacts.items():check(p,h)
    for p,h in obj('implementation-pins-r1.json').items():check(p,h)
    m=obj('model-r7.json');check('results/uarch/qwen_rom_kv_bank_groups_20261002/model-r4.json',m['predecessor_sha256'])
    for p,h in m['implementation_sha256'].items():check(p,h)
    for p,h in m['source_sha256'].items():
        check(p,h)
        blob=subprocess.check_output(['git','show',m['parent']+':'+p],cwd=ROOT)
        if hashlib.sha256(blob).hexdigest()!=h:raise ValueError('source parent mismatch: '+p)
    if len(m['calendar']['rows'])!=36 or m['admission']['hardware']:raise ValueError('scope/admission')
    for r in m['calendar']['rows']:
        if r['command_count_per_stack']!=[32736]*4 or r['owned_data_and_grant_count_per_stack']!=[65472]*4:raise ValueError('once-only byte debit')
        if r['peak_live_cohorts']>128 or r['peak_words_per_group_lane_pool']>80:raise ValueError('finite cohort/pool credits')
    if m['calendar']['adopted_rate'] is not None or m['physical']['actual_sustained_PHY_Bps'] is not None:raise ValueError('unqualified policy/PHY')
    return dict(verdict='PASS_PRESERVATION_AND_CONDITIONAL_MODEL_ONLY',source_pins=len(m['source_sha256']),
        artifacts=len(artifacts),originals=28,layers=36,physical=False,production=False)
if __name__=='__main__':print(json.dumps(verify(),sort_keys=True))
