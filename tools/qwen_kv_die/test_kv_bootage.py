#!/usr/bin/env python3
"""KV-BOOTAGE 10-19: boot-age image / check (kv_bootage.py) and the die cfg image with age words."""
import copy
from pathlib import Path

import kv_bootage as KB
import kv_static_kvjf_join as F

ROOT = Path(__file__).resolve().parents[2]
STACKS = ('WS', 'WN', 'ES', 'EN')


def sched(rt=17, dq=0, fia=108, lead=(37, 37), fdly=49):
    """the KVR-DERIVE base-run numbers (V port RT 16-17, pair FIRST_INPUT_AGE 107-108, PV_LEAD 37, F_DLY 49)"""
    vp = {f'vport_{st}_{k}': dict(RT=rt - (k % 2), DQ=dq + (k % 2), sides=[rt - 9, rt - 9], sides_equal=True)
          for st in STACKS for k in range(4)}
    return dict(vport=vp, pv=dict(RL=fia - 1, FIRST_INPUT_AGE=fia, W=[82]),
                attn=dict(PV_LEAD_by_pair=list(lead), PV_LEAD=max(lead), F_DLY=fdly, pvfst=40, pvp=[3, 3],
                          pvfin_start_align=[0, 0], fin=10, face_land_fin=1), ectl={})


TILE = dict(ECTL_QK_ISSUE_AGE=91)


def test_image_words_and_layout():
    img = KB.image_ages(sched(), TILE)
    assert img['error'] is None and len(img['words']) == KB.NAGE
    w = img['words']
    assert w[0] == 37 | (49 << 8) | ((91 - 34) << 16) | ((108 - 1 - 19) << 24)
    assert w[1] == w[2] == 108
    assert w[3] == 17 | (0 << 8) and w[4] == 16 | (1 << 8)          # vport_WS_0, vport_WS_1
    assert w[3 + KB.vport_index('vport_EN_3')] == 16 | (1 << 8)


def test_check_pass_mismatch_bound():
    s = sched()
    img = KB.image_ages(s, TILE)
    assert KB.check_image(img, s, TILE) == []
    s2 = copy.deepcopy(s)
    s2['vport']['vport_ES_2']['RT'] = 18                             # a post-station stage moved one V port
    ids = {f['id'] for f in KB.check_image(img, s2, TILE)}
    assert ids == {'BOOT_AGE_MISMATCH'}
    s3 = sched(rt=40)                                                # beyond the 31-deep slot line
    img3 = KB.image_ages(s3, TILE)
    assert img3['words'] is None and 'VPORT_RT' in img3['error']
    assert 'BOOT_AGE_BOUND' in {f['id'] for f in KB.check_image(img3, s3, TILE)}
    s4 = sched(lead=(37, 36))
    assert 'PV_LEAD_PAIR_EQ' in {f['id'] for f in KB.check_image(KB.image_ages(s4, TILE), s4, TILE)}


def test_die_cfg_image_with_ages():
    a = [1] * 32
    w = F.die_cfg_image(a, a, a, [0] * 43, 1, ages=KB.image_ages(sched(), TILE)['words'])
    assert len(w) == 32 + 43 + 1 + 19 + 1 and w[-1] == F.DIE_CFG_SEAL and w[32 + 43] == 1
    assert w[32 + 43 + 1] == KB.image_ages(sched(), TILE)['words'][0]
    try:
        F.die_cfg_image(a, a, a, [0] * 43, 1, ages=[0] * 18)
        raise AssertionError('short age list accepted')
    except ValueError:
        pass


def test_pvw_variant_anchors():
    for f in ('rtl/qwen_sys/split_20261014/qkd_pvw_die_t.sv', 'rtl/qwen_sys/split_20261014/qkd_pvw_die_t_f.sv'):
        p = ROOT / f
        if not p.exists():
            continue
        t = KB.pvw_variant(p.read_text())
        assert 'module qkd_pvw_die_tb #(' in t and '.cfg_fia(cfg_age[8*PAIR+:8])' in t
        assert (ROOT / KB.pvw_file(f)).read_text() == t, f'{KB.pvw_file(f)} stale: kv_bootage.py --pvw {f}'


if __name__ == '__main__':
    for n, fn in list(globals().items()):
        if n.startswith('test_'):
            fn()
    print('test_kv_bootage PASS')
