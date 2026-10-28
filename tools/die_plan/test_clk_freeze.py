"""FLOW-CLKFREEZE 2026-10-27 tests: clk_geom_diff.py verdicts + every post-route ECO chain locks the clock network
before its first incremental GRT and blocks sign-off on any clock-net geometry change."""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DP = ROOT / "tools" / "die_plan"
DIFF = DP / "clk_geom_diff.py"
sys.path.insert(0, str(DP))
import clk_geom_diff as cgd  # noqa: E402

BASE_NET = "NET\tclkA\tCLOCK\t3\t{t}\t{op}:M3 4:100 4:200 8:TV:VIA12 9:ff1/CLK"
PRE = [
    "#CLKDUMP tag pre nets 2 block top",
    BASE_NET.format(t="96", op=0),
    "PIN\tclkA\tbuf0/Y ff1/CLK ff2/CLK",
    "NET\tclkB\tCLOCK\t2\t96\t0:M2 4:5 4:6",
    "PIN\tclkB\tbuf1/Y ff3/CLK",
    "INST\tbuf0\tBUFx4_ASAP7_75t_R\t10\t20\tR0\tPLACED",
    "INST\tff1\tDFFHQNx1_ASAP7_75t_R\t30\t40\tR0\tPLACED",
]


def run(tmp, pre, post):
    a, b = tmp / "pre.tsv", tmp / "post.tsv"
    a.write_text("\n".join(pre) + "\n")
    b.write_text("\n".join(post) + "\n")
    j = tmp / "d.json"
    p = subprocess.run([sys.executable, "-I", str(DIFF), str(a), str(b), "--json", str(j)], capture_output=True, text=True)
    return p.returncode, p.stdout, (json.loads(j.read_text()) if j.exists() else None)


def test_identical_pass(tmp_path):
    rc, out, r = run(tmp_path, PRE, PRE)
    assert rc == 0 and r["verdict"] == "PASS" and "changed 0" in out


def test_freeze_type_bits_only_pass(tmp_path):
    # ROUTED (96 = 0x60) -> FIXED (64 = 0x40): the type bits are masked in the tokens; status PLACED -> LOCKED is the lock
    post = [l.replace("\t96\t", "\t64\t").replace("\tPLACED", "\tLOCKED") for l in PRE]
    rc, out, r = run(tmp_path, PRE, post)
    assert rc == 0 and r["fixed_nets_post"] == 2


def test_rerouted_wire_fails_with_net_list(tmp_path):
    post = [l.replace("4:200", "4:201") for l in PRE]
    rc, out, r = run(tmp_path, PRE, post)
    assert rc == 1 and r["wire"] == ["clkA"] and "clkA" in out
    assert r["details"]["clkA"]["op_index"] == 2


def test_destroyed_wire_fails(tmp_path):
    post = [("NET\tclkB\tCLOCK\t0\t\t" if l.startswith("NET\tclkB") else l) for l in PRE]
    rc, _, r = run(tmp_path, PRE, post)
    assert rc == 1 and r["wire"] == ["clkB"]


def test_pin_change_fails(tmp_path):
    post = [l.replace("ff2/CLK", "hb1/A ff2/CLK") if l.startswith("PIN\tclkA") else l for l in PRE]
    rc, _, r = run(tmp_path, PRE, post)
    assert rc == 1 and r["pins"] == ["clkA"]


def test_moved_or_resized_instance_fails(tmp_path):
    post = [l.replace("\t30\t40\t", "\t30\t310\t") for l in PRE]
    rc, _, r = run(tmp_path, PRE, post)
    assert rc == 1 and r["inst"] == ["ff1"]
    post = [l.replace("DFFHQNx1", "DFFHQNx2") for l in PRE]
    assert run(tmp_path, PRE, post)[0] == 1


def test_missing_and_new_clock_net_fail(tmp_path):
    post = [l for l in PRE if "clkB" not in l]
    rc, _, r = run(tmp_path, PRE, post)
    assert rc == 1 and r["missing"] == ["clkB"]
    post = PRE + ["NET\tclkA_split\tCLOCK\t2\t96\t0:M2 4:1 4:2", "PIN\tclkA_split\thb/Y ff2/CLK"]
    rc, _, r = run(tmp_path, PRE, post)
    assert rc == 1 and r["new"] == ["clkA_split"]


