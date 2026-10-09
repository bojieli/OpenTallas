"""MTP-DIE (2026-10-08): die-level homes of the DSpark MTP functions.

HBM r25m: hfd_mtp in the low spine slot and the loader memory chains, outline unchanged, legal, no generated pin
clashes.  S81: the --wfc-hard / --mtp-seq / --mtp-links options parse and stay off by default (the full-die builds
take ~10-40 min; their check outputs are committed in results/arch/mtp_die_20261008/checks).  Plan: the record's
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


def test_s81_mtp_options_default_off():
    ap = S.die_options(argparse.ArgumentParser())
    a = ap.parse_args(['--gen', 'r8', '--die', 'head', '--mtp-seq', '--mtp-links', '5', '--wfc-hard'])
    assert a.mtp_seq and a.mtp_links == 5 and a.wfc_hard
    b = ap.parse_args(['--gen', 'r8'])
    assert not b.mtp_seq and b.mtp_links == 0 and not b.wfc_hard


def test_plan_record():
    p = json.loads((ROOT / 'results/arch/mtp_die_20261008/plan.json').read_text())
    rec = p['ds_rom_array']['reconciliation']
    assert rec['dies'] == dict(rack=52, dp1_ep5=64, proposed=40)
    cap = p['ds_rom_array']['topologies'][2]['capacity']
    assert cap['die_A_pairs'] <= cap['die_pairs_available']
    b = p['budget']['ds_rom']
    assert abs(b['verify_us'] + b['draft_us'] + b['seed_commit_us'] - b['step_us']) < 1e-2
    assert p['areas']['wfc']['real_need_mm2'] < p['areas']['wfc']['reservation_mm2']
