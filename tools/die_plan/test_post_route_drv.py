"""FLOW-CLOCK-R7 2026-10-29: shared post-route drive repair (tools/die_plan/post_route_drv) -- the three fixes the R6
HBM bdring canary measured (two-mode session staged, clock-freeze sink masters never resized, <= 2 passes on the
re-extracted RCX), the kit's own runner kept, opt-in only.  The loop runs against a fake `docker` (no OpenROAD)."""
import json
import os
import re
import stat
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PRD = ROOT / "tools" / "die_plan" / "post_route_drv"
NICK = "hbc_x"

FAKE_DOCKER = r'''#!/bin/bash
# fake docker for test_post_route_drv: dispatch on the container command
[ "$1" = ps ] && exit 0
shift
W=; declare -A E
while [ $# -gt 0 ]; do
  case $1 in
    -v) W=${2%%:/work}; shift 2 ;;
    -e) E[${2%%=*}]=${2#*=}; shift 2 ;;
    --*=*) shift ;;
    --rm) shift ;;
    --name|--cpus|--memory|--memory-swap|-w) shift 2 ;;
    *) break ;;
  esac
done
cmd="${*: -1}"
B=$(ls -d $W/run/results/asap7/*/base 2>/dev/null | head -1)
w() { echo "${1/\/work/$W}"; }
case "$cmd" in
  *do-route*)
    p=${E[OT_PRD_PASS]}; echo "$W" >> $FAKE_LOG.route
    echo "OT_PRD pass $p hook done (sink masters restored ${FAKE_RESTORED:-0})" > $W/run/logs/asap7/$NICK/base/5_1_grt.log
    for f in 5_1_grt.odb 5_2_route.odb 5_route.odb; do echo "pass $p $f" > $B/$f; done
    printf '#CLKDUMP tag pre nets 1 block top\nNET\tclkA\tCLOCK\t0\t\t\nPIN\tclkA\tb0/Y f1/CLK\nINST\tb0\tBUFx4_ASAP7_75t_R\t1\t2\tR0\tLOCKED\n' > $B/clk_freeze_pre.tsv
    echo clkA > $B/clk_freeze_nets.txt
    exit ${FAKE_ROUTE_RC:-0} ;;
  *clk_dump_db.tcl*)
    sed 's/tag pre/tag post/; s/\t0\t\t$/\t2\t64\t0:M3 4:1/' $B/clk_freeze_pre.tsv > $(w ${E[OT_OUT]}); exit 0 ;;
  *prd_count.tcl*)
    t=${E[TAG]}; n=$(echo ",$FAKE_COUNTS," | sed -n "s/.*,$t=\([0-9]*\),.*/\1/p")
    s=$(w ${E[SPEF]}); test -f $s || echo "*SPEF rcx of $(cat $(w ${E[ODB]}))" > $s
    echo "$t odb=$(w ${E[ODB]})" >> $FAKE_LOG.count
    echo "OT_PRD_COUNT $t slew ${n:-0} cap 0 placement ok"; exit 0 ;;
  *do-finish*) echo fin > $B/6_final.odb; echo "$W" >> $FAKE_LOG.finish; echo "$cmd" > $W/finish_cmd.txt; exit 0 ;;
  *) exit 0 ;;
esac
'''


def make_kit(tmp, mm=True):
    k = tmp / "kit"
    b = k / "run" / "results" / "asap7" / NICK / "base"
    b.mkdir(parents=True)
    (b / "4_1_cts.odb").write_text("kit ORIGINAL cts\n")
    (b / "5_1_grt.odb").write_text("kit grt\n")
    (b / "6_final.spef").write_text("*SPEF kit routed\n")
    (k / "constraint.sdc").write_text("create_clock -period 833 [get_ports clk]\n")
    cfg = "export DESIGN_NICKNAME = %s\nexport ADDITIONAL_LIBS =\n" % NICK
    if mm:
        cfg += "override export OT_HOLD_MM = 1\n"
    (k / "config.mk").write_text(cfg)
    (k / "run_kit_hbm.sh").write_text('#!/bin/bash\n# GOAL=post: sign-off only\necho "post $1 $2" >> "$FAKE_LOG.post"\n')
    return k


