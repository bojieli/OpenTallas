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
