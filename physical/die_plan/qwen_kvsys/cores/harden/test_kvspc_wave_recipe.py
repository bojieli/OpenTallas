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
        assert '--two-mode-grt' in flags
    assert W.module_recipe('qkd_kvs_ctl')==[]


def test_clock_profile_is_idempotent_across_parameter_order(tmp_path):
    import kvspc_core_clock as C
    rtl=tmp_path/'rtl';rtl.mkdir()
    for n in ('qkd_static_kv_pc_path_nc.sv','qkd_ctrl_pc_nc.sv','ot_qkd_static_ctrl_pc_emb.sv','ot_qkd_static_kv_timing.sv'):
        (rtl/n).write_text('// CORE_CLOCK common833\n')
    h=rtl/'qkd_static_kv_pc_path_fan_nc_b_head_p.sv'
    h.write_text('module qkd_static_kv_pc_path_fan_nc_b_head_p #(parameter MU=0, CORE_CLOCK=0)(input ck);\n'
                 'qkd_static_kv_pc_path_emb_nc_b #(.MU(MU),.CORE_CLOCK(CORE_CLOCK)) u_pce(.ck(ck));\nendmodule\n')
    p=rtl/'physical_leaf.sv'
    p.write_text('module leaf(input ck);\nqkd_static_kv_pc_path_fan_nc_b_head_p #(.MU(1), .CORE_CLOCK(1), .PC(0)) u_pc(.ck(ck));\nendmodule\n')
    before={f.name:f.read_text() for f in rtl.iterdir()}
    C.apply_kit(tmp_path);C.apply_kit(tmp_path)
    assert {f.name:f.read_text() for f in rtl.iterdir()}==before


def test_head_stale_slices_are_replaced_by_one_live_declaration():
    # Current raw cuts preserve already planned slice names as unused aliases.
    mod='qkd_kvs_pc_h_head_p'
    s=('module '+mod+' (\n    input wire [0:0] ck,\n'
       '    input wire [3:0] pc__front_hbm_data,\n    input wire [3:0] pc__return_hbm_data,\n'
       '    input wire [260:0] pc__land_er,\n    input wire [260:259] pc__land_er_259,\n'
       '    input wire [32:0] pc__ki,\n    input wire [20:15] pc__ki_15,\n    input wire [32:31] pc__ki_31,\n'
       '    input wire rst_n\n);\nleaf u(.hck(ck[0]), .pc__front_hbm_data(pc__front_hbm_data[3:0]),'
       ' .pc__return_hbm_data(pc__return_hbm_data[3:0]), .pc__land_er(pc__land_er[260:0]), .pc__ki(pc__ki[32:0]));\nendmodule\n')
    got=F.wrapper(s,mod,True)
    assert got.count('input wire [260:259] pc__land_er_259,')==1
    assert got.count('input wire [20:15] pc__ki_15,')==1
    assert got.count('input wire [32:31] pc__ki_31,')==1


def test_wave_selected_pin_view_overrides_historical_extraction_slot(tmp_path, monkeypatch):
    from types import SimpleNamespace
    src=tmp_path/'leaf.sv';src.write_text('module qkd_kvs_pc(); endmodule\n')
    cj=tmp_path/'core.json';cj.write_text(json.dumps(dict(module='qkd_kvs_pc',type='old_type',inst='old',files=[str(src)])))
    views=tmp_path/'views.json';views.write_text(json.dumps(dict(plan='plan.json',view_list=[dict(
        view='qkd_kvs_pc@mirror',module='qkd_kvs_pc',type='mirror_type',insts=['mirror_inst','old'],
        core_json=str(cj),hr=False)])))
    calls=[]
    monkeypatch.setattr(W.subprocess,'run',lambda cmd: calls.append(cmd) or SimpleNamespace(returncode=0))
    out=tmp_path/'gen'
    a=SimpleNamespace(views=views,view='qkd_kvs_pc@mirror',repo=tmp_path,out=out,kit_rtl='auto',plan=None,fp_root=[])
    assert W.gen(a,['--util','0.4'])==0
    staged=json.loads((out/'_qkd_kvs_pc_core.json').read_text())
    assert (staged['type'],staged['inst'])==('mirror_type','mirror_inst')
    assert staged['kv_core_wave']['source_type']=='old_type'
    assert (out/'_kit_rtl/mirror_type/kit_rtl.json').is_file()
    assert calls[0][-4:]==['--plan-inst','mirror_inst','--util','0.4']
    assert '--two-mode-grt' in calls[0]
