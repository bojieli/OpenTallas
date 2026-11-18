"""KV-KT-E0 11-18: the kt station depth law (kv_head_kst) and its two consumers (kv_qkh_safe32 HXK / D_QK)."""
import importlib
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


def _fresh(env):
    old = {k: os.environ.get(k) for k in ('OT_KV_HEAD_KST', 'OT_KV_QKH_SAFE32')}
    for k in old:
        os.environ.pop(k, None)
    os.environ.update(env)
    try:
        import kv_head_kst
        import kv_qkh_safe32
        importlib.reload(kv_head_kst)
        importlib.reload(kv_qkh_safe32)
        return (kv_head_kst.depth(), kv_qkh_safe32.capture_hxk(), kv_qkh_safe32.calendar_d_qk(91),
                kv_qkh_safe32.data_edges())
    finally:
        for k, v in old.items():
            os.environ.pop(k, None)
            if v is not None:
                os.environ[k] = v


def test_default_is_today():
    assert _fresh({}) == (0, 13, 57, 0)


def test_depth_two_moves_hxk_and_d_qk_by_two():
    assert _fresh({'OT_KV_HEAD_KST': '2'}) == (2, 15, 59, 0)
    assert _fresh({'OT_KV_HEAD_KST': '1'}) == (1, 14, 58, 0)


def test_composes_with_the_safe32_lane_edges():
    assert _fresh({'OT_KV_HEAD_KST': '2', 'OT_KV_QKH_SAFE32': '1'}) == (2, 17, 61, 2)


def test_bad_depth_fails_closed():
    for v in ('3', '-1', 'x'):
        try:
            _fresh({'OT_KV_HEAD_KST': v})
        except ValueError:
            continue
        raise AssertionError(f'OT_KV_HEAD_KST={v} accepted')


def test_leaves_and_flops():
    import kv_head_kst as K
    lv = K.leaves(2)
    assert len(lv) == 32 and lv[0] == (0, 'u_kst0', True) and lv[5] == (2, 'u_kst1', False)
    assert K.flops(2) == dict(parent=34 * 2 * 14, e0=34 * 2 * 2)
    assert K.flops(0) == dict(parent=0, e0=0)
    assert K.flops(2, heads=128)['parent'] == 121856


def test_generated_heads_carry_the_named_leaves_and_are_fresh():
    import head_st_rtl as G
    txt = G.generate_kst()
    assert G.OUT_KST.read_text() == txt
    for m in ('ot_qkh_head_native_r4_kst', 'ot_qkh_head_native_r4_s_kst', 'ot_qkh_head_native_r4_ft_s_kst',
              'ot_qkh_head_native_r4_s_lk_kst', 'ot_qkh_head_native_r4_ft_s_lk_kst'):
        assert txt.count(f'module {m} #(') == 1
    assert txt.count(' u_kst0\n') == 5 and txt.count(' u_kst1\n') == 5
    assert txt.count('parameter integer KT_ST=0,parameter integer KT_MUT=0') == 5
    # the source heads keep their text (pinned sha256 in the token vehicles)
    assert 'KT_ST' not in G.OUT.read_text() + G.OUT_LK.read_text() and 'u_kst' not in G.OUT.read_text() + G.OUT_LK.read_text()


def test_relay_regex_names_both_stages_of_a_lane():
    import kv_head_kst as K
    rx = re.compile('^(' + K.RELAY_MID_RE_ALT + ')[.]')
    assert rx.match('u_bound.u_head1_g_t_7_u_kst0.g_r.r[3]')
    assert rx.match('u_bound.u_head0_g_t_15_u_kst1.g_r.r[33]')
    assert not rx.match('u_bound.u_head0_g_t_15_u_stk.u_rkd.r[0]')
