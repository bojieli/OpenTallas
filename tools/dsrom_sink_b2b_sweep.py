#!/usr/bin/env python3
"""Back-to-back Sinkhorn sweep through the XU (rtl/test/tb_hdc_v41_xu_sink_b2b.sv): 7 unit-clock phases x
gaps 0..14 after the first op's result, for the as-built XU and the v41x XU adapter, with the default-off
acceptance handshake (tools/dsrom_sink_handshake.py) OFF and ON.  OFF must reproduce the MTP ITER deadlock
(every gap 0/1 hangs), ON must pass every case, and the cases that pass in both must take identical cycles.

    python3 tools/dsrom_sink_b2b_sweep.py --out DIR [--verilator verilator]
"""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V41 = ROOT / "rtl/hdc/v41"
BASE = [V41 / n for n in ("ot_hdc_engram_tables_pkg.sv", "ot_hdc_sinkhorn.sv", "ot_hdc_sk_arith.sv",
                          "ot_hdc_sk_recip_rom.sv", "ot_hdc_select.sv", "ot_hdc_engram_hash.sv")]
ADAPT_DEPS = [ROOT / "rtl/hdc/v41x/ot_hdc_v41x_sel_lib.sv", ROOT / "rtl/hdc/v41x/ot_hdc_v41x_egather.sv"]
TB = ROOT / "rtl/test/tb_hdc_v41_xu_sink_b2b.sv"
HE_TB = ROOT / "rtl/test/tb_hdc_v41_hcproj_b2b.sv"
HE_DEPS = [ROOT / p for p in ("rtl/proto/ot_fp32_add_rne_pipe.sv", "rtl/proto/ot_fp32_mul_rne_pipe.sv",
                              "rtl/hdc/ot_hdc_delay.sv", "rtl/hdc/ot_hdc_fp32_mul_pipe.sv", "rtl/hdc/ot_hdc_fpu.sv",
                              "rtl/hdc/ot_hdc_sfu.sv")]
HE_LINE = re.compile(r"gap=(\d+)\s+(ok|BAD) bad_words=(\d+)")


def run_he(verilator, out, on):
    """The hyper-connection projection engine: two ops, gap 0 .. 40 after the first is accepted."""
    import sys
    sys.path.insert(0, str(ROOT / "tools"))
    from dsrom_sink_handshake import select
    sel = select([V41 / "ot_hdc_v41_xu.sv", V41 / "ot_hdc_sinkhorn_mc.sv", V41 / "ot_hdc_v41_hcproj.sv"], enable=on)
    he = [p for p in sel["sources"] if p.name == "ot_hdc_v41_hcproj.sv"]
    tag = f"he_{'on' if on else 'off'}"
    obj = out / f"obj_{tag}"
    b = subprocess.run([verilator, "--binary", "--timing", "-Wno-fatal", "-Wno-lint", "-Wno-style", "-j", "8",
                        "--top-module", "tb_hdc_v41_hcproj_b2b", "-Mdir", str(obj), *sel["defines"],
                        *map(str, HE_DEPS + he), str(HE_TB)], capture_output=True, text=True)
    (out / f"build_{tag}.log").write_text(b.stdout + b.stderr)
    if b.returncode:
        return {"build_returncode": b.returncode}
    r = subprocess.run([str(obj / "Vtb_hdc_v41_hcproj_b2b")], capture_output=True, text=True)
    (out / f"run_{tag}.log").write_text(r.stdout)
    cases = {int(m[1]): (m[2], int(m[3])) for m in HE_LINE.finditer(r.stdout)}
    return {"returncode": r.returncode, "sources": [str(p.relative_to(ROOT)) for p in HE_DEPS + he],
            "defines": sel["defines"], "cases": len(cases), "bad": sorted(g for g, v in cases.items() if v[0] != "ok"),
            "pass_line": "PASS cases=41 fail=0" in r.stdout}
LINE = re.compile(r"phase=(\d+) gap=(\d+) (ok|HANG|MISMATCH) c1=(-?\d+) c2=(-?\d+)")


def sources(adapt, on):
    import sys
    sys.path.insert(0, str(ROOT / "tools"))
    from dsrom_sink_handshake import select
    xu = [V41 / "ot_hdc_v41_xu.sv", V41 / "ot_hdc_sinkhorn_mc.sv"]
    if adapt:
        xu.append(ROOT / "rtl/hdc/v41x/ot_hdc_v41x_xu_adapt.sv")
    sel = select(BASE + xu, enable=on)
    return sel["sources"] + (ADAPT_DEPS if adapt else []), sel["defines"]


