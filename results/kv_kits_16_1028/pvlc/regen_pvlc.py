#!/usr/bin/env python3
"""KV-KITS-16 (2026-10-28) pvlc: regenerate the kv3_pv_pair kits (R0 + fMX) for the DIE-KV-19 LC bank leaf.

COORD priority (22:1x): "regenerate kv3_pv_pair from the LC pin files that DIE-KV-20 posted in KV-CORES.md"
(claude/die-kv-20-1028@b555bf16af results/die_kv_19_1028/cores/kv3_pv_pair_pins{,_fMX}_r26c_lc.json).

Base = the KV-KITS-15 kits (kv-kits-15-1028/kits_pv, claude/kv-kits-15-pv-1028@1017ea9142: QK-CORES-11 plan tree +
DIE-KV-14b SRAM macro leaves + --cts-setup-only). The original generator inputs are gone (core json paths point at
deleted kv-g3 / kv-cores-r2 trees), so this is the regen_pv.sh form: carried kit + ONLY these deltas:
  (1) leaf: u_s0/u_s1 ot_qwen_tp8_pv_slice_t -> ot_qwen_tp8_pv_slice_lc_t #(.G(4)) (main
      rtl/hdc/nearhbm/ot_qwen_tp8_pv_slice_lc_gen.sv, RM230), new input ports s0__bcx[5:0] / s1__bcx[5:0] -> .bcx
      (DIE-KV-19: the die drives bcx from the same command bits as bc[17]/bc[18]; LEC slice_lc_t == slice_t with that
      tie: results/die_kv_14_1028/pv_pair/lec_result.txt);
  (2) pins: io.tcl / pins.json / pins_added.json rebuilt with the MAIN generator functions (gen_core_kit_kv.io_tcl,
      island_ft_arcs, on-track check) from the LC pin file (r26c face re-spread + 12 bcx pins); island ft arcs asserted
      unchanged; core.json port_decl / pin_class / boundary_role += bcx (class in);
  (3) SDC: bcx joins the regular input port list (IO delay / driving cell, like bc); sdc_lint.json inputs / io_floor
      += bcx; sdc_lint.lint must PASS;
  (4) plan tree: the 12 new pin registers u_sK.cx_r[b] ($_DFF_P_, the c_r naming of the same synth) join the CTS-open
      leaf that already holds u_sK.c_r[17] (same face corner, bcx pins sit next to bc[17]/bc[18]); core_infra
      re-installed from pv_tree_slice.json with main core_infra.install. PREDICTED names: the run's synth netlist must
      be checked against the plan sinks before place reaches PRE_GLOBAL_PLACE (core_infra fails closed otherwise);
  (5) --two-mode-grt (gen_core_kit_kv.timing_modes_stage), main tool copies, signoff bundle, freeze/PROVENANCE.
usage (intel2, CLEAN checkout of this branch): regen_pvlc.py PLAN_DIR OUTDIR
  PLAN_DIR = dir with plan.json (DIE-KV-19 event plan) + cores/kv3_pv_pair_pins{,_fMX}_r26c_lc.json
"""
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO / "physical/die_plan/qwen_kvsys/cores/harden"), str(REPO / "tools/die_plan")]
import gen_core_kit_kv as GK  # noqa: E402
import lec as LEC  # noqa: E402
import core_infra as CI  # noqa: E402
import kit_contract as KC  # noqa: E402
import sdc_lint  # noqa: E402

BASE = Path("/srv/opentallas-scratch2/claude/kv-kits-15-1028/kits_pv")
FORMS = {"kv3_pv_pair__380.16x190.08": "cores/kv3_pv_pair_pins_r26c_lc.json",
         "kv3_pv_pair__380.16x190.08_fMX": "cores/kv3_pv_pair_pins_fMX_r26c_lc.json"}
