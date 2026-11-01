import pytest
import copy,json
from pathlib import Path
from layer_prog.emitted_leaf_routes import Wiring
from layer_prog.emitted_v_bridges import compose


def test_actual_gunit_lane_pad_payload_and_epoch_mapping():
    source='''wire [275:0] xtier_i0_b;
wire xtier_i0_eb;
wire [275:0] xtier_i0_q;
wire xtier_i0_eq;
ot_dp_dly #(.W(277), .D(1)) u_lpad_xtier_i0 (.clk(clk), .d({xtier_i0_eb, xtier_i0_b}), .q({xtier_i0_eq, xtier_i0_q}));
'''
    w=Wiring(source)
    for i in range(276):assert w.trace(('xtier_i0_q',i),{'xtier_i0_b'})==('xtier_i0_b',i,1)
    assert w.trace(('xtier_i0_eq',0),{'xtier_i0_eb'})==('xtier_i0_eb',0,1)
    with pytest.raises(ValueError,match='width differs'):Wiring(source.replace('.W(277)','.W(276)'))


def test_actual_full_V_path_cannot_skip_an_internal_gunit_link():
    root=Path(__file__).resolve().parents[3]/'results/token_pass/norm_leaf_calendar_1101'
    nx=json.loads((root/'nx_routes_kva3_v2.json').read_text())
    v=json.loads((root/'v_bridge_kva3.json').read_text())
    paths=compose(nx,v)
    assert len(paths)==16 and sum(len(r['primitive_terms'])for r in paths)==18
    assert all(r['source_local_forward_edges']is None for r in paths)
    bad=copy.deepcopy(v);bad['gunit_local_links'].pop()
    with pytest.raises(ValueError,match='actual middle V wire absent'):compose(nx,bad)