def env_with_fake(tmp, **extra):
    bindir = tmp / "bin"
    bindir.mkdir(exist_ok=True)
    d = bindir / "docker"
    d.write_text(FAKE_DOCKER)
    d.chmod(d.stat().st_mode | stat.S_IEXEC)
    env = dict(os.environ, PATH=f"{bindir}:{os.environ['PATH']}", FAKE_LOG=str(tmp / "log"), NICK=NICK)
    env.update({k: str(v) for k, v in extra.items()})
    return env


def mk(kit, out, variant="m10", env=None):
    return subprocess.run(["bash", str(PRD / "prd_mk.sh"), str(kit), str(out), variant, str(ROOT)],
                          capture_output=True, text=True, env=env)


def test_mk_stages_two_mode_session_and_keeps_kit_runner(tmp_path):
    kit = make_kit(tmp_path)
    r = mk(kit, tmp_path / "p1")
    assert r.returncode == 0, r.stdout + r.stderr
    p1 = tmp_path / "p1"
    v = (p1 / "variant.env").read_text()
    assert "OT_HOLD_MM_KIT=1" in v and "OT_ECO_FROM=grt" in v and 'CORNERS=\\"tc bc\\"' in v or 'CORNERS="tc bc"' in v
    assert (p1 / "orfs_hold_mm.py").is_file() and (p1 / "orfs_hold_mm.tcl").is_file()   # fix 1
    assert not (p1 / "run_kit_kv.sh").exists()                                          # no KV runner over a non-KV kit
    assert (p1 / "run_kit_hbm.sh").is_file()
    eco = (p1 / "eco_post.tcl").read_text().splitlines()
    assert eco[:3] == ["source /work/kit_modes_eco.tcl", "source /work/prd_hook.tcl", "kit_modes_eco_done"]
    base = p1 / "run/results/asap7" / NICK / "base"
    assert (base / "4_cts.odb").read_text() == "kit grt\n" and (base / "6_final.spef").read_text() == "*SPEF kit routed\n"
    assert "set_propagated_clock [all_clocks]" in (base / "4_cts.sdc").read_text()
    assert "override export POST_GLOBAL_ROUTE_TCL = /work/eco_post.tcl" in (p1 / "config.mk").read_text()
    # never relaunched into an existing dir
    assert mk(kit, p1).returncode == 2


def test_mk_maps_standard_cell_libs_to_ff(tmp_path):
    # DIE-KV-46 10-30: an explicit platform INVBUF_LVT TT lib was refused as 'missing FF macro lib'
    kit = make_kit(tmp_path)
    nl = "/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM"
    for f in ("macros/m_tt.lib", "macros/m_ff.lib", "stdlib_lvt/asap7sc7p5t_INVBUF_LVT_TT_nldm_220122.lib.gz",
              "stdlib_lvt/asap7sc7p5t_INVBUF_LVT_FF_nldm_220122.lib.gz"):
        (kit / f).parent.mkdir(parents=True, exist_ok=True)
        (kit / f).write_text("library(x) {}\n")
    libs = (f"/work/macros/m_tt.lib {nl}/asap7sc7p5t_INVBUF_LVT_TT_nldm_220122.lib.gz "
            "/work/stdlib_lvt/asap7sc7p5t_INVBUF_LVT_TT_nldm_220122.lib.gz")
    cfg = (kit / "config.mk").read_text().replace("export ADDITIONAL_LIBS =\n", f"export ADDITIONAL_LIBS = {libs}\n")
    (kit / "config.mk").write_text(cfg)
    r = mk(kit, tmp_path / "p1")
    assert r.returncode == 0, r.stdout + r.stderr
    bc = [l for l in (tmp_path / "p1" / "config.mk").read_text().splitlines() if l.startswith("export BC_LIB_FILES")][-1]
    assert bc.split()[4:] == ["/work/macros/m_ff.lib", f"{nl}/asap7sc7p5t_INVBUF_LVT_FF_nldm_220122.lib.gz",
                              "/work/stdlib_lvt/asap7sc7p5t_INVBUF_LVT_FF_nldm_220122.lib.gz"]
    # a /work copy without its FF twin still fails closed
    (kit / "stdlib_lvt/asap7sc7p5t_INVBUF_LVT_FF_nldm_220122.lib.gz").unlink()
    r = mk(kit, tmp_path / "p2")
    assert r.returncode == 2 and "missing FF macro lib /work/stdlib_lvt/" in r.stdout


