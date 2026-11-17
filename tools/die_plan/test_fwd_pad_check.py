import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fwd_pad_check as F  # noqa: E402
import signoff_profile as SP  # noqa: E402


def _netlist(pads, port="fclk_out_u1_o"):
    lines = ["module t (clk_t9, d, " + port + ", q);", "input clk_t9;", "input d;", "output " + port + ";",
             "output q;", "wire n0;"]
    prev = "clk_t9"
    lines.append(" BUFx4_ASAP7_75t_R clk_t9_tb0_d0 (.A(" + prev + "), .Y(n0));")
    prev = "n0"
    for k in range(pads):
        lines.append(f" BUFx4_ASAP7_75t_R delaybuf_otstb_{k} (.A({prev}), .Y(otstb_net_{k}));")
        prev = f"otstb_net_{k}"
    lines.append(f" BUFx4_ASAP7_75t_R cland_fwd_{port} (.A({prev}), .Y(fwd));")
    lines.append(" assign " + port + " = fwd;")
    lines.append(" DFFHQNx1_ASAP7_75t_R f0 (.CLK(n0), .D(d), .QN(q));")
    lines.append("endmodule")
    return "\n".join(lines) + "\n"


def test_96_pads_fail_and_count_root():
    r = F.check(_netlist(96))
    assert r["verdict"] == "FAIL" and r["failing"] == ["fclk_out_u1_o"]
    p = r["ports"]["fclk_out_u1_o"]
    assert p["pads"] == 96 and p["root"] == "clk_t9" and p["depth"] == 98


def test_limit_inclusive_and_env(monkeypatch):
    assert F.check(_netlist(10))["verdict"] == "PASS"
    assert F.check(_netlist(11))["verdict"] == "FAIL"
    monkeypatch.setenv("OT_FWD_PAD_MAX", "20")
    assert F.check(_netlist(11))["verdict"] == "PASS"


def test_flop_is_root_and_no_port_passes():
    text = _netlist(0).replace("(.A(clk_t9), .Y(n0))", "(.A(qq), .Y(n0))") + \
        "module u (o); output o; DFFHQNx1_ASAP7_75t_R g (.CLK(c), .D(d), .QN(qq)); endmodule\n"
    r = F.check(text)
    assert r["verdict"] == "PASS" and r["ports"]["fclk_out_u1_o"]["root"] == "qq"
    assert F.check("module m (a, y);\ninput a;\noutput y;\nendmodule\n")["verdict"] == "PASS"


def test_cli_exit(tmp_path, capsys):
    good, bad = tmp_path / "g.v", tmp_path / "b.v"
    good.write_text(_netlist(0))
    bad.write_text(_netlist(96))
    assert F.main([str(good)]) == 0
    assert F.main([str(good), str(bad)]) == 1
    assert "failing fclk_out_u1_o=96" in capsys.readouterr().out


def _rec(fwd):
    return dict(route=dict(drc=0), checks=dict(fwd_pads=fwd),
                corners=dict(tt=dict(done=True, std_wns_max=50.0), ff=dict(done=True, std_min_start=dict(core_wns=1.0))))


def test_minimal_profile_blocks_fwd_pads():
    j = SP.judge(_rec(dict(verdict="FAIL", failing=["fclk_out_u1_o"], max_pads=96, limit=10)), die="s81_head")
    assert j["verdict"] == "NOT SIGNED" and any(r.startswith("fwd_pads: FAIL") for r in j["reasons"])
    assert j["gates"]["fwd_pads"] == "FAIL"
    j = SP.judge(_rec(dict(verdict="PASS", failing=[], max_pads=0, limit=10)), die="s81_head")
    assert j["gates"]["fwd_pads"] == "PASS"
    assert not any(r.startswith("fwd_pads") for r in j["reasons"] + j["advisories"])
