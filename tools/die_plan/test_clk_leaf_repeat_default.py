"""KW-FIX-24/LEAFREP 11-06 (COORD 20:0x (5) / 20:2x (6)): clk_leaf_repeat is default-on for every kit.

Local, no Docker/OpenROAD: core_flow.stage_grt183 stages physical/common_flow/clk_leaf_repeat.tcl as
clk_leaf_repeat_default.tcl, grt183_make.sh (the make wrapper of every kit runner) hooks it into the container's
cts.tcl (before POST CTS) and global_route.tcl (after the first GRT parasitics estimate), and the Tcl itself runs once,
skips a kit that hooks it explicitly, honours the opt-outs, and repeats a long / over-macro clock branch on GRT data.
The Tcl is exercised under tclsh with mocked odb / sta / grt commands."""
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "autopilot"))
import core_flow  # noqa: E402
import kit_resume as KR  # noqa: E402

CLR = ROOT / "physical/common_flow/clk_leaf_repeat.tcl"
WRAP = ROOT / "physical/common_flow/grt183_make.sh"
CTS = "a\nsource_step_tcl POST CTS\norfs_write_db x\n"
GRT = ("  source_step_tcl PRE GLOBAL_ROUTE\n  set_propagated_clock [all_clocks]\n  log_cmd estimate_parasitics -global_routing\n"
       "  repair_design_helper\n  log_cmd estimate_parasitics -global_routing\n")


# ------------------------------------------------------------------------------------------------ staging / wrapper
def test_stage_grt183_stages_default_copy(tmp_path):
    core_flow.stage_grt183(tmp_path)
    assert (tmp_path / "clk_leaf_repeat_default.tcl").read_bytes() == CLR.read_bytes()
    assert (tmp_path / "grt183_make.sh").is_file()


def test_kit_resume_reads_default_copy_at_cts():
    st = KR.classify({"grt183_make.sh": WRAP.read_text()}, ["grt183_make.sh", "clk_leaf_repeat_default.tcl"], {})
    assert st["clk_leaf_repeat_default.tcl"] == "cts" and st["grt183_make.sh"] == KR.GATE


def wrap_kit(tmp_path, cfg="", stage=True):
    w, s = tmp_path / "work", tmp_path / "scripts"
    w.mkdir(); s.mkdir()
    (s / "cts.tcl").write_text(CTS); (s / "global_route.tcl").write_text(GRT)
    (w / "config.mk").write_text(cfg)
    if stage:
        shutil.copyfile(CLR, w / "clk_leaf_repeat_default.tcl")
    return w, s


def run_wrap(w, s, env=None):
    e = dict(os.environ, OT_GRT183_WORK=str(w), OT_GRT183_SCRIPTS=str(s), **(env or {}))
    return subprocess.run(["bash", str(WRAP), "true"], env=e, capture_output=True, text=True)


@pytest.mark.parametrize("cfg", ["", "export OT_GRT183_RESUME = 0\n"])
def test_wrapper_hooks_cts_and_grt_once(tmp_path, cfg):
    w, s = wrap_kit(tmp_path, cfg)
    for _ in range(2):                                           # idempotent per container
        p = run_wrap(w, s)
        assert p.returncode == 0, p.stdout + p.stderr
    c = (s / "cts.tcl").read_text().splitlines()
    i = c.index("source_step_tcl POST CTS")
    assert c[i - 1].startswith("set ::ot_clr_default 1; source /work/clk_leaf_repeat_default.tcl; unset -nocomplain ::ot_clr_default")
    assert sum("clk_leaf_repeat_default" in x for x in c) == 1
    g = (s / "global_route.tcl").read_text().splitlines()
    j = g.index("  log_cmd estimate_parasitics -global_routing")
    assert g[j + 1] == ("  set ::ot_clr_stage grt; source /work/clk_leaf_repeat_default.tcl; unset -nocomplain ::ot_clr_stage "
                        ";# OT_CLK_LEAF_REPEAT grt")
    assert sum("clk_leaf_repeat_default" in x for x in g) == 1   # only after the FIRST estimate (before repair_design)
    assert g.index("  repair_design_helper") == j + 2


