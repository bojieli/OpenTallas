#!/usr/bin/env python3
"""Sequential gate-level LEC of one kit: kit RTL (config.mk VERILOG_FILES / VERILOG_DEFINES) vs its ORFS netlist (default
run/results/asap7/<DESIGN>/base/1_2_yosys.v) with ASAP7 RVT TT liberty functional models, one AIG miter, ABC dprove.
(KV-PV-CAP 11-24: the pv_v3 probe-kit gate LEC; a whole-design miter from a matched zero start, not lec.py's key points.)

    python3 tools/die_plan/kit_seq_lec.py KIT --out DIR [--netlist NET.v] [--rtl-dir DIR] [--image IMG] [--dry-run]
    -> exit 0 PROVED, 1 CEX, 2 NO_VERDICT, 3 tool error;  DIR/lec.ys, lec.log, abc.log, verdict.json

Both sides: ot_dp_lk := wire (kit_dly_lockup's LEC view); every cell that is not a yosys primitive after flatten (SRAM macros,
hard cores, landing macros) is cut by name with expose -evert, and the cut lists must be equal.  Flops start at zero; on the
gate side the liberty QN state wire (IQN) starts at 1 so that Q = 0 matches the RTL.  DFFASRHQNx1 is read from
lec_asap7_dffasrhqn.v AFTER the liberty files: yosys 0.67 read_liberty imports it with the set always active (SETN = 1), which
holds every async-reset synchroniser in reset and makes the miter fail (or hide differences behind a stuck reset).
The verdict is PROVED only on ABC's own "Networks are equivalent"."""
import argparse, json, os, re, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ASRH = HERE / "lec_asap7_dffasrhqn.v"
NLDM = "/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM"
STD = ("SEQ", "INVBUF", "SIMPLE", "AO", "OA")
IMAGE = "opentallas/orfs:asap7lock-grtT3"
LK_RE = re.compile(r"^module (\\\$paramod\\ot_dp_lk\\W=s32'([01]+)) \(clk, d, q\);", re.M)
LK_GOLD = ("module ot_dp_lk #(parameter integer W = 1) (input wire clk, input wire [W-1:0] d, output wire [W-1:0] q);\n"
           "    assign q = d;\nendmodule\n")


def config(kit):
    """config.mk export lines -> {KEY: value} (continuation lines joined)"""
    txt = (Path(kit) / "config.mk").read_text().replace("\\\n", " ")
    return {m[1]: m[2].strip() for m in re.finditer(r"^export\s+(\w+)\s*[?:]?=\s*(.*)$", txt, re.M)}


def lk_gate(netlist_text):
    """gate-side wire view of every kept $paramod ot_dp_lk module in the netlist"""
    out = []
    for m in LK_RE.finditer(netlist_text):
        w = int(m[2], 2)
        out.append(f"module {m[1]} (clk, d, q);\n  input clk;\n  input [{w - 1}:0] d;\n  output [{w - 1}:0] q;\n  assign q = d;\nendmodule\n")
    return "".join(out)


def script(kit, cfg, netlist, out, rtl_dir=None, libdir=None):
    """-> lec.ys text"""
    kit, out = Path(kit), Path(out)
    rtl_dir = Path(rtl_dir) if rtl_dir else kit
    top = cfg["DESIGN_NAME"]
    fix = lambda p: str(rtl_dir / p[len("/work/"):]) if p.startswith("/work/") else p
    vf = [fix(p) for p in cfg.get("VERILOG_FILES", "").split()]
    src, bbs = [p for p in vf if not p.endswith("_bb.v")], [p for p in vf if p.endswith("_bb.v")]
    libs = [fix(p) for p in cfg.get("ADDITIONAL_LIBS", "").split()]
    defs = " ".join(d for d in cfg.get("VERILOG_DEFINES", "").split() if d.startswith("-D"))
    libdir = libdir or str(out / "asap7")

    def bb():
        return [f"read_verilog -sv -lib {b}" for b in bbs] + [f"read_liberty -lib -ignore_redef {l}" for l in libs]

    def prep(side):
        s = [f"hierarchy -check -top {top}", "proc", "setattr -mod -unset keep_hierarchy *", "flatten"]
        if side == "gate":
            s.append("setattr -set init 1'1 w:*.IQN")
        return s + ["memory", "opt_clean", f"tee -o {out}/lat_{side}.txt select -list t:$dlatch t:$_DLATCH*",
                    "select -set bb c:* t:$* %d", f"tee -o {out}/bb_{side}.txt select -list @bb", "expose -evert @bb",
                    f"rename {top} {side}", f"design -stash {side}"]
    s = [f"read_verilog -sv {defs} -defer " + " ".join(src)] + bb() + [f"read_verilog -overwrite -sv {out}/lk_gold.v"] + prep("gold")
    s += [f"read_liberty -ignore_miss_func -ignore_redef {libdir}/lib_{g}.lib" for g in STD]
    s += [f"read_verilog -overwrite {ASRH}", f"read_verilog {netlist}"] + bb() + [f"read_verilog -overwrite {out}/lk_gate.v"] + prep("gate")
    s += ["design -copy-from gold -as gold gold", "design -copy-from gate -as gate gate", "miter -equiv -flatten gold gate miter",
          "hierarchy -top miter", "async2sync", "setundef -undriven -zero", "opt -fast", "techmap", "setundef -zero", "opt -fast",
          "dfflegalize -cell $_DFF_P_ 01", "stat", "setundef -init -zero", "aigmap", f"write_aiger -zinit {out}/miter.aig"]
    return "\n".join(s) + "\n"


