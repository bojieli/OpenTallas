import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import hbm_accel_die_fp as H


def test_plan_json_stringifies_tuple_keys():
    rec = dict(variant=dict(pin_centre={('hfd_router', 'ck'): 612.5932, ('hfd_stn_r23', 'rst'): 10.0}),
               nested=[{('a', 1): (1, 2)}], s={3})
    out = json.loads(H.plan_json(rec))
    assert out['variant']['pin_centre'] == {'hfd_router|ck': 612.5932, 'hfd_stn_r23|rst': 10.0}
    assert out['nested'] == [{'a|1': [1, 2]}] and out['s'] == [3]


def test_r25gp_plan_record_serialises():
    # R25GP carries the R25 / r23 tuple-keyed pin_centre: the whole plan record must reach floorplan.json
    m = H.build(H.R25GP, network_probe=True)     # retiled SM grid: labelled probe, as the CLI builds it
    rec = H.plan_record(m)
    assert any(isinstance(k, tuple) for k in rec['variant']['pin_centre'])
    out = json.loads(H.plan_json(rec))
    assert 'hfd_router|ck' in out['variant']['pin_centre']
    assert out['variant']['split_x_masters'].endswith('split_ps/split.json')


def test_psfc_face_clock_taps_ride_the_hbm_clock():
    v = dict(H.R25S, split_x_masters='physical/hbm_accel_die_views/svc/split_psfc/split.json')
    m = H.build(v)
    clk = {b[0]: b for b in m['buses'] if b[1] == 'clock_trunk'}
    taps = [e for b in m['buses'] for e in b[3] if e[1] in ('ckw', 'cke')]
    assert taps and all(e in clk['clk_hbm'][3] for e in taps)
    assert ('svc_SW_s5', 'ckw') in taps and ('svc_SW_s5', 'cke') in taps