def test_wrapper_without_kit_file_patches_nothing(tmp_path):
    w, s = wrap_kit(tmp_path, stage=False)
    assert run_wrap(w, s).returncode == 0
    assert (s / "cts.tcl").read_text() == CTS
    assert "clk_leaf_repeat" not in (s / "global_route.tcl").read_text()


# ------------------------------------------------------------------------------------------------ Tcl behaviour
MOCK = r"""
set ::log {}
proc L {args} { lappend ::log [join $args " "] }
# objects: dict name -> {method value}
proc mkobj {name methods} { set ::obj($name) $methods; proc $name {m args} "return \[dict get \$::obj($name) \$m\]" }
proc box {name x0 y0 x1 y1} { mkobj $name [list xMin $x0 yMin $y0 xMax $x1 yMax $y1] }
set ::nid 0
proc master {name {blk 0}} { mkobj m_$name [list getName $name isBlock $blk] }
proc inst {name m x y {w 1000} {h 1000}} {
  box b_$name $x $y [expr {$x + $w}] [expr {$y + $h}]
  mkobj $name [list getName $name getMaster m_$m getBBox b_$name getId [incr ::nid]]
}
proc iterm {name inst pin out} { mkobj $name [list getInst $inst getMTerm mt_$pin isOutputSignal $out isInputSignal [expr {!$out}] getNet nn_$name]
  mkobj mt_$pin [list getName $pin]; proc nn_$name {m args} "L \$m $name {*}\$args" }
proc net {name type its {guides {}}} { mkobj $name [list getName $name getSigType $type getBTerms {} getITerms $its getGuides $guides] }
proc ord::get_db_block {} { return blk }
proc ord::get_db_tech {} { return tech }
mkobj tech {getDbUnitsPerMicron 1000}
master BUFx4_ASAP7_75t_R; master DFFHQNx1_ASAP7_75t_R; master SRAM 1
proc estimate_parasitics {args} { L est {*}$args }
proc sta::find_pin {n} { return $n }
proc sta::db_net_to_sta {n} { return $n }
proc get_property {p prop} { if {[info exists ::slew($p)]} { return $::slew($p) }; return 10.0 }
proc insert_buffer {args} { L insert_buffer {*}$args
  foreach k [array names ::wl] { set ::wl($k) 10.0 }; foreach k [array names ::slew] { set ::slew($k) 10.0 } }
proc detailed_placement {args} { L [string trim "dpl $args"] }
proc check_placement {args} { L check_placement }
proc global_route {args} { L global_route {*}$args }
proc suppress_message {args} {}
proc unsuppress_message {args} {}
proc grt::create_wl_report_file {f v} { set fh [open $f w]; puts $fh "tool net total_wl #pins "; close $fh }
proc grt::report_net_wire_length {n g d v f} { set fh [open $f a]; puts $fh "grt: [$n getName] $::wl([$n getName]) 2"; close $fh }
"""
BLOCK = r"""
proc blk {m args} {
  switch $m {
    getNets { return $::nets }
    getInsts { return $::insts }
    findNet { set k findNet_[lindex $args 0]; if {[dict exists $::obj(blk) $k]} { return [dict get $::obj(blk) $k] }; return NULL }
  }
}
set ::obj(blk) {}
"""
# one branch: drv (BUF at 0,0) -> one leaf BUF 248 um away over an SRAM macro; one short leaf net to a flop
DESIGN = r"""
inst drv BUFx4_ASAP7_75t_R 0 0; inst lb BUFx4_ASAP7_75t_R 200000 48000; inst ff DFFHQNx1_ASAP7_75t_R 10000 0
inst mac SRAM 80000 0 60000 60000
iterm d_o drv Y 1; iterm lb_a lb A 0; iterm lb_y lb Y 1; iterm ff_ck ff CLK 0
box gb1 70000 10000 150000 20000; mkobj g1 [list getBox gb1]
net clknet_br CLOCK {d_o lb_a} {g1}
net clknet_leaf CLOCK {lb_y ff_ck}
set ::wl(clknet_br) %(wl_br)s; set ::wl(clknet_leaf) 12.0
set ::slew(lb/A) %(slew)s
set ::nets {clknet_br clknet_leaf}; set ::insts {drv lb ff mac}
"""
EMPTY = "set ::nets {}; set ::insts {}\n"