def run(verilator, out, adapt, on):
    tag = f"{'adapt' if adapt else 'xu'}_{'on' if on else 'off'}"
    srcs, defines = sources(adapt, on)
    obj = out / f"obj_{tag}"
    cmd = [verilator, "--binary", "--timing", "-Wno-fatal", "-Wno-lint", "-Wno-style", "-j", "8",
           "--top-module", "tb_hdc_v41_xu_sink_b2b", "-Mdir", str(obj), *defines,
           *(["+define+XU_ADAPT", "-y", str(ROOT / 'rtl/hdc/v41x')] if adapt else []), *map(str, srcs), str(TB)]
    b = subprocess.run(cmd, capture_output=True, text=True)
    (out / f"build_{tag}.log").write_text(b.stdout + b.stderr)
    if b.returncode:
        return tag, {"build_returncode": b.returncode}
    r = subprocess.run([str(obj / "Vtb_hdc_v41_xu_sink_b2b")], capture_output=True, text=True)
    (out / f"run_{tag}.log").write_text(r.stdout)
    cases = {(int(m[1]), int(m[2])): (m[3], int(m[4]), int(m[5])) for m in LINE.finditer(r.stdout)}
    return tag, {"returncode": r.returncode, "sources": [str(p.relative_to(ROOT)) for p in srcs], "defines": defines,
                 "cases": len(cases), "hang": sum(v[0] == "HANG" for v in cases.values()),
                 "mismatch": sum(v[0] == "MISMATCH" for v in cases.values()),
                 "hang_gaps": sorted({k[1] for k, v in cases.items() if v[0] == "HANG"}),
                 "_cases": cases}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--verilator", default="verilator")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    res = dict(run(a.verilator, a.out, adapt, on) for adapt in (False, True) for on in (False, True))
    rec = {"bench": str(TB.relative_to(ROOT)), "verilator": subprocess.run([a.verilator, "--version"],
           capture_output=True, text=True).stdout.strip(), "configs": {}}
    for unit in ("xu", "adapt"):
        off, on = res[f"{unit}_off"], res[f"{unit}_on"]
        both = [k for k in on.get("_cases", {}) if off.get("_cases", {}).get(k, ("",))[0] == "ok"
                and on["_cases"][k][0] == "ok"]
        rec["configs"][unit] = {
            "off": {k: v for k, v in off.items() if k != "_cases"},
            "on": {k: v for k, v in on.items() if k != "_cases"},
            "cases_ok_in_both": len(both),
            "cycle_identical_where_both_ok": all(off["_cases"][k] == on["_cases"][k] for k in both),
            "on_back_to_back_c2_cycles": sorted({on["_cases"][k][2] for k in on.get("_cases", {}) if k[1] <= 1})}
        c = rec["configs"][unit]
        c["pass"] = (c["off"].get("hang", 0) > 0 and c["on"].get("cases") == 105 and c["on"]["hang"] == 0
                     and c["on"]["mismatch"] == 0 and c["cycle_identical_where_both_ok"]
                     and c["cases_ok_in_both"] == 105 - c["off"]["hang"])
    he_off, he_on = run_he(a.verilator, a.out, False), run_he(a.verilator, a.out, True)
    rec["configs"]["he"] = {"off": he_off, "on": he_on,
                            "pass": bool(he_off.get("bad")) and he_on.get("pass_line", False) and he_on["cases"] == 41}
    rec["pass"] = all(c["pass"] for c in rec["configs"].values())
    files = {TB, HE_TB, *HE_DEPS, V41 / "ot_hdc_v41_hcproj.sv", *BASE, *ADAPT_DEPS, V41 / "ot_hdc_v41_xu.sv", V41 / "ot_hdc_sinkhorn_mc.sv",
             ROOT / "rtl/hdc/v41x/ot_hdc_v41x_xu_adapt.sv", *(V41 / "dspark_sink_handshake").glob("*.sv"),
             ROOT / "tools/dsrom_sink_handshake.py", Path(__file__).resolve()}
    rec["input_sha256"] = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)}
    (a.out / "result.json").write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps({u: {k: c.get(k) for k in ("pass", "cases_ok_in_both", "cycle_identical_where_both_ok")}
                      for u, c in rec["configs"].items()}))
    return 0 if rec["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
