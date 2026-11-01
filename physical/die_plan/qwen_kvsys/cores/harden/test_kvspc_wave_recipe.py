from copy import deepcopy
from pathlib import Path
import json
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import kv_core_wave as W
import kvspc_face_ports as F


def test_raw_current_core_recovers_exact_planned_face():
    root=HERE.parents[4]
    src=root/'results/kv_host_regen_1/rtl/qkd_kvs_pc'
    raw=json.loads((src/'qkd_kvs_pc_core.json').read_text())
    got=F.core_json_update(deepcopy(raw))
    plan=json.loads((HERE.parents[1]/'plan_of_record/pins/qkd_kvs_pc_pins_r27.json').read_text())
    ft={a[k] for a in plan.get('island_ft',{}).get('arcs',[]) for k in ('source','sink')}
    expected={p['name'] for p in plan['pins']} - ft
    assert set(got['pin_class']) == expected
    assert got['pin_class']['pc__land_er_259[259]']=='in'
    assert got['pin_class']['pc__land_er_259[260]']=='in'
    text=F.wrapper((src/'qkd_kvs_pc.sv').read_text(),'qkd_kvs_pc')
    assert text.count('input wire [260:259] pc__land_er_259,')==1
    assert 'input wire [3:0] pc__front_hbm_data' not in text
    assert 'input wire [3:0] pc__return_hbm_data' not in text
    assert ',\n);' not in text


def test_wave_pc_recipe_applies_existing_face_and_clock_contract():
    for mod in ('qkd_kvs_pc','qkd_kvs_pc_h_head_p'):
        flags=W.module_recipe(mod)
        assert '--kvspc-face-ports' in flags
        assert '--kvspc-private-ports' in flags
        assert '--kvspc-core-clock' in flags
    assert W.module_recipe('qkd_kvs_ctl')==[]