def tcl(tmp_path, body, env=None, design=EMPTY, wl_br=248.0, slew=358.0):
    if not shutil.which("tclsh"):
        pytest.skip("tclsh unavailable")
    nxt = tmp_path / "next.tcl"
    nxt.write_text("L next_sourced\n")
    script = tmp_path / "t.tcl"
    script.write_text("namespace eval ord {}; namespace eval sta {}; namespace eval grt {}\n" + MOCK + BLOCK
                      + (design % dict(wl_br=wl_br, slew=slew) if "%" in design else design)
                      + body.replace("@CLR@", str(CLR)).replace("@NEXT@", str(nxt))
                      + "\nputs \"LOG=[join $::log |]\"\n")
    e = {k: v for k, v in os.environ.items() if not k.startswith(("OT_CLK_LEAF", "OT_CLR", "POST_CTS"))}
    p = subprocess.run(["tclsh", str(script)], env=dict(e, **(env or {})), capture_output=True, text=True, cwd=tmp_path)
    assert p.returncode == 0, p.stdout + p.stderr
    log = [ln for ln in p.stdout.splitlines() if ln.startswith("LOG=")][-1][4:]
    return p.stdout, log.split("|") if log else []


DEFAULT = "set ::ot_clr_default 1; source @CLR@; unset -nocomplain ::ot_clr_default\n"
GRT_RUN = "proc helper {} { set ::ot_clr_stage grt; source @CLR@; unset -nocomplain ::ot_clr_stage }; helper\n"


def test_default_runs_once_and_never_sources_next(tmp_path):
    out, log = tcl(tmp_path, DEFAULT + DEFAULT)
    assert out.count("OT_CLK_LEAF_REPEAT done: 0 nets repeated") == 1
    assert "OT_CLK_LEAF_REPEAT already ran in this process: skipped" in out
    assert "next_sourced" not in log


def test_explicit_hook_after_default_skips_body_but_chains_next(tmp_path):
    out, log = tcl(tmp_path, DEFAULT + "source @CLR@\n", env={"OT_CLR_NEXT_TCL": str(tmp_path / "next.tcl")})
    # OT_CLR_NEXT_TCL set = kit-wave LEAFSLEW chain: the default run steps aside, the explicit hook runs + chains
    assert "default run skipped" in out and out.count("OT_CLK_LEAF_REPEAT done") == 1
    assert log.count("next_sourced") == 1


@pytest.mark.parametrize("hook", ["direct", "sourced"])
def test_default_skipped_when_kit_hooks_it(tmp_path, hook):
    post = tmp_path / "post.tcl"
    post.write_text("source /work/clk_leaf_repeat.tcl\n" if hook == "sourced" else "# tap balance\n")
    target = str(post) if hook == "sourced" else "/work/clk_leaf_repeat.tcl"
    out, _ = tcl(tmp_path, DEFAULT, env={"POST_CTS_TCL": target})
    assert "default run skipped" in out and "OT_CLK_LEAF_REPEAT done" not in out


def test_default_runs_with_unrelated_post_cts_hook(tmp_path):
    post = tmp_path / "post.tcl"
    post.write_text("puts tap_balance\n")
    out, _ = tcl(tmp_path, DEFAULT, env={"POST_CTS_TCL": str(post)})
    assert "OT_CLK_LEAF_REPEAT done: 0 nets repeated" in out


