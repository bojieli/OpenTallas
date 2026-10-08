#!/usr/bin/env python3
"""Closure-loop job specs of stream qwen-band-integrate (2026-10-08): OPTION-B TT routes (ORFS corner TC = setup repair
at TT, MM FF hold HM 50 ps, rule H1, CTS fix hooks + the consistent die-link budget through the TT-batch overlay
snapshot) of the masters this stream changed:
  qfd_sp_tree_top_b(_t)   ot_qfd_sp_tree_top BAND 1 (ot_qfd_band_upper inside, control element RX / BANDF), LANDED 1;
  slab_s14o_bf / s14ok_bf ot_qwen_slab_port_group BANDF 1 (band-local group index), the s14o / s14ok die element.
Benches gate adoption, not launch: the split-spine end-to-end bench (tb_qfd_spine_band) with its negative mutants, the
tree-top BAND 0 regressions, and the slab element bench in the band frame with its negative mutant.  Every expected-FAIL
bench exits non-zero on FAIL (the loop reads a mutant's rc).

    mk_jobs.py --commit <sha> [--out DIR]
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "qwen_vm_me"))
import mk_jobs as VM  # noqa: E402

OWNER = "Claude:qwen-band-integrate"
BRANCH = "claude/qwen-band-integrate-20261008"
REC = "results/rtl/qwen_band_integrate_20261008"
TTB = ("TTB=$(ls -d /srv/opentallas-scratch/claude/ttbatch/26f14af32 /home/ubuntu/closure-loop-local/ttbatch/26f14af32 "
       "2>/dev/null | head -1) && export OT_TTB_CORNER_MARK={CL}/ttb_corner.txt && python3 $TTB/tools/closure_loop/"
       "tt_overlay.py {SRC} && export OT_CTS_FIX_HOOKS='physical/common_flow/cg_pushdown.tcl "
       "physical/common_flow/clk_net_protect.tcl physical/common_flow/link_budget_hook.tcl'; "
       "export OT_ORFS_CORNER_OVERRIDE=TC; ")
SB = "rtl/test/qwen_band_integrate/run_spine_band.sh"
REAL = "-GTCUT=7 -GSMAX=11 -GMAXT=2 -GMAXK=2"     # the Qwen die geometry: GT 6,144, splits 7..11


def sbench(name, g, exp, ram=16, threads=8):
    b = dict(name=name, cmd=f"mkdir -p {{RUN}}/bench && JOBS={threads} bash {SB} {{RUN}}/bench/{name} {g}",
             expect=exp, threads=threads, peak_ram_gb=ram, needs=["verilator"])
    b["pass_regex" if exp == "pass" else "fail_regex"] = f"^{'PASS' if exp == 'pass' else 'FAIL'} qfd_spine_band"
    return b


def spine_benches(full=True):
    out = [sbench("sb_exact", "-GCYCLES=40000 -GSEED=1", "pass"),
           sbench("sb_link", "-GLNK=1 -GCLNK=2 -GCYCLES=40000 -GSEED=2", "pass"),
           sbench("sb_mut_band", "-GBMUT=1 -GCYCLES=8000", "fail"),
           sbench("sb_mut_frame", "-GPBANDF=0 -GCYCLES=8000", "fail")]
    if full:
        out += [sbench("sb_qwen", f"{REAL} -GQB=9 -GCYCLES=20000 -GSEED=3", "pass", ram=48, threads=16),
                sbench("sb_mut_upper", "-GUMUT=2 -GCYCLES=8000", "fail"),
                sbench("sb_mut_clnk", "-GLNK=1 -GCLNK=2 -GDMUT=1 -GCYCLES=8000", "fail")]
    return out


def regressions():
    """BAND 0 must be unchanged: qwen-vm-me's landed bench and qwen-rtl-finish's tree-top lockstep (exit codes)."""
    out = []
    b = dict(name="reg_landed", cmd="mkdir -p {RUN}/bench && JOBS=8 bash rtl/test/qwen_vm_me/run_spine_landed.sh "
             "{RUN}/bench/reg_landed -GCYCLES=30000 && grep -q '^PASS qfd_spine_landed' {RUN}/bench/reg_landed/result.txt",
             expect="pass", threads=8, peak_ram_gb=16, needs=["verilator"], pass_regex="^PASS qfd_spine_landed")
    out.append(b)
    b = dict(name="reg_tree_top", cmd="mkdir -p {RUN}/bench && JOBS=8 bash rtl/test/qwen_rtl_finish/run_tree_top.sh "
             "{RUN}/bench/reg_tree_top 30000 && grep -q '\"mismatch_cycles\": 0,' {RUN}/bench/reg_tree_top/result.json "
             "&& echo PASS qfd_tree_top", expect="pass", threads=8, peak_ram_gb=16, needs=["verilator"],
             pass_regex="^PASS qfd_tree_top")
    out.append(b)
    return out


def tree_top_job(cfg, commit, purpose, benches):
    name, spec = VM.job(cfg, commit, purpose, benches, 128,
                        cycles="+5 + 2 LNK engine edges on every ME op result (band round trip; RX in the control "
                               "element); LNK 0 / CLNK 0 in this master (die parameters)")
    r = spec["stages"]["route"]
    r["cmd"] = r["cmd"].replace("export OT_TTB_CORNER_MARK={CL}/ttb_corner.txt && python3 tools/closure_loop/tt_overlay.py "
                                "{SRC} && export OT_CTS_FIX_HOOKS='physical/common_flow/cg_pushdown.tcl "
                                "physical/common_flow/clk_net_protect.tcl physical/common_flow/link_budget_hook.tcl'; "
                                "export OT_ORFS_CORNER_OVERRIDE=TC; ", TTB)
    assert r["cmd"].startswith("TTB="), r["cmd"][:80]
    spec["record"][1]["to"] = f"{REC}/routes/{name}"
    return name, spec


def slab_job(variant, commit, purpose):
    name = f"slab_{variant}-{commit[:9]}tt"
    tool = "PYTHONPATH=src:tools python3 tools/qwen_slab_m3_takeover.py"
    spec = dict(
        name=name, block="ot_qwen_slab_port_group_s14_die", owner=OWNER, purpose=purpose,
        hosts=VM.HOSTS, threads=16, peak_ram_gb=24, source=dict(branch=BRANCH, commit=commit),
        stages=dict(
            bench=[dict(name="slab_bf_exact", cmd=f"{tool} bench --variant {variant} --out {{RUN}}/bench_positive",
                        expect="pass", pass_regex="PASS: 1505 requests, 1505 results bit-exact", needs=["iverilog"]),
                   dict(name="slab_bf_mut_frame", cmd=f"{tool} bench --negative --variant {variant} --out {{RUN}}/bench_negative",
                        expect="fail", fail_regex="EQUIVALENCE_TERMINAL_FAIL", needs=["iverilog"])],
            calibrate=dict(enabled=False, reason="as slab_s14o: in-run corner-exact reference pin"),
            route=dict(cmd=TTB + "export OT_MM_FF_SDC='physical/qwen_slab_structural/signoff833_die.sdc'; export "
                       "PYTHONPATH=src:tools; set -e\n[ \"$(docker image inspect openroad/orfs:latest --format '{{.Id}}')\" = "
                       "\"$(docker image inspect openroad/orfs:asap7lock --format '{{.Id}}')\" ]\n"
                       f"python3 tools/qwen_slab_m3_takeover.py route --variant {variant} --out {{RUN}}/routes/{{LABEL}} "
                       "--name {LABEL} --threads 16", threads=16, peak_ram_gb=24, needs=["orfs", "yosys"]),
            collect=dict(cmd="mkdir -p {RUN}/record\ncp {RUN}/routes/{LABEL}/*.json {RUN}/record/\n"
                             "cp {RUN}/bench_positive/result.json {RUN}/record/bench_positive.json\n"
                             "cp {RUN}/bench_negative/result.json {RUN}/record/bench_negative.json")),
        verdict=dict(corner_sta="{RUN}/routes/{LABEL}/corner_sta.json",
                     drc_metrics="{RUN}/routes/{LABEL}/work/orfs/logs/asap7/*/base/5_2_route.json",
                     checks=[dict(name="ttb_routed_at_TC", cmd="test -s {CL}/ttb_corner.txt && ! grep -qv '^TC ' {CL}/ttb_corner.txt")],
                     post_sdc=["physical/qwen_slab_structural/signoff833_die.sdc", "physical/common_flow/link_budget_consistent.sdc"],
                     macros=["physical/asap7_memory_macros/ot_rom_4096x266_m8"]),
        hold_eco=dict(enabled=False, reason="as slab_s14o"),
        budget=dict(enabled=False, reason="as slab_s14o"),
        record=[{"from": "{RUN}/record", "to": f"{REC}/routes/{name}"}],
        cycles_added=0, merge_target=None, route_hold_corners="mm", route_hold_margin_ns=0.05, route_corner="TC",
        notes="BANDF: 0 cycles (per-split constants selected at D1); routed slot GID 40 (band 5 slot 0). Vt: RVT.")
    return name, spec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--commit", required=True)
    ap.add_argument("--out", type=Path, default=Path("/tmp/claude-review-20261003/closure_jobs"))
    a = ap.parse_args()
    c = a.commit
    jobs = [
        tree_top_job("qfd_sp_tree_top_b", c, "r21m qfd_sp_tree_top_b: tree top LANDED + BAND (ot_qfd_band_upper: levels 11/12 "
                     "over the 6 band words, 64 FP32 adders LAT 7; control element RX 5 + 2 LNK, BANDF); 777.6 x 3732.48 PD 0.55",
                     spine_benches() + regressions()),
        tree_top_job("qfd_sp_tree_top_b_t", c, "r21m qfd_sp_tree_top_b AGGRESSIVE variant: 777.6 x 4354.56 PD 0.45",
                     spine_benches(full=False)),
        slab_job("s14o_bf", c, "qwen-band-integrate: r21m slab result-port group in the band-local frame (BANDF 1, slot GID 40): "
                 "rows / scale address / result address / in-range mask by g(split, slot); s14o element (MUL_LAT 7, OREG). "
                 "Route at 770 ps, ORFS CORNER=TC, MM FF hold HM 50, H1, CTS fix hooks + consistent link budget."),
        slab_job("s14ok_bf", c, "qwen-band-integrate: as slab_s14o_bf with MUL_KCP 4 (s14ok element)."),
    ]
    a.out.mkdir(parents=True, exist_ok=True)
    for name, spec in jobs:
        spec["owner"] = OWNER
        spec["source"] = dict(branch=BRANCH, commit=c)
        (a.out / f"{name}.json").write_text(json.dumps(spec, indent=1) + "\n")
        print(a.out / f"{name}.json")


if __name__ == "__main__":
    main()