def verdict(abc_log):
    if "Networks are equivalent" in abc_log:
        return "PROVED"
    if re.search(r"NOT EQUIVALENT|was asserted|counter-example|Networks are not equivalent", abc_log, re.I):
        return "CEX"
    return "NO_VERDICT"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("kit"); ap.add_argument("--out", required=True); ap.add_argument("--netlist")
    ap.add_argument("--rtl-dir", help="dir standing for /work (default KIT)"); ap.add_argument("--image", default=IMAGE)
    ap.add_argument("--abc-timeout", type=int, default=14000); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    kit, out = Path(a.kit).resolve(), Path(a.out).resolve(); out.mkdir(parents=True, exist_ok=True)
    cfg = config(kit)
    net = Path(a.netlist).resolve() if a.netlist else kit / f"run/results/asap7/{cfg.get('DESIGN_NICKNAME', cfg['DESIGN_NAME'])}/base/1_2_yosys.v"
    (out / "lk_gold.v").write_text(LK_GOLD)
    (out / "lk_gate.v").write_text(lk_gate(net.read_text()))
    (out / "lec.ys").write_text(script(kit, cfg, net, out, a.rtl_dir))
    if a.dry_run:
        print(f"KIT_SEQ_LEC DRY {out}/lec.ys"); return 0
    d = ["docker", "run", "--rm", "-u", f"{os.getuid()}:{os.getgid()}", "-v", "/srv:/srv"]
    if not str(kit).startswith("/srv/") or not str(out).startswith("/srv/"):
        d += ["-v", f"{kit}:{kit}", "-v", f"{out}:{out}"]
    d.append(a.image)
    getl = "; ".join(f"zcat -f $(ls {NLDM}/asap7sc7p5t_{g}_RVT_TT_nldm_2*.lib* | head -1) > {out}/asap7/lib_{g}.lib" for g in STD)
    (out / "asap7").mkdir(exist_ok=True)
    r = subprocess.run(d + ["bash", "-c", f"{getl} && yosys -q -l {out}/lec.log {out}/lec.ys"], capture_output=True, text=True)
    if r.returncode or not (out / "miter.aig").stat().st_size:
        print("KIT_SEQ_LEC TOOL_ERROR", (r.stderr or "")[-400:]); return 3
    cut = {s: sorted(l.split("/")[-1] for l in (out / f"bb_{s}.txt").read_text().split()) for s in ("gold", "gate")}
    if cut["gold"] != cut["gate"]:
        print("KIT_SEQ_LEC TOOL_ERROR cut lists differ", sorted(set(cut["gold"]) ^ set(cut["gate"]))[:8]); return 3
    r = subprocess.run(d + ["bash", "-c", f"timeout {a.abc_timeout} yosys-abc -c 'read {out}/miter.aig; print_stats; dprove -v'"],
                       capture_output=True, text=True)
    (out / "abc.log").write_text(r.stdout + r.stderr)
    v = verdict(r.stdout + r.stderr)
    (out / "verdict.json").write_text(json.dumps({"verdict": v, "kit": str(kit), "netlist": str(net), "cut": len(cut["gold"])}, indent=1))
    print("KIT_SEQ_LEC", v, out)
    return {"PROVED": 0, "CEX": 1}.get(v, 2)


if __name__ == "__main__":
    sys.exit(main())