@pytest.mark.parametrize("body", [DEFAULT, GRT_RUN])
def test_opt_out_both(tmp_path, body):
    out, log = tcl(tmp_path, body, env={"OT_CLK_LEAF_REPEAT": "0"}, design=DESIGN)
    assert "OT_CLK_LEAF_REPEAT" not in out and not any(x.startswith(("insert_buffer", "global_route")) for x in log)


def test_cts_no_net_over_rule_is_noop(tmp_path):
    # placement-stage rule (unchanged): the long branch's placement-estimated slew is the mock 10 ps < 80 -> kept
    out, log = tcl(tmp_path, DEFAULT, design=DESIGN, slew=10.0)
    assert "OT_CLK_LEAF_REPEAT done: 0 nets repeated, 0 repeaters" in out
    assert not any(x.startswith(("insert_buffer", "dpl")) for x in log)


def test_grt_long_branch_repeated_on_routed_length(tmp_path):
    out, log = tcl(tmp_path, GRT_RUN, design=DESIGN)
    assert "net clknet_br routed 248.0 um, GRT est slew 358.0 ps, 1 loads" in out
    ins = [x for x in log if x.startswith("insert_buffer")]
    assert len(ins) == 1 and "-load_pins lb/A" in ins[0] and "-buffer_cell BUFx4_ASAP7_75t_R" in ins[0]
    # inside an incremental GRT, then the GRT parasitics are re-estimated
    i = log.index(ins[0])
    assert log[i - 2:i] == ["global_route -start_incremental", "dpl"]
    # the new net (found through the moved load pin) is a CLOCK net; then DPL + incremental GRT + GRT parasitics
    assert log[i + 1:i + 5] == ["setSigType lb_a CLOCK", "dpl", "global_route -end_incremental", "est -global_routing"]
    assert "OT_CLK_LEAF_REPEAT grt done: 1 nets repeated, 1 repeaters" in out
    assert "next_sourced" not in log


def test_grt_over_macro_branch_repeated_below_length(tmp_path):
    out, log = tcl(tmp_path, GRT_RUN, design=DESIGN, wl_br=90.0)
    assert "routed 90.0 um over a macro" in out and sum(x.startswith("insert_buffer") for x in log) == 1


def test_grt_slew_gate_and_short_nets_keep_design(tmp_path):
    out, log = tcl(tmp_path, GRT_RUN, design=DESIGN, slew=120.0)          # long, but GRT slew <= 150
    assert "grt done: 0 nets repeated, 0 repeaters (1 long / over-macro nets kept" in out
    out, log = tcl(tmp_path, GRT_RUN, design=DESIGN, wl_br=40.0)          # short, no macro rule below 50 um
    assert "grt done: 0 nets repeated" in out
    assert not any(x.startswith(("insert_buffer", "global_route")) for x in log)


def test_grt_pass_opt_out(tmp_path):
    out, log = tcl(tmp_path, GRT_RUN, env={"OT_CLK_LEAF_GRT": "0"}, design=DESIGN)
    assert "OT_CLK_LEAF_REPEAT" not in out and not log


# MACRO-CK-PIN (S81-TYPES-5 11-07, serdes__t2): a clock load on a 2000-um macro is located at its PIN, not the macro
# centre; drv at (0,0), macro 2000x100 um at (100,1000) um with ck 10 um from its left edge -> repeater half way to
# the pin (55, 500), not to the centre (1100, 1050) um.
MACRO_CK = r"""
inst drv BUFx4_ASAP7_75t_R 0 0
inst pma SRAM 100000 1000000 2000000 100000
iterm d_o drv Y 1; iterm pma_ck pma ck 0
box pb 110000 1000000 110000 1000000; dict set ::obj(pma_ck) getBBox pb
net clknet_pma CLOCK {d_o pma_ck}
set ::slew(pma/ck) 5000.0
set ::nets {clknet_pma}; set ::insts {drv pma}
"""