def test_bad_input_is_exit_2(tmp_path):
    (tmp_path / "e.tsv").write_text("")
    p = subprocess.run([sys.executable, "-I", str(DIFF), str(tmp_path / "e.tsv"), str(tmp_path / "e.tsv")],
                       capture_output=True, text=True)
    assert p.returncode == 2


ECO_HOOKS = [
    ROOT / "physical/die_plan/qwen_kvsys/cores/harden/eco/eco_route.tcl",       # KV ECO + HEAD post-route ECO
    ROOT / "physical/die_plan/qwen_compute/cores/legacy/hold_route.tcl",        # QC warm hold ECO
]


def test_every_eco_hook_locks_before_first_incremental_grt_and_asserts_after_each():
    for p in ECO_HOOKS:
        lines = [l.strip() for l in p.read_text().splitlines() if l.strip() and not l.strip().startswith("#")]
        i_freeze = lines.index("ot_clk_freeze")
        i_start = next(i for i, l in enumerate(lines) if l.startswith("global_route -start_incremental"))
        i_spef = next(i for i, l in enumerate(lines) if l.startswith("read_spef"))
        assert i_spef < i_freeze < i_start, p
        for i, l in enumerate(lines):
            if l.startswith("global_route -end_incremental"):
                assert lines[i + 1] == "ot_clk_freeze_assert post_grt", (p, i)
        # no repair command before the lock
        assert not any(re.match(r"(repair_|detailed_placement)", l) for l in lines[:i_freeze]), p


CHAINS = {
    ROOT / "tools/s81_head/head_post_route_eco.sh": ("$HERE/../die_plan/$f", "clk_freeze_check.sh\" \"$OUT\""),
    ROOT / "physical/die_plan/qwen_kvsys/cores/harden/eco/mk_eco.sh": ("$ROOT/tools/die_plan/$f", None),
    ROOT / "physical/die_plan/qwen_compute/cores/legacy/mk_hold_qc.sh": ("$ROOT/tools/die_plan/$f", None),
}


def test_chains_stage_the_lock_and_the_check():
    for p, (src, _) in CHAINS.items():
        t = p.read_text()
        assert "for f in clk_freeze.tcl clk_dump_db.tcl clk_geom_diff.py clk_freeze_check.sh" in t, p
        assert src in t, p


def test_signoff_is_gated_on_the_check():
    t = (ROOT / "tools/s81_head/head_post_route_eco.sh").read_text()
    i_ck = t.index('clk_freeze_check.sh" "$OUT"')
    i_so = t.index('python3 -I "$OUT/signoff.py" run')
    assert i_ck < i_so and 'if [ "$rrc" = 0 ] && [ "$ckf" = 0 ]; then' in t[i_ck:i_so]
    assert "exit 4" in t.split("HEAD_ECO_CHAIN done")[-1]
    for p in (ROOT / "physical/die_plan/qwen_kvsys/cores/harden/eco/run_eco.sh",
              ROOT / "physical/die_plan/qwen_compute/cores/legacy/run_hold.sh"):
        t = p.read_text()
        i_ck = t.index("clk_freeze_check.sh $D $IMAGE")
        i_so = t.index("run_kit_kv.sh $D post") if "run_kit_kv" in t else t.index("signoff.py run")
        assert i_ck < i_so and "[ $ck = 0 ] || rc=5" in t[i_ck:i_so], p


def test_check_script_fails_closed_without_pre_dump(tmp_path):
    d = tmp_path / "eco"
    (d / "run/results/asap7/x/base").mkdir(parents=True)
    for f in ("clk_freeze.tcl", "clk_dump_db.tcl", "clk_geom_diff.py"):
        (d / f).write_text("")
    p = subprocess.run(["bash", str(DP / "clk_freeze_check.sh"), str(d)], capture_output=True, text=True)
    assert p.returncode == 2 and "clk_freeze_pre.tsv missing" in p.stdout


def test_lock_uses_fixed_wire_and_locked_placement():
    t = (DP / "clk_freeze.tcl").read_text()
    assert "newPath [$dec getLayer] FIXED" in t and "$enc {*}$a" in t
    assert "ot_clk_encode_wire $n $::ot_clk_ops($nm) $::ot_clk_tok($nm)" in t  # post-GRT restore
    assert "setPlacementStatus LOCKED" in t and "setDoNotTouch 1" in t
    # fail closed: a re-encode that is not byte-identical errors out
    assert "is not byte-identical" in t