LC_RTL = "rtl/hdc/nearhbm/ot_qwen_tp8_pv_slice_lc_gen.sv"
EXCL = ["run", "signoff", "views", "lec", "__pycache__", "autopilot_chain_*", "preflight_autopilot_*", "preflight.json",
        "1_synth_odb.v", "synth_odb_v.*", "face_guard*.json", "face_guard*.log", "rtl_lint.json", "rtl_lint.log",
        "rtl_lint.ys", "selrange.*", "dont_use_check.json", "adder_map_dontuse.json", "sdc_lint.log", "lec_run.log",
        "run_place.log", "run_route.log", "run_finish.log", "run_cts.log", "signoff.log", "pin_audit.json",
        "replica_check_odb.json", "ft_interface.json"]
G = 4
NB = 2 * G - 2          # bcx width


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def one(text, old, new):
    if text.count(old) != 1:
        raise SystemExit(f"patch anchor x{text.count(old)}: {old[:60]!r}")
    return text.replace(old, new)


def regen(plan_dir, out, tid, pins_rel):
    base, kd = BASE / tid, out / tid
    if kd.exists():
        shutil.rmtree(kd)
    kd.mkdir(parents=True)
    subprocess.run(["rsync", "-a"] + [f"--exclude={e}" for e in EXCL] + [f"{base}/", f"{kd}/"], check=True)
    for f in ("face_guard.py", "lec.py", "rtl_lint.py", "sdc_lint.py", "straps.py", "vclk_corner.tcl"):
        shutil.copyfile(REPO / "tools/die_plan" / f, kd / f)
    shutil.copyfile(REPO / "physical/die_plan/qwen_kvsys/cores/harden/run_kit_kv.sh", kd / "run_kit_kv.sh")
    cfg = (kd / "config.mk").read_text().splitlines()
    if any("OT_HOLD_MM" in l for l in cfg) or not any("post_cts_setup.tcl" in l for l in cfg):
        raise SystemExit(f"{tid}: base must be cts-setup-only and not yet two-mode")
    fz = json.loads((kd / "freeze.json").read_text())
    w, h = fz["outline_um"]
    mod = fz["module"]

    # (1) RTL leaf swap + bcx ports
    shutil.copyfile(REPO / LC_RTL, kd / "rtl" / Path(LC_RTL).name)
    top = kd / "rtl" / f"{mod}.sv"
    t = top.read_text()
    for s in (0, 1):
        t = one(t, f"    input wire [22:0] s{s}__bc,\n",
                f"    input wire [22:0] s{s}__bc,\n    input wire [{NB - 1}:0] s{s}__bcx,\n")
        t = one(t, f"    ot_qwen_tp8_pv_slice_t #(.RESET_PIN(1)) u_s{s} (\n        .bc(s{s}__bc[22:0]),\n",
                f"    // KV-KITS-16 pvlc (DIE-KV-19 LC leaf): bcx = per-lane-group red_issue/red_capture copy pins\n"
                f"    ot_qwen_tp8_pv_slice_lc_t #(.RESET_PIN(1),.G({G})) u_s{s} (\n        .bc(s{s}__bc[22:0]),\n"
                f"        .bcx(s{s}__bcx[{NB - 1}:0]),\n")
    if "ot_qwen_tp8_pv_slice_t " in t:
        raise SystemExit("slice_t left in top")
    top.write_text(t)
    vi = [i for i, l in enumerate(cfg) if l.startswith("export VERILOG_FILES = ")]
    assert len(vi) == 1
    cfg[vi[0]] += f" /work/rtl/{Path(LC_RTL).name}"

    # core.json: bcx ports
    cj = json.loads((kd / "core.json").read_text())
    pd = {}
    for k, v in cj["port_decl"].items():
        pd[k] = v
        if re.fullmatch(r"s[01]__bc", k):
            pd[k + "x"] = ["input", NB - 1, 0]
    cj["port_decl"] = pd
    for s in (0, 1):
        cj["boundary_role"][f"s{s}__bcx"] = "in"
        for b in range(NB):
            cj["pin_class"][f"s{s}__bcx[{b}]"] = "in"
    cj["pin_bits"] = int(cj["pin_bits"]) + 2 * NB
    cj["classes"]["in"] = int(cj["classes"]["in"]) + 2 * NB
    cj.setdefault("files", []).append(LC_RTL)
    cj["kv_kits_16_pvlc"] = dict(leaf="ot_qwen_tp8_pv_slice_t -> ot_qwen_tp8_pv_slice_lc_t G=4",
                                 ports_added=[f"s{s}__bcx[{NB - 1}:0]" for s in (0, 1)], pins_file=pins_rel,
                                 source="DIE-KV-19 pv_pair_lc_plan.py (claude/die-kv-20-1028@b555bf16af)")
    (kd / "core.json").write_text(json.dumps(cj, indent=1) + "\n")

    # (2) pins from the LC plan pin file, main generator functions
    pf = Path(plan_dir) / pins_rel
    doc = json.loads(pf.read_text())
    ft_arcs, ft_names = GK.island_ft_arcs(doc, w, h)
    old_isl = json.loads((kd / "island_ft.json").read_text())
    if json.dumps(old_isl["arcs"], sort_keys=True) != json.dumps(ft_arcs, sort_keys=True):
        raise SystemExit(f"{tid}: island ft arcs differ from the carried kit")
    ft_pins = [p for p in doc["pins"] if p["name"] in ft_names]
    pins = [p for p in doc["pins"] if p["name"] not in ft_names]
    names = set(cj["pin_class"])
    have = {p["name"] for p in pins}
    if have != names:
        raise SystemExit(f"{tid}: pin file vs core ports: missing {sorted(names - have)[:4]} extra {sorted(have - names)[:4]}")
    off = [q["name"] for q in pins if abs(((q["x"] if q["layer"] in ("M3", "M5", "M7") else q["y"]) - GK.OFFS[q["layer"]])
                                       / GK.PITCH[q["layer"]] - round(((q["x"] if q["layer"] in ("M3", "M5", "M7") else q["y"])
                                                                       - GK.OFFS[q["layer"]]) / GK.PITCH[q["layer"]])) > 0.05]
    if off:
        raise SystemExit(f"{tid}: {len(off)} pins off track {off[:3]}")
    clk_set = {n for n, c in cj["pin_class"].items() if c in ("clk", "clk_unused")}
    io, prow = GK.io_tcl(pins + ft_pins, w, h, tid, clk_set | ft_names)
    bad = [r for r in prow if r["face"] == "interior" and r.get("clock")
           and (min(r["size"]) < GK.CLK_PORT_W_UM - 1e-9 or max(r["size"]) < GK.CLK_PORT_L_UM - 1e-9)]
    if bad:
        raise SystemExit(f"{tid}: interior clock port below 0.048x0.48: {bad[:3]}")
    (kd / "io.tcl").write_text(io)
    (kd / "pins.json").write_text(json.dumps(prow) + "\n")
    pa = json.loads((kd / "pins_added.json").read_text())
    pa.update(plan_pins=len(pins), added=[])
    (kd / "pins_added.json").write_text(json.dumps(pa, indent=1) + "\n")
    old_isl.update(pins_file=pins_rel, pins_sha256=sha(pf))
    (kd / "island_ft.json").write_text(json.dumps(old_isl, indent=1) + "\n")

    # (3) SDC + sdc_lint context
    sdc = (kd / "constraint.sdc").read_text()
    sdc = one(sdc, "{s0__bc s0__clk", "{s0__bc s0__bcx s0__clk")
    sdc = one(sdc, "s1__bc s1__pe2", "s1__bc s1__bcx s1__pe2")
    (kd / "constraint.sdc").write_text(sdc)
    lctx = json.loads((kd / "sdc_lint.json").read_text())
    ins = []
    for p in lctx["inputs"]:
        ins.append(p)
        if re.fullmatch(r"s[01]__bc", p):
            ins.append(p + "x")
            lctx["io_floor_ps"][p + "x"] = lctx["io_floor_ps"][p]
    lctx["inputs"] = ins
    (kd / "sdc_lint.json").write_text(json.dumps(lctx, indent=1) + "\n")
    lerr = sdc_lint.lint(sdc, **lctx)
    if lerr:
        raise SystemExit(f"{tid}: sdc_lint FAIL {lerr[:5]}")

    # (4) plan tree: cx_r pin registers join the c_r[17] leaf of their slice
    sl = json.loads((kd / "pv_tree_slice.json").read_text())
    added = {}
    for s in (0, 1):
        ref = f"u_s{s}.c_r\\[17\\]$_DFF_P_/CLK"
        lf = [l for l in sl["core_tree"]["leaves"] if ref in l["sinks"]]
        if len(lf) != 1:
            raise SystemExit(f"{tid}: {ref} in {len(lf)} leaves")
        new = [f"u_s{s}.cx_r\\[{b}\\]$_DFF_P_/CLK" for b in range(NB)]
        assert not set(new) & set(lf[0]["sinks"])
        lf[0]["sinks"] = lf[0]["sinks"] + new
        if "domain_sinks" in lf[0]:
            lf[0]["domain_sinks"] = len(lf[0]["sinks"])
        added[lf[0]["node"]] = added.get(lf[0]["node"], 0) + len(new)
    sl["plan"] += " | KV-KITS-16 pvlc: + LC pin registers u_sK.cx_r[0..5] on the c_r[17] leaf (PREDICTED synth names)"
    CI.install(kd, sl)
    (kd / "pv_tree_slice.json").write_text(json.dumps(sl, indent=1) + "\n")

    # (5) flow: two-mode GRT, ft interface skeleton, signoff bundle, provenance
    GK._ms().plan_tree_cts(kd, cfg)
    if (kd / "ft_ports.json").is_file():
        import ft_ports as FT
        (kd / "ft_interface.json").write_text(json.dumps(FT.model_skeleton(json.loads((kd / "ft_ports.json").read_text())), indent=1) + "\n")
    (kd / "config.mk").write_text("\n".join(cfg) + "\n")
    tm = GK.timing_modes_stage(kd)
    subprocess.run([sys.executable, "-I", str(REPO / "tools/die_plan/signoff.py"), "bundle", str(kd)], check=True)
    prov = LEC._repo_provenance(REPO)
    plan = Path(plan_dir) / "plan.json"
    fz.update(pins_file=pins_rel, pins_sha256=sha(pf), pins=len(pins), plan_pins=len(pins),
              pins_canon_sha256=KC._canon(doc, [w, h]), plan_sha256=sha(plan) if plan.is_file() else None,
              timing_modes=tm, source_commit=prov.get("commit"),
              regen=dict(lane="KV-KITS-16 pvlc", base_kit=str(base), base_source_commit=fz.get("source_commit"),
                         base_kit_hash=fz.get("kit_hash"),
                         plan_delta="DIE-KV-19 LC leaf + bcx pins (claude/die-kv-20-1028@b555bf16af " + pins_rel + ")",
                         clock_sinks_added=added, clock_sinks_basis="PREDICTED (c_r naming); verify vs run 1_synth",
                         options=["--cts-setup-only (carried)", "--two-mode-grt"],
                         tools_refreshed=["face_guard.py", "lec.py", "rtl_lint.py", "sdc_lint.py", "straps.py",
                                          "vclk_corner.tcl", "run_kit_kv.sh", "signoff bundle", "core_infra install"]))
    fz["kit_hash"] = GK.kit_hash(kd)
    (kd / "freeze.json").write_text(json.dumps(fz, indent=1) + "\n")
    LEC.write_kit_provenance(kd, REPO, provenance=prov)
    print("REGEN", tid, "kit_hash", fz["kit_hash"], "pins", len(pins), "+ft", len(ft_pins), "sinks+", added,
          "src", prov.get("commit"), "modes", tm)


def main():
    plan_dir, out = Path(sys.argv[1]), Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    for tid, rel in FORMS.items():
        regen(plan_dir, out, tid, rel)


if __name__ == "__main__":
    main()
