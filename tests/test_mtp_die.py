"""MTP-DIE (2026-10-08): die-level homes of the DSpark MTP functions.

HBM r25m: hfd_mtp in the low spine slot and the loader memory chains, outline unchanged, legal, no generated pin
clashes.  S81: the --wfc-hard / --mtp-seq / --mtp-links / --draft options parse AND bind (mtp-draftdie 2026-10-09: the head
sequencer defaults ON, the WFC slab follows WFC_HARD_DEFAULT; the full-die builds take ~10-40 min and run remotely).  Plan: the record's
reconciled die counts and budget terms.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import dsrom_s81_fulldie as S  # noqa: E402
import hbm_accel_die_fp as H  # noqa: E402


def test_hbm_r25m_mtp_and_loader_wiring():
    m = H.build(H.variant_arg('r25m'))
    assert (m['geo']['W'], m['geo']['H']) == (30590.352, 24621.84)          # r25 outline: nothing grows
    by = {it.name: it for it in m['insts']}
    mt = by['hb_mtp']
    assert (mt.w, mt.h) == H.MTP_SLOT and mt.y + mt.h <= by['hb_loader'].y  # below the loader in the spine column
    lg = H._legality(m)
    assert lg['overlaps'] == 0 and lg['outside'] == 0
    assert H.pin_clashes(m) == []
    cls = {}
    for bid, c, bits, eps in m['buses']:
        cls.setdefault(c, set()).update(i for i, _ in eps)
    # every stack's stream service has a loader request and response chain
    for st in ('SW', 'SE', 'NW', 'NE'):
        assert any(f'lq_{st}' in b[0] for b in m['buses']) and any(f'lr_{st}' in b[0] for b in m['buses'])
    assert any(eps[0][0] == 'hb_mtp' or eps[-1][0] == 'hb_mtp' for _, _, _, eps in m['buses'])
    assert H.margin_lint(m)['verdict'] != 'FAIL'


def test_s81_mtp_options_parse():
    ap = S.die_options(argparse.ArgumentParser())
    a = ap.parse_args(['--gen', 'r8', '--die', 'head', '--mtp-seq', '--mtp-links', '5', '--wfc-hard'])
    assert a.mtp_seq and a.mtp_links == 5 and a.wfc_hard
    b = ap.parse_args(['--gen', 'r8'])
    assert b.mtp_seq is None and b.mtp_links == 0 and b.wfc_hard is None and b.draft is None
    c = ap.parse_args(['--gen', 'r8', '--no-mtp-seq', '--no-wfc-hard', '--die', 'layer1', '--draft', 'A'])
    assert c.mtp_seq is False and c.wfc_hard is False and c.draft == 'A'


def test_s81_mtp_options_bind():
    """the options must reach the module globals (a merge once dropped the binding: the flags were silent no-ops)"""
    ap = S.die_options(argparse.ArgumentParser())
    saved = (S.WFC_HARD, S.MTP_SEQ, S.MTP_LINKS, S.DRAFT_SIDE)
    try:
        S.apply_options(ap.parse_args(['--gen', 'r8', '--rev', 'r9', '--die', 'head', '--mtp-links', '5']))
        assert S.MTP_SEQ is S.MTP_SEQ_DEFAULT is True and S.MTP_LINKS == 5
        assert S.WFC_HARD is S.WFC_HARD_DEFAULT          # flips with the one constant when the SOURCE partner closes
        S.apply_options(ap.parse_args(['--gen', 'r8', '--rev', 'r9', '--die', 'head', '--no-mtp-seq', '--wfc-hard']))
        assert S.MTP_SEQ is False and S.WFC_HARD is True
        S.apply_options(ap.parse_args(['--gen', 'r8', '--rev', 'r9', '--die', 'layer1', '--draft', 'B']))
        assert S.DRAFT_SIDE == 'B'
    finally:
        S.WFC_HARD, S.MTP_SEQ, S.MTP_LINKS, S.DRAFT_SIDE = saved
        S.configure('layer')


def test_draft_buses_and_rule():
    sys.path.insert(0, str(ROOT / 'tools'))
    import dsrom_mtp_draft_images as D
    assert D.md2_side('mtp.0.ffn.experts.5.w1.weight') == 'A' and D.md2_side('mtp.1.ffn.experts.0.w2.weight') == 'B'
    assert D.md2_side('mtp.2.ffn.experts.63.w3.weight') == 'A' and D.md2_side('mtp.2.ffn.experts.64.w3.weight') == 'B'
    names = [(a, b) for a, b, *_ in S.P2_BUSES]
    assert len(names) == len(set(names))               # one chain per slab pair (hb_<a>_<b> names are unique)
    assert S.DRAFT_IMAGE['words_per_die'] / S.DRAFT_IMAGE['words_capacity'] == S.DRAFT_IMAGE['fill']


def test_plan_record():
    p = json.loads((ROOT / 'results/arch/mtp_die_20261008/plan.json').read_text())
    rec = p['ds_rom_array']['reconciliation']
    assert rec['dies'] == dict(rack=52, dp1_ep5=64, proposed=40)
    cap = p['ds_rom_array']['topologies'][2]['capacity']
    assert cap['die_A_pairs'] <= cap['die_pairs_available']
    b = p['budget']['ds_rom']
    assert abs(b['verify_us'] + b['draft_us'] + b['seed_commit_us'] - b['step_us']) < 1e-2
    assert p['areas']['wfc']['real_need_mm2'] < p['areas']['wfc']['reservation_mm2']
