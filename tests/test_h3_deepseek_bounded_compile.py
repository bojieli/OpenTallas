import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import numpy as np
import pytest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import h3_deepseek_bounded_compile as C
import h3_native_microop_adapter as A
import h3_deepseek_complete_native as N
FINAL=ROOT/'results/uarch/h3_deepseek_bounded_tiles_20261002/forward_dispatch_milestone.json.gz'


def test_frozen_full_source_dispatch_and_pins():
    p=json.loads(gzip.decompress(FINAL.read_bytes()))
    assert len(p['PC_dispatch'])==2213 and len(p['coverage']['families'])==30
    assert len(p['templates'])==1127 and p['automatic_scalar_fallback_templates']==0
    assert p['workspace']['rank_cap_bytes']==33554432 and p['workspace']['provider_AW']==27
    assert p['workspace']['base'] is None and not p['latency_admitted']
    for name,digest in p['source_sha256'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest
    pc=next(op for op in p['PC_dispatch'] if op['pc']==127)
    assert pc['family']=='topk_merge'
    for call in pc['calls']:
        t=p['templates'][call['template']]
        assert t['execution_path']=='source_order_live_range_stages'
        assert t['plan']['workspace_upper_bytes']<=33554432
    for op in p['PC_dispatch']:
        assert sum(op['projected_executed_primitive_scalars'].values())>0
        assert op['provider_transfer_projection']['accepted_commands_upper']>0
        assert op['provider_transfer_projection']['continuation_128B_commands']==0
        assert op['recomputed_dependency_scalars']==0


@pytest.mark.parametrize('family',sorted(N.FAMILIES))
def test_full_shape_projection_dominates_executed_toy_transfers(family):
    spec=importlib.util.spec_from_file_location('fixture',ROOT/'tests/test_h3_deepseek_complete_native.py');F=importlib.util.module_from_spec(spec);spec.loader.exec_module(F)
    p=N.recipe(family,F.TOY,F.ATTR);p.update(family=family,source_attributes=F.ATTR,shape_parameters=F.TOY)
    got,r=A.execute_ds(p,F.fixture(p),(0,'projection_v0',0,0,1))
    bound=C.transfer_projection(p)
    assert bound['accepted_commands_upper']>=r['provider']['events']['accepted']
    assert bound['memo_32B_commands']==bound['continuation_128B_commands']==0
