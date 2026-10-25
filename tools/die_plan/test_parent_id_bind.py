"""IDs remain ordinary input pins; parent constants preserve the tiny golden graph."""
import json
import re
import shutil
import sys
from pathlib import Path

import pytest
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import bind

pytestmark=pytest.mark.skipif(not shutil.which('docker'),reason='requires Yosys in ORFS docker')


def test_parent_ids_match_golden_and_wrong_id_is_caught(tmp_path):
    src=tmp_path/'source';src.mkdir()
    ex=HERE/'examples'/'bind_tiny'
    for name in ['leaves.sv','par.sv','die.v']:
        (src/name).write_text(re.sub(r'\bid\b','tile_id',(ex/name).read_text()))
    p=json.loads((ex/'die_plan.json').read_text())
    p['asbuilt']['base']=str(src)
    p['asbuilt']['straps']=[r'p\d\.u_b\.tile_id']
    p['partition_types']['ta']['contents']=[dict(inst='u_b',module='lf_b',status='reuse',
        parent_id_straps={'tile_id':dict(width=4,value=5)})]
    plan=src/'plan.json';plan.write_text(json.dumps(p))
    out=tmp_path/'bound'
    for cmd in ['elab','bind','verify']:
        assert bind.main([cmd,str(plan),'--out',str(out),'--mem','4'])==0
    mod=(out/'rtl'/'bt_ta.sv').read_text()
    assert 'input wire [3:0] strap_u_b_tile_id' in mod
    assert 'parameter [3:0] strap_u_b_tile_id' not in mod
    assert '.tile_id({strap_u_b_tile_id[3], strap_u_b_tile_id[2], strap_u_b_tile_id[1], strap_u_b_tile_id[0]})' in mod or '.tile_id(strap_u_b_tile_id[3:0])' in mod
    manifest=json.loads((out/'bind_parent_id_straps.json').read_text())
    assert manifest['instances']['A0']['strap_u_b_tile_id']==dict(width=4,value=5)
    assert manifest['instances']['A1']['strap_u_b_tile_id']==dict(width=4,value=6)
    assert manifest['added_data_cycles']==0
    aud=json.loads((out/'bind_tie_audit.json').read_text())   # OWNER 10-25 B: ties only on declared straps
    assert aud['verdict']=='PASS' and {r[0] for r in aud['rows']}>={'A0','A1'}
    assert 'ot_strap_tie_check {A0} {strap_u_b_tile_id[0]} 1' in (out/'strap_ties_check.tcl').read_text()
    bad=tmp_path/'wrong_id';shutil.copytree(out,bad)
    top=bad/'rtl'/'bind_tiny_bound_top.sv'
    text=top.read_text();old=".strap_u_b_tile_id(4'b0110)";assert old in text
    top.write_text(text.replace(old,".strap_u_b_tile_id(4'b0111)"))
    assert bind.main(['verify',str(plan),'--out',str(bad),'--mem','4'])!=0
