#!/usr/bin/env python3
"""TOK-DS-11: lower_xs.source_frame_schedule gate for as-built band frames (col_h*_l4_lp_asb_{x,nx}).

An as-built frame compiles only with its own extracted schedule AND a PASS plan-latency check bound (sha256) to that
exact schedule file; missing / FAIL / unbound checks raise.  Also checks the committed extraction for col_h10_asb_x
(validation on the LP twin all PASS; plan check FAIL lists the frame_int seams) so the compiler fails closed on it.
"""
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'tools/s81_dv/layer_prog'), str(ROOT / 'tools/s81_dv')]
import lower_xs as X

M = 'col_h10_l4_lp_asb_x'


def expect_raise(fn, needle):
    try:
        fn()
    except ValueError as e:
        assert needle in str(e), (needle, str(e))
        return
    raise AssertionError('no ValueError: ' + needle)


def main():
    n = 0
    assert X.base_master(M) == 'col_h10' and X.base_master('col_h9_l4_lp_asb_nx') == 'col_h9'
    assert X.base_master('col_h10_l4_lp') == 'col_h10' and X.is_asbuilt(M) and not X.is_asbuilt('col_h10_l4_lp')
    n += 1
    for gb_master in ('col_h10_l4_lp_gb', M + '_gb'):
        expect_raise(lambda: X.source_frame_schedule(gb_master), 'legacy frame calendars cannot qualify'); n += 1
    with tempfile.TemporaryDirectory() as d:
        os.environ['OT_XS_ASB_SCHEDULE_DIR'] = d
        source = Path(d) / 'frame.sv'
        source.write_text('legacy739')
        os.environ['OT_S81_SELECTED_SOURCE_ROOT'] = d
        hashes = {'frame.sv': hashlib.sha256(source.read_bytes()).hexdigest()}
        expect_raise(lambda: X.source_frame_schedule(M), 'needs its extracted frame schedule'); n += 1
        sp, cp = Path(d) / (M + '_schedule.json'), Path(d) / (M + '_check.json')
        sp.write_text(json.dumps(dict(schema='opentallas.s81.frame_schedule.v1', source_sha256=hashes)))
        cp.write_text(json.dumps(dict(verdict='FAIL', fails=['frame_int r0->r1 (band port to band port)'],
                                      schedule_sha256=hashlib.sha256(sp.read_bytes()).hexdigest())))
        expect_raise(lambda: X.source_frame_schedule(M), 'frame_int r0->r1'); n += 1
        cp.write_text(json.dumps(dict(verdict='PASS', fails=[], schedule_sha256='0' * 64)))
        expect_raise(lambda: X.source_frame_schedule(M), 'not bound'); n += 1
        cp.write_text(json.dumps(dict(verdict='PASS', fails=[], schedule_sha256=hashlib.sha256(sp.read_bytes()).hexdigest())))
        assert X.source_frame_schedule(M) == sp; n += 1
        # Real source mutation: changing selected739 to737 at the SAME path cannot reuse the old PASS receipt.
        source.write_text('GB737')
        expect_raise(lambda: X.source_frame_schedule(M), 'differs from selected source'); n += 1
        hashes['frame.sv'] = hashlib.sha256(source.read_bytes()).hexdigest()
        candidate = dict(source_sha256=hashes, station_inputs={'e0': dict(go_boundary_edges=1,
                         required_go_issue_advance_edges=1, native_provider_qualified=False)})
        expect_raise(lambda: X.qualify_frame_source(candidate, M, d), 'qualified one-edge-early'); n += 1
        candidate['station_inputs']['e1'] = {}
        expect_raise(lambda: X.qualify_frame_source(candidate, M, d), 'mixed legacy/GB'); n += 1
        expect_raise(lambda: X.qualify_frame_source({}, M, d), 'lacks exact source'); n += 1
        del os.environ['OT_XS_ASB_SCHEDULE_DIR']
        del os.environ['OT_S81_SELECTED_SOURCE_ROOT']
    c = json.loads((ROOT / 'results/arch/s81_dv_1016/frame_lp/asb_schedule' / (M + '_check.json')).read_text())
    assert c['validation']['links'] > 0 and not c['validation']['fails'], c['validation']['fails']
    assert c['verdict'] == 'FAIL' and all(f.startswith('frame_int ') for f in c['fails']), c['fails']
    expect_raise(lambda: X.source_frame_schedule(M), 'frame_int'); n += 1
    print(f'test_asb_schedule_gate {n}/{n} PASS')


if __name__ == '__main__':
    main()