def test_cts_macro_clock_load_located_at_pin(tmp_path):
    out, log = tcl(tmp_path, DEFAULT, design=MACRO_CK)
    ins = [x for x in log if x.startswith("insert_buffer")]
    assert ins and "-load_pins pma/ck" in ins[0], out
    loc = ins[0].split("-location ")[1].split(" -buffer_name")[0]
    x, y = (float(v) for v in loc.strip("{}").split())
    assert abs(x - 55.0) < 1 and abs(y - 500.0) < 1, loc


# KW-FIX-35-F 11-08 (FLOW class F): one extra ordinary legalization before the mandatory CTS-stage check, only when
# the first check fails (same rule as 20cff21bab for the final DPL); the verbose check still runs and decides.
FAIL_ONCE = ("set ::cp_fail %d\n"
             "proc check_placement {args} { L check_placement {*}$args; "
             "if {$::cp_fail && $args eq {}} { set ::cp_fail 0; error DPL-0033 } }\n")
DPL_STEPS = ("dpl", "check_placement", "check_placement -verbose")


def cts_dpl_tail(log, start="insert_buffer"):
    i = next((k for k, x in enumerate(log) if x.startswith(start)), 0)
    return [x for x in log[i:] if x in DPL_STEPS or x.startswith("dpl ")]


def test_cts_residual_overlap_gets_one_more_legalization(tmp_path):
    out, log = tcl(tmp_path, FAIL_ONCE % 1 + DEFAULT, design=DESIGN)
    # KW-FIX-35-F2: the extra pass is the diamond legalizer, not a second stalled negotiation pass
    assert cts_dpl_tail(log) == ["dpl", "check_placement", "dpl -use_diamond_legalizer", "check_placement -verbose"], log
    assert out.count("OT_DPL_RESIDUAL") == 1


def test_cts_clean_first_legalization_unchanged(tmp_path):
    out, log = tcl(tmp_path, FAIL_ONCE % 0 + DEFAULT, design=DESIGN)
    assert cts_dpl_tail(log) == ["dpl", "check_placement", "check_placement -verbose"], log
    assert "OT_DPL_RESIDUAL" not in out


# KW-FIX-35-F2 11-08 (FLOW class F follow-up): CTS legalization uses the kit's 3_5 legalizer.  ORFS erases
# DETAIL_PLACEMENT_ARGS outside the place stage, so grt183_make.sh captures it in cts.tcl before the erase
# (::ot_kit_dpl_args); clk_leaf_repeat reads that (env as fallback).  QC sle_hc1__cl7d360508 a10R: negotiation 512 left
# at CTS where 3_5 diamond was 100 % legal.
KIT_DPL = "-use_diamond_legalizer -max_displacement {614 1340}"
KIT_DIAMOND = "dpl -use_diamond_legalizer -max_displacement {614 1340}"


@pytest.mark.parametrize("how", ["captured", "env"])
def test_cts_diamond_kit_legalizes_with_kit_args(tmp_path, how):
    pre = "set ::ot_kit_dpl_args {%s}\n" % KIT_DPL if how == "captured" else ""
    env = {"DETAIL_PLACEMENT_ARGS": KIT_DPL} if how == "env" else None
    out, log = tcl(tmp_path, FAIL_ONCE % 1 + pre + DEFAULT, design=DESIGN, env=env)
    assert cts_dpl_tail(log) == [KIT_DIAMOND, "check_placement", KIT_DIAMOND, "check_placement -verbose"], log


def test_cts_captured_args_win_over_erased_env(tmp_path):
    # ORFS erased the env var (captured value set); a non-diamond capture leaves the first pass a bare call
    out, log = tcl(tmp_path, FAIL_ONCE % 0 + "set ::ot_kit_dpl_args {}\n" + DEFAULT, design=DESIGN,
                   env={"DETAIL_PLACEMENT_ARGS": KIT_DPL})
    assert cts_dpl_tail(log) == ["dpl", "check_placement", "check_placement -verbose"], log