def test_mk_no_fanout_limit_by_default(tmp_path):
    # R8: sign-off fanout is WARN-only; a default max_fanout split wide nets with weak buffers (bdring TT setup -22 -> -40)
    kit = make_kit(tmp_path)
    assert mk(kit, tmp_path / "p1").returncode == 0
    assert "OT_MAX_FANOUT=0" in (tmp_path / "p1" / "variant.env").read_text().splitlines()
    r = mk(kit, tmp_path / "p2", env=dict(os.environ, OT_PRD_MAX_FANOUT="24"))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "OT_MAX_FANOUT=24" in (tmp_path / "p2" / "variant.env").read_text().splitlines()
    assert mk(kit, tmp_path / "p3", env=dict(os.environ, OT_PRD_MAX_FANOUT="x")).returncode == 2


def test_mk_refuses_ff_only_variant_on_two_mode_kit(tmp_path):
    kit = make_kit(tmp_path)
    r = mk(kit, tmp_path / "p1", "b10")
    assert r.returncode == 2 and "use variant m" in r.stdout


def test_hook_sink_guard_order():
    s = (PRD / "prd_hook.tcl").read_text()
    order = ["ot_clk_freeze\n", "set_dont_use $lc", "repair_design {*}${_drv_args}", "repair_timing -setup",
             "ot_repair_hold_guarded $args", "repair_timing -hold {*}$args", "set ::ot_prd_reverted [ot_prd_sink_revert]", "\ndetailed_placement\n",
             "check_placement", "global_route -end_incremental", "ot_clk_freeze_assert post_grt"]
    pos = [s.index(x) for x in order]
    assert pos == sorted(pos), list(zip(order, pos))
    assert "read_spef $::env(RESULTS_DIR)/6_final.spef" in s
    # two-mode kits use the shared chunk-capped hold guard (no -hold in the guarded args: the guard adds it)
    assert "if {[llength [info commands ot_repair_hold_guarded]] && [ot_hold_guard_on]}" in s
    assert "set args [list -hold_margin" in s
    # buffer / inverter / hold-cell families are never made dont_use (repair needs them)
    assert re.search(r"regexp \{\^\(BUF\|INV\|HB\[0-9\]\|CKINV\)\}", s)


def test_hook_family_pattern():
    s = (PRD / "prd_hook.tcl").read_text()
    proc = s[s.index("proc ot_prd_family"):]
    proc = proc[:proc.index("\n}\n") + 3]
    tcl = proc + ("foreach m {DFFHQNx1_ASAP7_75t_R DFFHQNx3_ASAP7_75t_R ICGx2p67DC_ASAP7_75t_R DFFLQNx1_ASAP7_75t_SL "
                  "sram_bank_256x64} { puts [ot_prd_family $m] }\n")
    out = subprocess.run(["tclsh"], input=tcl, capture_output=True, text=True).stdout.split()
    assert out == ["DFFHQNx*_ASAP7_75t_R", "DFFHQNx*_ASAP7_75t_R", "ICGx*_ASAP7_75t_R", "DFFLQNx*_ASAP7_75t_SL",
                   "sram_bank_256x64"]


def run_loop(tmp_path, counts, maxp=2, **extra):
    kit = make_kit(tmp_path)
    p1 = tmp_path / "p1"
    env = env_with_fake(tmp_path, FAKE_COUNTS=counts, **extra)
    assert mk(kit, p1, env=env).returncode == 0
    r = subprocess.run(["bash", str(PRD / "prd_run.sh"), str(p1), "2", "4", str(maxp)], capture_output=True, text=True, env=env)
    res = json.loads((p1 / "prd_result.json").read_text())
    log = lambda k: (tmp_path / f"log.{k}").read_text().split() if (tmp_path / f"log.{k}").exists() else []
    return r, res, log


