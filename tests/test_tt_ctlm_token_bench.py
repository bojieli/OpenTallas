"""tools/qwen_tokfunc/tt_ctlm_token_bench.py: generator / program checks only (no simulator)."""
import importlib.util
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('ttb', ROOT / 'tools/qwen_tokfunc/tt_ctlm_token_bench.py')
B = importlib.util.module_from_spec(spec); spec.loader.exec_module(B)

PORTS = '''module m(rst_n,pw,dh,init_u0,dh_user,f16_auth,control_stores_ready,cf,cmd,native_cmd,table_req,emb_start,f16_st,dc,cal_image_ready,ck_core);
input wire [0:0] rst_n;
input wire [74:0] pw;
input wire [186:0] dh;
input wire [0:0] init_u0;
input wire [1:0] dh_user;
input wire [82:0] f16_auth;
output wire [0:0] control_stores_ready;
output wire [0:0] cf;
output wire [115:0] cmd;
output wire [379:0] native_cmd;
output wire [8:0] table_req;
output wire [0:0] emb_start;
output wire [16:0] f16_st;
output wire [55:0] dc;
output wire [0:0] cal_image_ready;
input wire [0:0] ck_core;
'''


def test_ports_and_tb_modes():
    ports = B.parse_ports(PORTS)
    assert ('input', 75, 'pw') in ports and ('output', 380, 'native_cmd') in ports
    tb = B.make_tb(ports, 'm', '', 0xbe4977f1d99c58a1, 8, 2, 10)
    assert 'm  dut(' in tb and '.ck_core(ck)' in tb and "64'hbe4977f1d99c58a1 ^ 64'(mode == 4)" in tb
    for m in (1, 2, 3):
        assert f'mode == {m}' in tb
    assert 'mode != 5' in tb
    assert 'TT_TOKBENCH_PASS' in tb and 'ready_cyc < start_cyc' in tb


def test_missing_port_refused():
    try:
        B.make_tb(B.parse_ports(PORTS.replace('input wire [82:0] f16_auth;\n', '')), 'm', '', 1, 8, 1, 1)
    except SystemExit as e:
        assert 'f16_auth' in str(e)
    else:
        raise AssertionError('missing f16_auth accepted')


def test_xpf_reprice_and_digest():
    p = [0] * 1032
    arm, fw = 5849, 5872
    rec = 1 | (2 << 84) | (1 << 86) | (arm << 92) | (5844 << 124) | (fw << 156)
    p[1004], p[1005], p[1006] = rec & (2**64 - 1), (rec >> 64) & (2**64 - 1), rec >> 128
    assert B.xpf_records(p) == [(arm, fw)]
    q = B.reprice_xpf(p, 1)
    assert B.xpf_records(q) == [(arm, fw + 1)]
    assert B.image_digest(p) != B.image_digest(q)
    assert B.image_digest([0] * 1032) == B.image_digest([0] * 1032)