def test_qc_hold_chain_runs_its_hook_on_routed_kits():
    # QC kits 'override export' both GRT hooks; the warm ECO must override them too (else neither ECO nor lock runs) and
    # survive ORFS's pre-POST 'estimate_parasitics -global_routing' on a fully routed DB (EST-0005 canary 10-27 11:53)
    lg = ROOT / "physical/die_plan/qwen_compute/cores/legacy"
    t = (lg / "mk_hold_qc.sh").read_text()
    assert "override export POST_GLOBAL_ROUTE_TCL = /work/hold_route.tcl" in t
    assert "override export PRE_GLOBAL_ROUTE_TCL = /work/eco_pre_grt.tcl" in t and "OT_KIT_PRE_GRT = $KPRE" in t
    assert "override export PRE_DETAIL_ROUTE_TCL =\n" in t and "override export POST_DETAIL_ROUTE_TCL =\n" in t
    p = (lg / "eco_pre_grt.tcl").read_text()
    assert "![grt::have_routes]" in p and "read_spef $s" in p and "source $::env(OT_KIT_PRE_GRT)" in p


# FLOW-SHARED-10: pre-DRT hold ECO (5_1_grt start, one detailed route) -> --pre-unrouted
PRE_UNROUTED = [
    "#CLKDUMP tag pre nets 2 block top",
    "NET\tclkA\tCLOCK\t0\t\t",
    "PIN\tclkA\tbuf0/Y ff1/CLK ff2/CLK",
    "NET\tclkB\tCLOCK\t0\t\t",
    "PIN\tclkB\tbuf1/Y ff3/CLK",
    "INST\tbuf0\tBUFx4_ASAP7_75t_R\t10\t20\tR0\tLOCKED",
    "INST\tff1\tDFFHQNx1_ASAP7_75t_R\t30\t40\tR0\tLOCKED",
]


def run_pu(tmp, pre, post):
    a, b, j = tmp / "pre.tsv", tmp / "post.tsv", tmp / "d.json"
    a.write_text("\n".join(pre) + "\n")
    b.write_text("\n".join(post) + "\n")
    p = subprocess.run([sys.executable, "-I", str(DIFF), str(a), str(b), "--json", str(j), "--pre-unrouted"],
                       capture_output=True, text=True)
    return p.returncode, p.stdout, (json.loads(j.read_text()) if j.exists() else None)


def test_pre_unrouted_first_route_passes_but_pins_and_insts_stay_blocking(tmp_path):
    rc, out, r = run_pu(tmp_path, PRE_UNROUTED, PRE)          # the single DRT routed both clock nets
    assert rc == 0 and r["verdict"] == "PASS" and r["mode"] == "pre_unrouted" and "not compared" in out
    rc, _, r = run_pu(tmp_path, PRE_UNROUTED, [l.replace("ff2/CLK", "ff2/CLK hb1/A") for l in PRE])
    assert rc == 1 and r["pins"] == ["clkA"]
    rc, _, r = run_pu(tmp_path, PRE_UNROUTED, [l.replace("\t30\t40\t", "\t31\t40\t") for l in PRE])
    assert rc == 1 and r["inst"] == ["ff1"]
    # without the flag the same first route is a wire change (the post-route ECO contract is unchanged)
    rc, _, r = run(tmp_path, PRE_UNROUTED, PRE)
    assert rc == 1 and set(r["wire"]) == {"clkA", "clkB"}


def test_pre_unrouted_refuses_a_wired_start(tmp_path):
    rc, out, r = run_pu(tmp_path, PRE, PRE)                   # a routed DB is not a pre-DRT start
    assert rc == 1 and r["pre_wired"] == ["clkA", "clkB"] and "pre_wired" in out


def test_check_script_selects_pre_unrouted_only_for_grt_eco():
    t = (DP / "clk_freeze_check.sh").read_text()
    assert "grep -qs '^OT_ECO_FROM=grt$' \"$D/variant.env\" && PU=--pre-unrouted" in t
    assert '--json "$D/clk_geom_diff.json" $PU' in t
