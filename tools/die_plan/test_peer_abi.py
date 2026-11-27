"""P-PEER-ABI: cross-die pair guard (tools/die_plan/peer_abi.py).  Fixture: the live KV/QC STATUS-v1 mismatch."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import peer_abi as PA  # noqa: E402

KV_SRC = "module kv3_sys_c_part; \n    qkd_d2d_static_sfm #(.FEG(1), .NL(2), .NTX(3), .SAFE_RC(1), .SRAMV(2), .TXDP(32'h039ba2ae)%s) u_d2d_kv (\n .x(w));\nendmodule\n"
QC_SRC = "module qfd_qc_glue_part;\n    %s #(.HEAD_CONTEXT(1), .TXDP(32'h15011213)) u_d2d_rom (\n .x(w));\nendmodule\n"


def mk_bind(root, name, fname, text):
    d = Path(root) / name / "rtl"
    d.mkdir(parents=True)
    (d / fname).write_text(text)
    return str(d.parent)


def kv(tmp, compat=None, name="kv"):
    extra = "" if compat is None else f", .OBS1_COMPAT({compat})"
    return mk_bind(tmp, name, "kv3_sys_c_part.sv", KV_SRC % extra)


def qc(tmp, module="qfd_d2d_static_ovl_sf7_obs1", name="qc"):
    return mk_bind(tmp, name, "qfd_qc_glue_part.sv", QC_SRC % module)


def test_live_pair_kv_default_vs_qc_status_v1_is_a_mismatch(tmp_path):
    rec = PA.gate("qwen_kvsys", "/none", kv(tmp_path), {"qwen_compute": ("/none", qc(tmp_path))})
    assert rec["verdict"] == "FAIL"
    (row,) = rec["pairs"]
    assert row["pair"] == "QC-KV:status" and row["state"] == "MISMATCH"
    assert "OBS1_COMPAT=0" in row["detail"] and row["fix_side"].startswith("KV")


def test_same_pair_seen_from_the_qc_cut_also_fails(tmp_path):
    rec = PA.gate("qwen_compute", "/none", qc(tmp_path), {"qwen_kvsys": ("/none", kv(tmp_path))})
    assert rec["verdict"] == "FAIL" and rec["pairs"][0]["state"] == "MISMATCH"


def test_kv_obs1_compat_1_matches(tmp_path):
    rec = PA.gate("qwen_kvsys", "/none", kv(tmp_path, 1), {"qwen_compute": ("/none", qc(tmp_path))})
    assert rec["verdict"] == "PASS" and rec["pairs"][0]["state"] == "MATCH"


def test_legacy_qc_master_is_accepted_by_default_kv(tmp_path):
    rec = PA.gate("qwen_kvsys", "/none", kv(tmp_path), {"qwen_compute": ("/none", qc(tmp_path, "qfd_d2d_static_ovl_sf7"))})
    assert rec["verdict"] == "PASS"


def test_unreadable_peer_is_unknown_and_does_not_block(tmp_path):
    rec = PA.gate("qwen_kvsys", "/none", kv(tmp_path), {"qwen_compute": ("/nonexistent", None)})
    assert rec["verdict"] == "PASS" and rec["pairs"][0]["state"] == "UNKNOWN"


def test_die_without_a_pair_passes():
    assert PA.gate("hbm", "/none", None, {})["verdict"] == "PASS"


def test_param_parser_handles_nested_parens_and_defaults():
    t = "foo_x #(.A(f(1,2)), .B(3)) u_i (.p(q));"
    (i,) = PA.find_instances(t, "foo_x", "u_i")
    assert i["params"] == {"A": "f(1,2)", "B": "3"}


def link_tree(tmp, name, serdes_extra="", common="K"):
    d = Path(tmp) / name / PA.LINK_DIR
    d.mkdir(parents=True)
    (d / "ot_pdie_serdes.sv").write_text("module ot_pdie_serdes #(parameter integer PMA_LAT = 4%s) (input wire clk, output wire [543:0] pma_tx);\n" % serdes_extra)
    (d / "ot_s81_kp4_enc.sv").write_text("module ot_s81_kp4_enc #(parameter integer N=1) (input wire ck);\n")
    (d / "ot_s81_kp4_dec.sv").write_text("module ot_s81_kp4_dec #(parameter integer N=1) (input wire ck);\n")
    (d / "ot_s81_kp4_common.sv").write_text(common)
    return str(Path(tmp) / name)


def test_s81_head_link_match_and_mismatch(tmp_path):
    a, b = link_tree(tmp_path, "s81"), link_tree(tmp_path, "head")
    assert PA.gate("s81", a, None, {"s81_head": (b, None)})["pairs"][0]["state"] == "MATCH"
    c = link_tree(tmp_path, "head2", common="K2")
    r = PA.gate("s81", a, None, {"s81_head": (c, None)})
    assert r["verdict"] == "FAIL" and "kp4_common" in r["pairs"][0]["detail"]
    e = link_tree(tmp_path, "head3", serdes_extra=", parameter integer NEW = 0")
    assert PA.gate("s81_head", e, None, {"s81": (a, None)})["verdict"] == "FAIL"


def test_cli_census_exit_code(tmp_path, capsys):
    rc = PA.main(["census", "--kv", "/none:" + kv(tmp_path), "--qc", "/none:" + qc(tmp_path)])
    assert rc == 1 and "MISMATCH" in capsys.readouterr().out
    assert PA.main(["census", "--kv", "/none:" + kv(tmp_path, 1, "kv1"), "--qc", "/none:" + qc(tmp_path, name="qc1")]) == 0
