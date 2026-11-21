"""LATCH-SWAP-0045: resizer latch -> flop swaps are restored after every repair pass and fail sign-off if left in 6_final.v."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_phys  # noqa: E402
import signoff  # noqa: E402

HERE = Path(__file__).resolve().parent


def _net(p, cells):
    p.write_text("module top (a);\n" + "".join(f"  {c} u{i} (.CLK(ck), .D(d), .Q(q{i}));\n" for i, c in enumerate(cells))
                 + "endmodule\n")
    return str(p)


def test_counts_and_fail_on_swap(tmp_path):
    syn = _net(tmp_path / "1_synth.v", ["DLLx2_ASAP7_75t_R"] * 3 + ["DFFLQNx1_ASAP7_75t_R", "DHLx1_ASAP7_75t_L"])
    fin = _net(tmp_path / "6_final.v", ["DLLx2_ASAP7_75t_R", "DFFLQx4_ASAP7_75t_R", "DFFHQx4_ASAP7_75t_L",
                                         "DFFLQNx1_ASAP7_75t_R", "DLLx3_ASAP7_75t_R"])
    assert signoff.latch_cell_counts(syn) == dict(latch=4, swap_flop=0)
    r = signoff.latch_swap_check(dict(synth=syn, final_v=fin))
    assert r["verdict"] == "FAIL" and r["final"]["swap_flop"] == 2


def test_pass_and_not_run(tmp_path):
    syn = _net(tmp_path / "1_synth.v", ["DLLx2_ASAP7_75t_R"] * 2)
    fin = _net(tmp_path / "6_final.v", ["DLLx3_ASAP7_75t_R", "DLLx2_ASAP7_75t_R"])
    assert signoff.latch_swap_check(dict(synth=syn, final_v=fin))["verdict"] == "PASS"
    assert signoff.latch_swap_check(dict(synth=syn, final_v=None))["verdict"] == "NOT RUN"


def test_evaluate_blocks_fail_only():
    def rec(v):
        r = dict(corners={}, latch_swap=dict(verdict=v))
        signoff.evaluate(r)
        return r
    assert any(x.startswith("latch_swap: FAIL") for x in rec("FAIL")["reasons"])
    assert not any(x.startswith("latch_swap") for x in rec("NOT RUN")["reasons"])
    assert not any(x.startswith("latch_swap") for x in rec("PASS")["reasons"])


def test_hook_chains_floorplan_and_resize(tmp_path):
    cfg = ["export DESIGN_NAME = t", "export POST_CTS_TCL = /work/cts_post.tcl",
           "export POST_RESIZE_TCL = /work/a.tcl", "override export POST_RESIZE_TCL = /work/b.tcl"]
    out = gen_phys.latch_restore_hook_lines(cfg, tmp_path)
    assert cfg == ["export DESIGN_NAME = t", "export POST_CTS_TCL = /work/cts_post.tcl"]   # CTS hook line untouched
    assert (tmp_path / "latch_restore.tcl").is_file()
    for var, tag in gen_phys.LATCH_RESTORE_STAGES:
        assert f"export {var} = /work/latch_restore_{tag}.tcl" in out
        body = (tmp_path / f"latch_restore_{tag}.tcl").read_text()
        assert f"set ::ot_lr_tag {tag}; uplevel #0 {{source /work/latch_restore.tcl}}" in body
    rs = (tmp_path / "latch_restore_post_resize.tcl").read_text()
    assert "source /work/b.tcl\n" in rs and "a.tcl" not in rs                 # make reads the last definition
    assert "source /work/" not in (tmp_path / "latch_restore_post_floorplan.tcl").read_text().split("if {")[0]


def test_cts_and_grt_hooks_restore_before_pg_connect():
    for f, tag, var in (("cts_post.tcl", "post_cts", "cp_dir"), ("grt_post.tcl", "post_grt", "gq_dir")):
        s = (HERE / f).read_text()
        h = f"set ::ot_lr_tag {tag}; uplevel #0 [list source [file join ${var} latch_restore.tcl]]"
        assert s.count(h) == 1 and s.index(h) < s.index(f"source [file join ${var} pg_connect.tcl]")


def test_restore_tcl_targets():
    t = (HERE / "latch_restore.tcl").read_text()
    assert "setDoNotTouch" not in t                                  # ODB-0369: dont_touch breaks synth / CTS edits
    assert re.search(r"DFF\(\[HL\]\)Qx4", t) and "DLLx3" in t and "DHLx3" in t
    assert "global_route -start_incremental" in t and "FAIL_LATCH_SWAP" in t


def test_genphys_writes_hook_before_config():
    src = (HERE / "gen_phys.py").read_text()
    i = src.index("    cfg += latch_restore_hook_lines(cfg, kd)\n")
    assert src.index('(kd / "config.mk").write_text("\\n".join(cfg) + "\\n")', i) - i < 80