def test_cts_no_repeater_residual_repaired_not_gated(tmp_path):
    out, log = tcl(tmp_path, FAIL_ONCE % 1 + DEFAULT, design=DESIGN, slew=10.0)   # no net over the rule
    assert not any(x.startswith("insert_buffer") for x in log)
    assert cts_dpl_tail(log, "check_placement") == ["check_placement", "dpl -use_diamond_legalizer", "check_placement"], log
    assert "CTS check after the extra legalization: PASS" in out and "check_placement -verbose" not in log


def test_cts_no_repeater_clean_unchanged(tmp_path):
    out, log = tcl(tmp_path, FAIL_ONCE % 0 + DEFAULT, design=DESIGN, slew=10.0)
    assert cts_dpl_tail(log, "check_placement") == ["check_placement"], log
    assert "OT_DPL_RESIDUAL" not in out


CTS_ORFS = ("source $::env(SCRIPTS_DIR)/load.tcl\nerase_non_stage_variables cts\nload_design 3_place.odb 3_place.sdc\n"
            "set result [catch { log_cmd detailed_placement } msg]\nsource_step_tcl POST CTS\n")


def wrap_cts(tmp_path, cfg=""):
    w, s = wrap_kit(tmp_path, cfg)
    (s / "cts.tcl").write_text(CTS_ORFS)
    return w, s


def test_wrapper_captures_dpl_args_before_erase_once(tmp_path):
    w, s = wrap_cts(tmp_path)
    for _ in range(2):
        p = run_wrap(w, s)
        assert p.returncode == 0, p.stdout + p.stderr
    c = (s / "cts.tcl").read_text().splitlines()
    i = c.index("erase_non_stage_variables cts")
    assert c[i - 1].startswith("set ::ot_kit_dpl_args ") and c[i - 1].endswith(";# OT_CTS_DPL_ARGS")
    assert sum("OT_CTS_DPL_ARGS" in x for x in c) == 1


def test_wrapper_cts_dpl_args_opt_out(tmp_path):
    w, s = wrap_cts(tmp_path, "export OT_CTS_DPL_ARGS = 0\n")
    assert run_wrap(w, s).returncode == 0
    assert "OT_CTS_DPL_ARGS" not in (s / "cts.tcl").read_text()


@pytest.mark.parametrize("kit", [KIT_DPL, "", "-disallow_one_site_gaps"])
def test_cts_dpl_args_line_behaviour(tmp_path, kit):
    if not shutil.which("tclsh"):
        pytest.skip("tclsh unavailable")
    w, s = wrap_cts(tmp_path)
    assert run_wrap(w, s).returncode == 0
    line = next(x for x in (s / "cts.tcl").read_text().splitlines() if "OT_CTS_DPL_ARGS" in x)
    t = tmp_path / "l.tcl"
    t.write_text("set ::log {}\nproc detailed_placement {args} { lappend ::log [string trim \"dpl $args\"] }\n" + line + "\n"
                 "array unset ::env DETAIL_PLACEMENT_ARGS\n"            # ORFS erase after the capture
                 "detailed_placement\ndetailed_placement -max_displacement {5 1}\nputs LOG=[join $::log |]\n")
    e = {k: v for k, v in os.environ.items() if k != "DETAIL_PLACEMENT_ARGS"}
    if kit:
        e["DETAIL_PLACEMENT_ARGS"] = kit
    p = subprocess.run(["tclsh", str(t)], env=e, capture_output=True, text=True)
    assert p.returncode == 0, p.stdout + p.stderr
    log = [x for x in p.stdout.splitlines() if x.startswith("LOG=")][0][4:].split("|")
    first = "dpl " + kit if "diamond" in kit else "dpl"
    assert log == [first, "dpl -max_displacement {5 1}"], log      # explicit args always pass through unchanged
    assert ("OT_CTS_DPL_ARGS:" in p.stdout) == ("diamond" in kit)
