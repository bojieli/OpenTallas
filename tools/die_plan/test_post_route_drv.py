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
  *do-finish*) echo fin > $B/6_final.odb; echo "$W" >> $FAKE_LOG.finish; exit 0 ;;
  *) exit 0 ;;
esac
'''


def make_kit(tmp, mm=True):
    k = tmp / "kit"
    b = k / "run" / "results" / "asap7" / NICK / "base"
    b.mkdir(parents=True)
    (b / "5_1_grt.odb").write_text("kit grt\n")
    (b / "6_final.spef").write_text("*SPEF kit routed\n")
    (k / "constraint.sdc").write_text("create_clock -period 833 [get_ports clk]\n")
    cfg = "export DESIGN_NICKNAME = %s\nexport ADDITIONAL_LIBS =\n" % NICK
    if mm:
        cfg += "override export OT_HOLD_MM = 1\n"
    (k / "config.mk").write_text(cfg)
    (k / "run_kit_hbm.sh").write_text('#!/bin/bash\n# GOAL=post\necho "post $1 $2" >> "$FAKE_LOG.post"\n')
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


def test_mk_refuses_ff_only_variant_on_two_mode_kit(tmp_path):
    kit = make_kit(tmp_path)
    r = mk(kit, tmp_path / "p1", "b10")
    assert r.returncode == 2 and "use variant m" in r.stdout


def test_hook_sink_guard_order():
    s = (PRD / "prd_hook.tcl").read_text()
    order = ["ot_clk_freeze\n", "set_dont_use $lc", "repair_design -slew_margin", "repair_timing -setup",
             "repair_timing {*}$args", "set ::ot_prd_reverted [ot_prd_sink_revert]", "\ndetailed_placement\n",
             "check_placement", "global_route -end_incremental", "ot_clk_freeze_assert post_grt"]
    pos = [s.index(x) for x in order]
    assert pos == sorted(pos), list(zip(order, pos))
    assert "read_spef $::env(RESULTS_DIR)/6_final.spef" in s
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


def test_loop_second_pass_reads_pass1_rcx_and_stops_at_two(tmp_path):
    r, res, log = run_loop(tmp_path, "p1_tc=1038,p1_bc=648,p2_tc=12,p2_bc=3")
    assert r.returncode == 0, r.stdout + r.stderr
    p2 = tmp_path / "p1_p2"
    assert [p["pass"] for p in res["passes"]] == ["1", "2"] and res["passes"][1]["tc_slew"] == "12"
    assert log("route") == [str(tmp_path / "p1"), str(p2)]        # never a third pass
    b2 = p2 / "run/results/asap7" / NICK / "base"
    # pass 2 starts from pass 1's ECO'd GRT DB and repairs on pass 1's re-extracted RCX of its filled route
    assert (b2 / "4_cts.odb").read_text() == "pass 1 5_1_grt.odb\n"
    assert (b2 / "6_final.spef").read_text().startswith("*SPEF rcx of pass 1 5_route.odb")
    assert res["final"]["dir"] == str(p2) and log("finish") == [str(p2)]
    assert (p2 / "config.mk").read_text().count("# OT_PRD post-route drive repair") == 1


def test_loop_route_failure_stops_without_signoff(tmp_path):
    r, res, log = run_loop(tmp_path, "p1_tc=5", FAKE_ROUTE_RC=2)
    assert r.returncode == 2 and "final" not in res and res["passes"][0]["route_rc"] == "2"
    assert log("finish") == [] and log("post") == []
