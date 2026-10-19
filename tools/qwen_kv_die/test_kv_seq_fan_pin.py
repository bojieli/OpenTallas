"""DIE-KV-REPLACE 10-19: kv_die's seq fan leaf pin homes match kv_expand.SEQ_S_PLAN and the krs top-lane waypoints."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import kv_die as K      # noqa: E402
import kv_expand as E   # noqa: E402


def test_fan_homes_match_expand_plan():
    for k in range(4):
        assert K.SEQ_FAN_HOMES[k] == E.SEQ_S_PLAN[f'g_fan[{k}].u_fan']


def test_seq_fan_pin_e_stack(monkeypatch):
    monkeypatch.setenv('OT_KV_SEQ_FAN_PIN', '1')
    monkeypatch.setenv('OT_KV_EXPAND', 'qkd_rhead,qkd_seq_st')
    it = K.F.Inst('seq', 'qkd_seq', 1000.0, 2000.0, 604.8, 475.2, 'R0')
    x, y = K._seq_fan_pin(it, 'af_ES')
    assert abs(x - (1000.0 + 518.4 + 32.4)) < 1e-6 and abs(y - (2000.0 + 259.2 + K.SEQ_FAN_PIN_Y)) < 1e-6
    assert K._seq_fan_pin(it, 'kvn_ES') is None
    monkeypatch.setenv('OT_KV_EXPAND', 'qkd_rhead')
    assert K._seq_fan_pin(it, 'af_ES') is None


def test_krs_top_lane_only_top_engine(monkeypatch):
    monkeypatch.setenv('OT_KV_KRS_TOP_LANE', '1')
    m = dict(geo=dict(grp_y={'ES': (100.0, 1000.0)}), insts=[
        K.F.Inst('astk_ES', 'qkd_astk', 500.0, 100.0, 200.0, 900.0, 'MY'),
        K.F.Inst('ectl_ES_7', 'qkd_ectl', 200.0, 700.0, 100.0, 50.0, 'R0')])
    assert K._krs_top_lane(m, 'krs_ES_6') is None
    wp = K._krs_top_lane(m, 'krs_ES_7')
    assert wp[0][1] == wp[1][1] == 1000.0 + 259.2 and wp[1][0] == wp[2][0] == 200.0 - 648.0 and wp[2][1] == 725.0
