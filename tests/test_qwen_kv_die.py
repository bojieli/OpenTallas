"""kv-die 2026-10-09: the KV-die generator and the ROM <-> KV contract stay consistent."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tools' / 'qwen_kv_die'))

import contract as C          # noqa: E402
import kv_die as K            # noqa: E402
import fp_margin_lint as FPL  # noqa: E402


def test_kv_die_legal_strict_and_reach():
    m = K.build()
    chk = K.check(m)
    assert chk['overlaps'] == 0 and chk['outside'] == 0
    assert K.strict_ports(K.masters(m))['ok']
    lint = FPL.die_margin(m['insts'], [b for b in m['buses'] if b[1] not in ('clock_trunk', 'reset')], {'relay'},
                          reach_um=504.0)
    assert lint['verdict'] == 'PASS'


def test_contract_flit_matches_phy_abstract():
    phy = json.loads((ROOT / 'physical/qwen_kv_die_phy/ot_qkvd_ucie_x64_phy/ot_qkvd_ucie_x64_phy.json').read_text())
    assert phy['fdi']['flit_bits'] == C.FLIT_BITS == 548
    assert phy['fdi']['latency_fdi_cycles_one_way'] == C.PHY_LAT
    c = C.contract()
    assert {x['name'] for x in c['classes']} == {'CTL', 'Q', 'KVN', 'EMBQ', 'RES', 'EMBD', 'HCTL'}
    for x in c['classes']:       # every class's link buffer covers the worst credit round trip, or is a control class
        assert x['link_buffer'] >= C.LINK_RTT['worst'] or x['name'] in ('CTL', 'KVN', 'HCTL')
