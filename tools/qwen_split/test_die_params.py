#!/usr/bin/env python3
"""QLB-GEN 10-18 (LAYERBENCH G-C1) unit test: compiler-assigned die master parameters (tools/qwen_split/die_params.py).

  python3 tools/qwen_split/test_die_params.py      (repository root; also collected by pytest)
"""
import json, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'tools' / 'qwen_split')]
import die_port_bind as DPB  # noqa: E402
import die_params as P       # noqa: E402

DIE = """module qfd_die ();
  wire [452:0] n_dvw_hr_wi;
  wire [452:0] n_dvw_hr_wi__r1;
  wire [452:0] n_dvw_hr_wi__r2;
  qfd_tt_ctlm_dv tt_ctlm (.hr(n_dvw_hr_wi), .ck(n_clk));
  qfd_rlyh0_453_WE_80x30 rly_dvw_hr_wi_0 (.a(n_dvw_hr_wi), .b(n_dvw_hr_wi__r1), .ck(n_clk));
  qfd_landh_453_NE_80x30 rly_dvw_hr_wi_1 (.a(n_dvw_hr_wi__r1), .tie_hi(n_hi), .k0(n_hi), .k1(n_hi), .k2(n_lo), .tie_lo(n_lo), .b(n_dvw_hr_wi__r2));
  qfd_dv_slice2_w dvs_W5 (.hr_wi(n_dvw_hr_wi__r2));
  qfd_d2d_static d2d_rom (.ck(n_clk));
endmodule
"""
PB = dict(masters={'qfd_tt_ctlm_dv': dict(rtl='rtl/qwen_dv/qfd_tt_ctlm_dv.sv'),
                   'qfd_d2d_static': dict(rtl='rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_dies.sv')})


def mods(f, name):
    return {m.name: m for m in DPB.parse_modules((ROOT / f).read_text(), f)}[name]


def test_transport_value():
    assert P.xpf_transport_edges([('dvw_hr_wi', dict(n=25, E=13, K=5))])[0] == 15      # fwd: 1 + E + 1 (landing o)
    assert P.xpf_transport_edges([('dvw_hr_wi', dict(n=25))])[0] == 26                  # plain: 1 + n
    assert P.xpf_transport_edges([('dvw_hr_wi', None)])[0] == 1                         # direct: the pin register
    for bad in ([], [('a', dict(n=2)), ('b', dict(n=3))]):
        try:
            P.xpf_transport_edges(bad)
            raise AssertionError(f'accepted {bad}')
        except ValueError:
            pass


def test_txdp_image():
    v, r = P.txdp_from_image()
    assert v == 0x09010308 and r['ports'] == [8, 3, 1, 9] and r['die_stages'], r


def test_trapped_sentinels():
    assert set(P.trapped_params(mods('rtl/qwen_dv/qfd_tt_ctlm_dv.sv', 'qfd_tt_ctlm_dv'))) == {'XPF_TRANSPORT_EDGES'}
    assert set(P.trapped_params(mods('rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_dies.sv', 'qfd_d2d_static'))) == {'TXDP'}


def _audit(params, E=3):
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        (d / 'die.v').write_text(DIE)
        (d / 'pb.json').write_text(json.dumps(PB))
        (d / 'fwd_lanes.json').write_text(json.dumps(dict(lanes=[dict(bid='dvw_hr_wi', n=2, E=E, K=3)])))
        if params is not None:
            (d / 'die.v.params.json').write_text(json.dumps(dict(masters=params)))
        return P.audit(d / 'die.v', d / 'pb.json', lanes=d / 'fwd_lanes.json')


def test_audit_pass_and_fail_closed():
    good = {'qfd_tt_ctlm_dv': dict(XPF_TRANSPORT_EDGES=5, STAGE_ME=1), 'qfd_d2d_static': dict(TXDP=0x09010308)}
    r = _audit(good)
    assert r['verdict'] == 'PASS' and r['xpf']['XPF_TRANSPORT_EDGES'] == 5 and r['xpf']['sinks'] == ['dvs_W5.hr_wi'], r
    r = _audit(None)                                                   # as built before G-C1: no sidecar
    assert r['verdict'] == 'FAIL' and len(r['fails']) == 3, r['fails']
    r = _audit(dict(good, qfd_tt_ctlm_dv=dict(XPF_TRANSPORT_EDGES=26, STAGE_ME=1)))  # the smoke's relay count (wrong for a fwd lane)
    assert r['verdict'] == 'FAIL' and 'XPF_TRANSPORT_EDGES 26 != 5' in r['fails'][0], r['fails']
    r = _audit(dict(good, qfd_d2d_static=dict(TXDP=0x09010306)))   # dv2f14bq as GEN'd on the SC_TX 0 image
    assert r['verdict'] == 'FAIL' and 'TXDP' in r['fails'][0], r['fails']
    r = _audit(dict(good, qfd_tt_ctlm_dv=dict(XPF_TRANSPORT_EDGES=5)))   # Q-DIE14: as built STAGE_ME 0 (no deployment image)
    assert r['verdict'] == 'FAIL' and 'STAGE_ME' in r['fails'][0], r['fails']


def test_gen_params():
    out, rec = P.gen_params([('tt_ctlm', 'qfd_tt_ctlm_dv'), ('d2d_rom', 'qfd_d2d_static')],
                            [('dvw_hr_wi', dict(n=25, E=13, K=5))])
    assert out['qfd_tt_ctlm_dv']['XPF_TRANSPORT_EDGES'] == 15 and out['qfd_tt_ctlm_dv']['STAGE_ME'] == 1 and out['qfd_d2d_static']['TXDP'] == 0x09010308
    assert P.gen_params([('x', 'other')], [])[0] == {}


if __name__ == '__main__':
    for k, f in list(globals().items()):
        if k.startswith('test_'):
            f()
            print('PASS', k)
