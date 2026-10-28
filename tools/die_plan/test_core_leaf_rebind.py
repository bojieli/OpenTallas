"""FLOW-GEN-2: opt-in post-placement exact-count rebind of plan-built core-tree sinks (GEOM-REVIEW-46, node a0k3)."""
import copy
import itertools
import random
import subprocess

import pytest
import core_infra as CI
import core_leaf_rebind as RB
from test_core_infra import sample


def _cost(leaves, sinks, asg):
    pos = {l[0]: l[1:] for l in leaves}
    return sum((abs(s[1] - pos[a][0]) + abs(s[2] - pos[a][1])) ** 2 for s, a in zip(sinks, asg))


def test_crossed_binding_is_untangled_with_exact_counts():
    # placement moved the flops: every sink sits next to the OTHER leaf
    leaves = [("w", 0.0, 0.0), ("e", 100.0, 0.0)]
    sinks = [(f"a{k}", 99.0, k, "w", 0) for k in range(3)] + [(f"b{k}", 1.0, k, "e", 0) for k in range(3)]
    new, st = RB.rebind(leaves, sinks)
    assert new == ["e"] * 3 + ["w"] * 3
    assert st["moved"] == 6 and st["after"]["max"] < 4 and st["before"]["max"] > 99


def test_counts_are_kept_even_when_nearest_would_overload_a_leaf():
    leaves = [("w", 0.0, 0.0), ("e", 100.0, 0.0)]
    sinks = [(f"s{k}", 1.0, k, "w" if k < 2 else "e", 0) for k in range(4)]   # all four sit next to w
    new, st = RB.rebind(leaves, sinks)
    assert sorted(new) == ["e", "e", "w", "w"]          # 2 + 2 as planned; nearest-only would put all 4 on w


def test_pinned_sinks_never_move():
    leaves = [("w", 0.0, 0.0), ("e", 100.0, 0.0)]
    sinks = [("p", 99.0, 0.0, "w", 1), ("q", 1.0, 0.0, "e", 0), ("r", 99.0, 1.0, "w", 0), ("t", 1.0, 1.0, "e", 0)]
    new, st = RB.rebind(leaves, sinks)
    assert new[0] == "w" and st["pinned"] == 1 and new == ["w", "e", "e", "w"]   # r <-> t, the cheaper swap


def test_result_is_the_exact_optimum_on_random_cases():
    rnd = random.Random(7)
    for _ in range(20):
        leaves = [(f"l{k}", rnd.uniform(0, 50), rnd.uniform(0, 50)) for k in range(3)]
        lab = [l[0] for l in leaves for _ in range(2)]
        rnd.shuffle(lab)
        sinks = [(f"s{k}", rnd.uniform(0, 50), rnd.uniform(0, 50), lab[k], 0) for k in range(6)]
        new, _ = RB.rebind(leaves, sinks)
        best = min(_cost(leaves, sinks, p) for p in set(itertools.permutations(lab)))
        assert sorted(new) == sorted(lab)
        assert _cost(leaves, sinks, new) == pytest.approx(best)


def test_cli_writes_moves_by_sink_id(tmp_path):
    (tmp_path / "in.tsv").write_text("L w 0 0\nL e 100 0\nS 0 99 0 w 0\nS 1 1 0 e 0\n")
    assert RB.main([str(tmp_path / "in.tsv"), str(tmp_path / "out.tsv")]) == 0
    out = (tmp_path / "out.tsv").read_text().splitlines()
    assert out[0].startswith("# OT_CORE_LEAF_REBIND leaves=2 sinks=2 pinned=0 moved=2")
    assert sorted(out[1:]) == ["M 0 w e", "M 1 e w"]


def _tree_slice(**opt):
    s = sample()
    s["core_tree"] = {"clock_port": "clk", "nodes": [
        dict(name="root", master="BUFx16f_ASAP7_75t_R", xy_um=[430, 430], parent="port:clk"),
        dict(name="n0", master="BUFx8_ASAP7_75t_R", xy_um=[200, 200], parent="root"),
        dict(name="n1", master="BUFx8_ASAP7_75t_R", xy_um=[600, 600], parent="root")],
        "leaves": [dict(node="n0", sinks=["u0/CLK", "u1/CLK"]), dict(node="n1", sinks=["u2/CLK", "u3/CLK"])],
        "same_leaf_pairs": [["u0/CLK", "u1/CLK"]], **opt}
    s["pg_obstructions_um"] = {}
    return s


def test_opt_in_only_and_default_hook_unchanged(tmp_path):
    legacy = CI.emit_cts_tcl(CI.compile_slice(_tree_slice()))
    assert "ot_ci_leaf_rebind_leaves" not in legacy.split("# Plan-built core clock tree")[0]
    assert CI.install(tmp_path, _tree_slice()) and not (tmp_path / CI.REBIND_PY).exists()
    hook = CI.emit_cts_tcl(CI.compile_slice(_tree_slice(post_place_rebind="exact_count")))
    assert "set ::ot_ci_leaf_rebind_leaves [list {n0} {n1}]\n" in hook
    assert "set ::ot_ci_leaf_rebind_pinned [list {u0/CLK} {u1/CLK}]\n" in hook
    assert hook.endswith(legacy.split("\n", 2)[2])
    d = tmp_path / "rb"; d.mkdir()
    assert CI.install(d, _tree_slice(post_place_rebind="exact_count")) and (d / CI.REBIND_PY).is_file()
    prog = "proc clock_tree_synthesis {args} {}\n" + hook + "\nputs $::ot_ci_leaf_rebind_leaves\nputs PARSED\n"
    r = subprocess.run(["tclsh"], input=prog, text=True, capture_output=True)
    assert r.returncode == 0 and r.stdout.split() == ["n0", "n1", "PARSED"] and not r.stderr


def test_bad_opt_in_refused():
    with pytest.raises(CI.InfraError, match="exact_count"):
        CI.compile_slice(_tree_slice(post_place_rebind="nearest"))
    s = _tree_slice(post_place_rebind="exact_count")
    s["core_tree"]["leaves"][1]["cts_open"] = True
    s["core_tree"]["leaves"][1]["domain_sinks"] = 2
    s["core_tree"]["leaves"][0]["cts_open"] = True
    s["core_tree"]["leaves"][0]["domain_sinks"] = 2
    with pytest.raises(CI.InfraError, match="two non-open register leaves"):
        CI.compile_slice(s)
