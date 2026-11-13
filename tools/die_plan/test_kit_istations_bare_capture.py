"""Direct native-leaf links select existing coherent CS bundles before flattening."""
import kit_istations as KI
import leaf_cs_depth as LCD
import pytest


def row(launch, capture, depth=2):
    return dict(conn="core:" + capture, launch="core:" + launch, capture=capture,
                bits=32, regs_um=[[100,100]]*depth)


@pytest.mark.parametrize("launch,capture,want", [
    ("u_lf.u_ve.u_m.a_val", "u_lf.u_vs", ("ve", False, None)),
    ("u_lf.u_ve.u_m.o_y", "u_lf.u_vs", ("ver", True, None)),
    ("u_lf.u_vn.u_a.wl_d", "u_lf.u_vp.u_b1", ("vni", False, None)),
    ("u_lf.u_rxsf.i_v", "u_lf.u_vs", ("ra", False, None)),
    ("u_lf.u_rxsf.i_x", "u_lf.u_vs", ("ra", False, None)),
    ("u_lf.u_vs.sw_v", "u_lf.u_vsw", ("sw", True, None)),
    ("u_lf.u_vs.sw_w", "u_lf.u_vsw", ("sw", True, None)),
    ("u_lf.u_vs.sw_lim", "u_lf.u_vsw", ("sw", True, None)),
    ("u_lf.u_vs.sw_vi", "u_lf.u_vsw", ("swr", False, None)),
])
def test_bare_capture_uses_actual_bundle_role(launch,capture,want):
    assert KI.core_class(row(launch,capture)) == want


def test_bus_input_is_not_invented_as_an_individual_pin_chain():
    assert KI.core_class(row("u_lf.u_vn.u_b.n_go", "bus:leafdn_i0")) == (None,None,None)


def test_depth_stage_gate_sees_coherent_class_maximum():
    rows=[row("u_lf.u_ve.u_m.a_val","u_lf.u_vs",2),
          row("u_lf.u_ve.u_m.a_v","u_lf.u_vs",1),
          row("u_lf.u_vs.sw_vi","u_lf.u_vsw",1)]
    assert LCD.plan_depths(dict(internal_stations=rows)) == ({"ve":2,"swr":1},{"ve":[1,2]})


def test_existing_strict_gate_rejects_unrealized_core_rows(tmp_path):
    import json
    tn="ot_s81sl_leaf__t28"
    bad=row("u_lf.u_unknown.payload", "u_lf.u_vs",2)
    t=dict(hard_cores=[1], internal_stations=[bad])
    (tmp_path/f"s81p_{tn}.sv").write_text("module native_leaf; endmodule")
    errors,_=LCD.check(dict(partition_types={tn:t}),tmp_path,types=[tn])
    assert any("unrealized core station" in e and "2 planned registers" in e for e in errors)
    assert LCD.unmapped_core_rows(dict(internal_stations=[dict(conn="bus:leafdn_i0",regs_um=[[1,2]])])) == []


def test_source_stage_refuses_unmapped_register_claim_before_elaboration():
    import stage_lfcs_netlist as SN
    tn="ot_s81sl_leaf__t28"
    p=dict(partition_types={tn:dict(hard_cores=[1],internal_stations=[row("u_lf.u_unknown.payload","u_lf.u_vs")])},
           partitions=[dict(name="s_0N_L1",type=tn)])
    with pytest.raises(SystemExit,match="no RTL class"):
        SN.leaf_depths(p)
