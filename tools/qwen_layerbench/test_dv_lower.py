#!/usr/bin/env python3
"""QLB-C4 10-18 unit tests of the DV slice lowering (tools/qwen_layerbench/dv_lower.py).

  python3 -m pytest -q tools/qwen_layerbench/test_dv_lower.py      (repository root)

The encoders are checked bit for bit against the slice2 bench encoders (rtl/test/qwen_dv/dv_bench.py / dv_bench2.py,
whose words the RTL benches a..j drive) and against the qfd_dv_slice2 decode field map.
"""
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / 'rtl/test/qwen_dv'))
import dv_lower as D  # noqa: E402

np = pytest.importorskip('numpy')
import dv_bench as B   # noqa: E402
import dv_bench2 as B2  # noqa: E402

AGES = ROOT / D.AGES


def test_slice_map_is_the_die_chain():
    m = D.slice_map()
    assert m['names'] == [f'dvs_W{k}' for k in range(5, -1, -1)] + [f'dvs_E{k}' for k in range(6)]
    assert m['cmd_arrival'] == [2 * k for k in range(12)]           # dv2f14bq: no relay on any cmd hop
    assert all(h['sc_extra'] == 0 for h in m['hops'])
    assert D.sc_down_edges(m, 11, 0) == 22


def test_ownership():
    o = D.ownership()
    res = o['residual']['blocks_per_slice']
    assert res[0] == [0, 12, 24] and res[7] == [7, 19, 31] and res[8] == [8, 20] and res[11] == [11, 23]
    assert sorted(b for s in res for b in s) == list(range(32))
    assert {b['slice'] for b in o['qkv']['blocks']} == {0, 2, 4, 6, 8, 10}
    gu = o['gu']['blocks']
    assert all(b['slice'] == b['block'] // 2 and b['pair'] == b['block'] % 2 for b in gu) and len(gu) == 24
    assert len(o['lm_head']['blocks']) == 149 and {b['slice'] for b in o['lm_head']['blocks']} == {0, 2, 4, 6, 8, 10}


def test_su_word_equals_bench_encoder():
    w = D.su_word(nout=3, nin=128, a=0, aso=128, asi=1, red=1, redsq=1, rb=D.W_SC | 5, rso=12)
    assert w == B.su(nout=3, nin=128, a=0, aso=128, asi=1, red=1, redsq=1, rb=B.W_SC | 5, rso=12)
    f = D.su_unpack(w)
    assert (f['nout'], f['nin'], f['red'], f['redsq'], f['rb'], f['rso'], f['go']) == (3, 128, 1, 1, (3 << 22) | 5, 12, 0)
    with pytest.raises(D.LowerError):
        D.su_word(nin=1 << 18)
    with pytest.raises(D.LowerError):
        D.su_word(nin=0)


def test_commands_equal_bench_encoders_and_decode():
    assert D.cmd_setid(0) == B2.setid(0)
    assert D.cmd_su(7, 3) == B.cmd_su(7) | (3 << 112)
    eps = 0x358637BD
    r = D.cmd_root(0, 1, 32, 384, fuse=1, rx=400, eps=eps, k=12)
    assert r == B.cmd_root(1, 32, 384, fuse=1, rx=400, eps=float(np.array([eps], dtype=np.uint32).view(np.float32)[0]), k=12)
    d = D.decode_cmd(r)
    assert (d['kind'], d['root'], d['nb'], d['ss'], d['fuse'], d['rx'], d['eps'], d['k'], d['dst']) == (3, 1, 32, 384, 1, 400, eps, 12, 0)
    assert D.cmd_ports(4, ar_base=16, ar_en=1) == B2.cmd_ports2(16, 0, ar_en=1) | (4 << 112)
    assert D.cmd_xc(0, 1, 256, 9) == B2.cmd_xc_coll(1, 256, 9)
    assert D.cmd_amax(15, emit=1, gather=1) == B2.cmd_amax2(emit=1, gather=1) | (15 << 112)
    with pytest.raises(D.LowerError):
        D.cmd_root(0, 1, 33, 0)
    with pytest.raises(D.LowerError):
        D.cmd_su(512, 0)
    with pytest.raises(D.LowerError):
        D.cmd_su(0, 12)


def test_prog_stream_words():
    ws = [D.su_word(nin=1), D.su_word(nin=2), D.su_word(nin=3)]
    pw = D.prog_words(ws)
    assert [a for a, _ in pw] == [0, 1] and pw[0][1] == ws[0] | (ws[1] << 512) and pw[1][1] == ws[2]
    t = D.stream_table_word(3, 5, 1, pw[1][1])
    assert t == B.stream_word(3, 5, 1, pw[1][1])
    with pytest.raises(D.LowerError):
        D.prog_words([0] * 513)


@pytest.mark.skipif(not AGES.exists(), reason='slice_ages.json not measured yet')
def test_lowering_schedule():
    lw = D.lower()
    assert lw['expected']['collisions'] == []
    res = lw['ownership']['residual']['blocks_per_slice']
    assert all(lw['ssq'][s]['tags'] == res[s] for s in range(12))
    assert lw['root'] == dict(slice=0, nb=32, k=12, eps=0x358637BD, rx=lw['vm']['RX']['base'], ss=lw['vm']['SSX']['base'])
    assert len({c['edge'] for c in lw['commands']}) == len(lw['commands'])
    assert D.lower('broadcast')['expected']['collisions']            # one dst-15 SU command collides on the chain
    assert D.lower('rso1')['ssq'][0]['tags'] == [0, 1, 2]


def test_isa_refusals(tmp_path):
    sys.path.insert(0, str(ROOT / 'tools'))
    import hdc_qwen_fullshape_isa_w12 as ISA
    src = ROOT / 'results/arch/qwen_tp8_native_dispatch_1014/actual_fused_layer0/die0/program.hex'
    words = [int(w, 16) for w in src.read_text().split()]
    f = ISA.decode_instruction(words[2])
    f['imm1'] = 0x3A000001                                             # not 2^-k
    words[2] = ISA.encode_instruction(f)
    p = tmp_path / 'prog.hex'
    p.write_text(''.join(f'{w:0256x}\n' for w in words))
    with pytest.raises(D.LowerError):
        D.isa_rmsnorm(p)