def test_loop_stops_after_one_clean_pass(tmp_path):
    r, res, log = run_loop(tmp_path, "p1_tc=0,p1_bc=0")
    assert r.returncode == 0, r.stdout + r.stderr
    assert len(res["passes"]) == 1 and res["passes"][0]["tc_slew"] == "0" and res["passes"][0]["clk_check_rc"] == "0"
    assert res["final"]["dir"] == str(tmp_path / "p1") and res["final"]["post_runner"] == "run_kit_hbm.sh"
    assert log("route") == [str(tmp_path / "p1")] and log("finish") == [str(tmp_path / "p1")]
    assert log("post") == ["post", str(tmp_path / "p1"), "post"]
    # finish runs in the variant's corners as ONE make word list (R7 canary: unquoted expansion broke 'CORNERS="tc bc"')
    assert 'do-finish CORNER=TC CORNERS="tc bc"' in (tmp_path / "p1" / "finish_cmd.txt").read_text()


def test_final_only_resume_keeps_pass_record(tmp_path):
    r, res, log = run_loop(tmp_path, "p1_tc=0,p1_bc=0")
    p1 = tmp_path / "p1"
    env = env_with_fake(tmp_path, OT_PRD_FINAL_ONLY=p1)
    r2 = subprocess.run(["bash", str(PRD / "prd_run.sh"), str(p1), "2", "4"], capture_output=True, text=True, env=env)
    assert r2.returncode == 0, r2.stdout + r2.stderr
    assert json.loads((p1 / "prd_result.json").read_text())["passes"][0]["tc_slew"] == "0"   # pass record kept
    fin = json.loads((p1 / "prd_result_final.json").read_text())
    assert fin["passes"] == [] and fin["final"]["dir"] == str(p1)
    assert log("route") == [str(p1)] and log("finish") == [str(p1), str(p1)]


def test_post_only_with_signoff_goal(tmp_path):
    kit = make_kit(tmp_path)
    (kit / "run_kit_hbm.sh").unlink()
    (kit / "run_kit.sh").write_text('#!/bin/bash\n# post-synth face_guard; run_kit.sh KITDIR [GOAL=finish]\necho "x" >> "$FAKE_LOG.post"\n')
    p1 = tmp_path / "p1"
    env = env_with_fake(tmp_path, FAKE_COUNTS="p1_tc=0,p1_bc=0")
    assert mk(kit, p1, env=env).returncode == 0
    r = subprocess.run(["bash", str(PRD / "prd_run.sh"), str(p1), "2", "4"], capture_output=True, text=True, env=env)
    res = json.loads((p1 / "prd_result.json").read_text())
    assert r.returncode == 0 and res["final"]["post_runner"] == "-" and not (tmp_path / "log.post").exists()


def test_loop_second_pass_reads_pass1_rcx_and_stops_at_two(tmp_path):
    r, res, log = run_loop(tmp_path, "p1_tc=1038,p1_bc=648,p2_tc=12,p2_bc=3")
    assert r.returncode == 0, r.stdout + r.stderr
    p2 = tmp_path / "p1_p2"
    assert [p["pass"] for p in res["passes"]] == ["1", "2"] and res["passes"][1]["tc_slew"] == "12"
    assert log("route") == [str(tmp_path / "p1"), str(p2)]        # never a third pass
    b2 = p2 / "run/results/asap7" / NICK / "base"
    # pass 2 starts from pass 1's ECO'd GRT DB and repairs on pass 1's re-extracted RCX of its filled route
    assert (b2 / "4_cts.odb").read_text() == "pass 1 5_1_grt.odb\n"
    assert (b2 / "4_1_cts.odb").read_text() == "kit ORIGINAL cts\n"
    assert (b2 / "6_final.spef").read_text().startswith("*SPEF rcx of pass 1 5_route.odb")
    assert res["final"]["dir"] == str(p2) and log("finish") == [str(p2)]
    assert (p2 / "config.mk").read_text().count("# OT_PRD post-route drive repair") == 1


