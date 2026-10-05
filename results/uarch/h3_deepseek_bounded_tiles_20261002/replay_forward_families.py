#!/usr/bin/env python3
"""Reproduce synthetic all-family numerical/counter receipts; no payload reads."""
import argparse
from collections import Counter
import gzip
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'tools'))
import h3_deepseek_complete_native as N
import h3_native_microop_adapter as A
import h3_deepseek_bounded_compile as C
spec=importlib.util.spec_from_file_location('source_fixture',ROOT/'tests/test_h3_deepseek_complete_native.py');F=importlib.util.module_from_spec(spec);spec.loader.exec_module(F)


def replay():
    result={}
    for family in sorted(N.FAMILIES):
        p=N.recipe(family,F.TOY,F.ATTR);p.update(family=family,source_attributes=F.ATTR,shape_parameters=F.TOY)
        inputs=F.fixture(p);expected=N.Machine(p,inputs,N.primitive_div).run();got,r=A.execute_ds(p,inputs,(0,'family_v0',0,0,1))
        if r['status'] not in A.PASS_STATUSES:raise ValueError(family+' execution failure')
        for key in expected:
            if not np.array_equal(got[key].reshape(-1).view(np.uint8),expected[key].reshape(-1).view(np.uint8)):raise ValueError(family+' numerical mismatch '+key)
        counts=r['executed_primitive_scalars'];baseline=Counter()
        for i in p['code']:baseline[i['op']]+=max(1,math.prod(i['shape']))
        costs={k:3 for k in counts};costs.update(provider=5,frame=2)
        commands=r['provider']['events']['accepted']
        projection=C.transfer_projection(p)
        if commands>projection['accepted_commands_upper']:raise ValueError('transfer projection undercount '+family)
        result[family]={'actual_receipt':r,'baseline_once_scalar_counts':dict(baseline),'executed_to_baseline_ratio':{'numerator':sum(counts.values()),'denominator':sum(baseline.values())},'512B_selected_provider_commands':commands,'memo_32B_commands':0,'continuation_128B_commands':0,'provider_projection':projection,'calendar':A.finite_calendar(counts,costs,commands),'calendar_costs':costs,'cost_units':'provisional software units, not measured hardware cycles','numerical_bits_equal':True}
    return {'schema':'H3_DS_FORWARD_ALL30_NUMERIC_PROVIDER_CALENDAR_RECEIPT_V1','families':result,'fixture_shapes':F.TOY,'actual_checkpoint_execution':False,'hardware_qualified':False,'source_sha256':{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ['tools/h3_deepseek_streaming_linear.py','tools/h3_deepseek_staged_native.py','tools/h3_native_microop_adapter.py','tools/h3_deepseek_bounded_compile.py','tests/test_h3_deepseek_complete_native.py']}}


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);ap.add_argument('--verify',action='store_true');args=ap.parse_args()
    raw=json.dumps(replay(),sort_keys=True,separators=(',',':')).encode()
    if args.verify:
        if gzip.decompress(args.out.read_bytes())!=raw:raise ValueError('immutable receipt mismatch')
    else:
        if args.out.exists():raise ValueError('refuse overwrite evidence')
        args.out.write_bytes(gzip.compress(raw,mtime=0))
    print('PASS_ALL30_FORWARD_NUMERICAL_TRANSFERS_CALENDARS hardware_qualified=False')
if __name__=='__main__':main()
