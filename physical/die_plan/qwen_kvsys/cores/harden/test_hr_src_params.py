"""QK-CORES-7 10-27: kv_core_rtl.hr_src_params must return EVERY overridable name of a comma-continued parameter
list. The old regex kept only the first name after each 'parameter' keyword, so qkd_hr_core_tx's u_ctrl
(qkd_host_ctrl_token_service_packet_collected_mu) was built with ENABLE_TOKEN/ENABLE_SERVICE/STRAPPED/MUT at
their module defaults instead of the bound values."""
import importlib.util
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('kv_core_rtl', HERE / 'kv_core_rtl.py')
K = importlib.util.module_from_spec(spec)
spec.loader.exec_module(K)
REPO = HERE.parents[4]


def _names(txt, name):
    with tempfile.NamedTemporaryFile('w', suffix='.sv', delete=False) as f:
        f.write(txt)
    J = {'T': {'attributes': {'src': f.name + ':1.1-9.9'}}}
    return K.hr_src_params(J, 'T', name)


def test_comma_continued_list():
    txt = ('module m #(parameter integer DIE=0,MUT=0,STRAPPED=0,ENABLE_SERVICE=0,ENABLE_TOKEN=0,'
           'parameter integer MU=1,parameter integer HCW=182)(input wire a);endmodule\n')
    assert _names(txt, 'm') == {'DIE', 'MUT', 'STRAPPED', 'ENABLE_SERVICE', 'ENABLE_TOKEN', 'MU', 'HCW'}


def test_ranges_comments_localparam_and_nested():
    txt = ('module m #(\n  parameter [3:0] A = 4\'d1, // c, D = 2\n  B = {1\'b0, 1\'b1}, /* E = 3, */\n'
           '  parameter integer C = f(1, 2),\n  localparam integer L = 3, L2 = 4\n) (input wire a);endmodule\n')
    assert _names(txt, 'm') == {'A', 'B', 'C'}


def test_real_ctrl_mu_header():
    src = REPO / 'rtl/qwen_sys/mu_qwen_20261018/qkd_host_ctrl_token_service_packet_collected_mu.sv'
    J = {'T': {'attributes': {'src': str(src) + ':17.1-500.9'}}}
    got = K.hr_src_params(J, 'T', 'qkd_host_ctrl_token_service_packet_collected_mu')
    assert {'ENABLE_TOKEN', 'ENABLE_SERVICE', 'STRAPPED', 'MUT'} <= got


def test_missing_source_is_none():
    J = {'T': {'attributes': {'src': '/nonexistent/x.sv:1'}}}
    assert K.hr_src_params(J, 'T', 'x') is None
