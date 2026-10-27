"""KV-CORES-PV3 10-27: the hr cut keeps every overridable parameter of a member (comma-continued lists included)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from kv_core_rtl import hr_header_params, hr_src_params  # noqa: E402


def test_comma_continued_list():
    hdr = ("parameter integer DIE=0,MUT=0,STRAPPED=0,ENABLE_SERVICE=0,ENABLE_TOKEN=0,"
           "parameter integer MU=1,parameter integer HCW=182")
    assert hr_header_params(hdr) == {"DIE", "MUT", "STRAPPED", "ENABLE_SERVICE", "ENABLE_TOKEN", "MU", "HCW"}


def test_types_ranges_localparam_and_nested_commas():
    hdr = ("parameter int W = 8, parameter logic [7:0] K = {4'd1, 4'd2}, signed_p = -1, "
           "parameter [W-1:0] M = '0, localparam int L = W*2, L2 = 3, parameter N = f(1, 2)")
    assert hr_header_params(hdr) == {"W", "K", "signed_p", "M", "N"}


def test_real_source_ctrl_mu():
    src = (Path(__file__).resolve().parents[5]
           / "rtl/qwen_sys/mu_qwen_20261018/qkd_host_ctrl_token_service_packet_collected_mu.sv")
    J = {"t": {"attributes": {"src": f"{src}:17.1-300.10"}}}
    got = hr_src_params(J, "t", "qkd_host_ctrl_token_service_packet_collected_mu")
    assert {"STRAPPED", "ENABLE_SERVICE", "ENABLE_TOKEN", "MUT", "DIE", "MU", "HCW"} <= got
