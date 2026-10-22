#!/usr/bin/env python3
"""Q-XPF (from claude/qw-slice3-1019 test_land_lag_sim.py; ROOT4 merge kept main's KVR-LANDLAG file and moved these here):
land_lag_sim.py annotate / ages / xpf-check on a two-landing toy slice."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import land_lag_sim as L  # noqa: E402

LANES = dict(lanes=[dict(bid='dvw_hr_wi', n=25, E=18, E_sta=7, K=2, landing='rly_dvw_hr_wi_24'),
                    dict(bid='dvw_cmd_wi', n=25, E=18, E_sta=7, K=2, landing='rly_dvw_cmd_wi_24'),
                    dict(bid='dvw_ss_wo', n=22, E=16, E_sta=6, K=0, landing='rly_dvw_ss_wo_21'),
                    dict(bid='dvw_ag_wo', n=22, E=16, E_sta=6, K=0, landing='rly_dvw_ag_wo_21'),
                    dict(bid='x', n=1, E=1, E_sta=1, K=1, landing='rly_x_0')])


def _slice(tmp, extra=''):
    S = tmp / 's'
    S.mkdir()
    glue = tmp / 'die_glue.sv'
    glue.write_text('module qfd_landh_4_NE_65x30 (input wire ckf);\n    ot_qfd_land #(.W(4), .D(4), .FIRST(0)) u_land ();\n'
                    'endmodule\n')
    (S / 'top.sv').write_text('  qfd_landh_4_NE_65x30 rly_dvw_hr_wi_24 (.ckf(a));\n  qfd_landh_4_NE_65x30 rly_x_0 (.ckf(a));\n' + extra)
    (S / 'top.f').write_text(f'{glue}\n/src/rtl/qwen_split/qfd_fwd_lane.sv\n{S}/top.sv\n')
    lanes = tmp / 'fwd_lanes.json'
    lanes.write_text(json.dumps(LANES))
    return S, lanes


def test_annotate_and_ages(tmp_path):
    S, lanes = _slice(tmp_path)
    r = L.annotate(S, lanes)
    assert {x['inst']: x['LAG'] for x in r['landings']} == {'rly_dvw_hr_wi_24': 5, 'rly_x_0': 0}
    t = (S / 'top.sv').read_text()
    assert 'qfd_landh_4_NE_65x30 #(.SIM_LAG(5)) rly_dvw_hr_wi_24 (' in t and '#(.SIM_LAG(0)) rly_x_0 (' in t
    g = (S / 'die_glue_lag.sv').read_text()
    assert '#(parameter integer SIM_LAG = 0)' in g and 'ot_qfd_land_lag #(.LAG(SIM_LAG), .W(4)' in g
    f = (S / 'top.f').read_text().splitlines()
    assert f[0].endswith('die_glue_lag.sv') and f[2] == '/src/rtl/qwen_split/ot_qfd_land_lag.sv'
    a = L.ages(lanes)
    assert (a['R_CMD'], a['R_HR'], a['R_SS'], a['R_AG'], a['XPF_TRANSPORT_EDGES']) == (19, 19, 17, 17, 20)


def test_annotate_fails_closed_without_lane_row(tmp_path):
    S, lanes = _slice(tmp_path, '  qfd_landh_4_NE_65x30 rly_unknown_3 (.ckf(a));\n')
    try:
        L.annotate(S, lanes)
    except SystemExit as e:
        assert 'rly_unknown_3' in str(e)
    else:
        raise AssertionError('annotate accepted a landing without a lane row')


def test_xpf_check(tmp_path):
    S, lanes = _slice(tmp_path)
    L.annotate(S, lanes)
    p = tmp_path / 'p.json'
    p.write_text(json.dumps(dict(masters=dict(qfd_tt_ctlm_dv=dict(XPF_TRANSPORT_EDGES=20)))))
    log = tmp_path / 'run.log'
    log.write_text('SMOKE_XPF hr lane edges 19 (x); XPF_TRANSPORT_EDGES elaborated 20 (expected 20 = 1 + lane)\n')
    assert L.xpf_check(log, S, lanes, p)['verdict'] == 'PASS'
    log.write_text('SMOKE_XPF hr lane edges 15 (x); XPF_TRANSPORT_EDGES elaborated 20 (expected 16 = 1 + lane)\n'
                   'OT_QFD_LAND_FAULT tb.dut.rly_dvw_hr_wi_24.u_land LAG 0 at 1\n')
    r = L.xpf_check(log, S, lanes, p)
    assert r['verdict'] == 'FAIL' and r['ctlm_land_faults'] == ['rly_dvw_hr_wi_24'] and len(r['fails']) == 2