def test_loop_route_failure_stops_without_signoff(tmp_path):
    r, res, log = run_loop(tmp_path, "p1_tc=5", FAKE_ROUTE_RC=2)
    assert r.returncode == 2 and "final" not in res and res["passes"][0]["route_rc"] == "2"
    assert log("finish") == [] and log("post") == []


def test_optional_wire_limit_uses_real_repair_command():
    import subprocess
    source = (PRD / "prd_hook.tcl").read_text()
    start = source.index("set _drv_args")
    end = source.index("repair_design {*}${_drv_args}", start) + len("repair_design {*}${_drv_args}")
    fragment = source[start:end]
    prefix = "set ::env(OT_SLEW_MARGIN) 20\nset _pass 1\nproc repair_design {args} {puts \"CALL $args\"}\n"
    for limit, expected in ((None, "-slew_margin 20 -cap_margin 20"), (100, "-slew_margin 20 -cap_margin 20 -max_wire_length 100")):
        envset = "" if limit is None else f"set ::env(OT_PRD_MAX_WIRE_LENGTH) {limit}\n"
        result = subprocess.run(["tclsh"], input=prefix + envset + fragment, text=True, capture_output=True)
        assert result.returncode == 0 and not result.stderr, result.stderr
        assert f"CALL {expected}" in result.stdout


def test_finish_passes_both_mm_corners_as_one_make_argument(tmp_path):
    result, record, log = run_loop(tmp_path, "p1_tc=0,p1_bc=0")
    assert result.returncode == 0, result.stdout + result.stderr
    command = (tmp_path / "p1" / "finish_cmd.txt").read_text()
    command = command[command.index("make DESIGN_CONFIG="):]
    argfile = tmp_path / "make_args.txt"
    prefix = 'make() { printf "%s\\n" "$@" > "$ARGFILE"; }; '
    env = dict(os.environ, ARGFILE=str(argfile), ROUTE_CORNERS='CORNER=TC CORNERS="tc bc"')
    run = subprocess.run(["bash", "-c", prefix + command], env=env, capture_output=True, text=True)
    assert run.returncode == 0, run.stderr
    args = argfile.read_text().splitlines()
    assert "CORNER=TC" in args and "CORNERS=tc bc" in args
    assert 'bc"' not in args
    # Old R7 expanded this variable inside the container: quote characters in
    # its value become data, so word splitting creates a literal bc" target.
    mutant = command.replace('CORNER=TC CORNERS="tc bc"', '$ROUTE_CORNERS')
    bad = subprocess.run(["bash", "-c", prefix + mutant], env=env, capture_output=True, text=True)
    assert bad.returncode == 0, bad.stderr
    broken = argfile.read_text().splitlines()
    assert "CORNERS=tc bc" not in broken and 'bc"' in broken


def test_prd_preserves_original_cts_stage_identity_and_refuses_missing_checkpoint(tmp_path):
    kit=make_kit(tmp_path)
    out=tmp_path/"prd_stage"
    result=mk(kit,out)
    assert result.returncode==0,result.stdout+result.stderr
    base=out/"run/results/asap7"/NICK/"base"
    assert (base/"4_1_cts.odb").read_text()=="kit ORIGINAL cts\n"
    assert (base/"4_cts.odb").read_text()=="kit grt\n"
    # Exercise the real stage-policy selector, rather than a test imitation.
    source=(ROOT/"tools/orfs_hold_mm.tcl").read_text()
    stage=re.search(r"proc ot_hold_stage \{\} \{\n.*?\n\}",source,re.S).group(0)
    script=stage+f'\nset ::env(RESULTS_DIR) {{{base}}}\nputs [ot_hold_stage]\n'
    selected=subprocess.run(["tclsh"],input=script,text=True,capture_output=True,check=True)
    assert selected.stdout.strip()=="grt" and not selected.stderr
    (kit/"run/results/asap7"/NICK/"base/4_1_cts.odb").unlink()
    missing=tmp_path/"missing_cts"
    result=mk(kit,missing)
    assert result.returncode==2 and "lacks original 4_1_cts.odb" in result.stdout
    assert not missing.exists()  # never fake a checkpoint or create an invalid vehicle
