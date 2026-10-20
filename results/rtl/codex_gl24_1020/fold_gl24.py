#!/usr/bin/env python3
"""Fold only the four layers with a complete, strict sixteen-owner receipt."""
import json
import sys
from pathlib import Path

root=Path(__file__).resolve().parents[3]
receipt=json.loads((Path(__file__).parent/'gl24_collection.json').read_text())
assert receipt['all64_PASS'] and set(receipt['layers'])=={'L24','L28','L32','L36'}
path=root/'results/token_pass/measured_s81_1019/elements/GATH.json'
record=json.loads(path.read_text())
gather=next(op for op in record['ops'] if op['op']=='attn.gather')
old_by_old=gather['by_old'].copy()
for layer,data in receipt['layers'].items():
    assert data['all16_PASS'] and len(data['views'])==16
    assert set(data['views'])=={f'{d},{s}' for d in range(4) for s in range(4)}
    gather.setdefault('per_layer',{})[layer]=data['worst_span']
    gather.setdefault('views',{})[layer]=data['views']
assert gather['by_old']==old_by_old
gather['shape']+='; L24/L28/L32/L36 re-index fixtures (L20 compressed KV including this token appended row, 512 real selected rows) each measured across all16 owner views; exact per-layer worst only'
gather['evidence']+='; results/rtl/codex_gl24_1020/gl24_collection.json + out/*.log and cases/*/case.json'
prefix=gather['note'].split('L24..L36 (re-index, old 811):')[0].rstrip()
gather['note']=prefix+' L24/L28/L32/L36 now each have all16 genuine released-fixture owner views, checked score/SE/PV values and zero faults. Only these measured per_layer entries change; the old811 fallback for any other layer remains. HBM model latency40 and existing splice edge obligations are unchanged.'
gather['gl24_receipt']=dict(exe_sha256=receipt['exe_sha256'],all64_PASS=True,full_layer_token_qualification=False,
                           fixture_source='released checkpoint dba1be0a + ctx1048576_seed20260930; own layer selection and L20 compressed state',
                           job='ep6 oth-ubuntu-2694552-1792485038 plus four nominal00 units in README',
                           agent_branch=sys.argv[1])
record['written']='2026-10-20 PT'
record['agent_branch']=sys.argv[1]
path.write_text(json.dumps(record,indent=1)+'\n')
print(json.dumps(gather['per_layer'],sort_keys=True))
