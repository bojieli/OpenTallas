#!/usr/bin/env python3
"""QC-A0 10-24: A0 v8 core clock-tap integration check (GEOM-REVIEW cond. 'tap/plan integration').

    check_a0c8_taps.py [--plan die_plan.json] [--out report.json]

For NK / NL compares, by tap name and xy (um, core frame):
  (1) inputs/a0_core_taps.json variants[k].taps          (the plan-side declaration, v8)
  (2) tools/qwen_romleaf/a0core/a0c8_<k>_taps.json        (the generator output the kit was made from)
  (3) tools/qwen_romleaf/a0core/qfd_tile_<k>_a0c8_pins.tcl (the kit's placed M7 tap pins)
  (4) RTL ports of qfd_tile_<k>_a0c under the kit's VERILOG_DEFINES (load-less ck_t<i> inputs)
and, with --plan, (5) the 'kind: core' taps the plan die_plan.json declares for every A0 hard core (core frame,
MY un-mirrored), which must equal (1) -- else the plan was generated from an older a0_core_taps.json.
"""
import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TOL = 0.01


def rtl_ports(k, defines):
    src = (ROOT / f"rtl/physical/a0_core/qfd_tile_{k}_a0c.sv").read_text().splitlines()
    stack, ports = [], set()
    for l in src:
        m = re.match(r"\s*`(ifdef|ifndef|else|endif)\s*(\w*)", l)
        if m:
            d, n = m.groups()
            if d == "ifdef":
                stack.append(n in defines)
            elif d == "ifndef":
                stack.append(n not in defines)
            elif d == "else":
                stack[-1] = not stack[-1]
            else:
                stack.pop()
            continue
        if all(stack):
            for p in re.findall(r"\binput\s+wire\s+(ck(?:_t\d+)?)\b", l):
                ports.add(p)
    return ports


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan"); ap.add_argument("--out")
    a = ap.parse_args()
    core = json.loads((ROOT / "physical/die_plan/qwen_compute/inputs/a0_core_taps.json").read_text())
    rep = dict(ok=True, variants={})
    plan = json.loads(Path(a.plan).read_text()) if a.plan else None
    for k in ("nk", "nl"):
        r = {}
        decl = {t["name"]: tuple(t["xy"]) for t in core["variants"][k]["taps"]}
        gen = {t["name"]: tuple(t["xy"]) for t in json.loads((ROOT / f"tools/qwen_romleaf/a0core/a0c8_{k}_taps.json").read_text())["taps"]}
        pins, layers = {}, set()
        for l in (ROOT / f"tools/qwen_romleaf/a0core/qfd_tile_{k}_a0c8_pins.tcl").read_text().splitlines():
            m = re.match(r"place_pin -pin_name \{(ck(?:_t\d+)?)\} -layer (\S+) -location \{([\d.]+) ([\d.]+)\}", l)
            if m:
                pins[m.group(1)] = (float(m.group(3)), float(m.group(4)))
                layers.add(m.group(2))
        env = (ROOT / f"physical/ref_tile/qfd_tile_{k}_a0cv8/kit.env").read_text()
        defs = set(re.findall(r"-D(\w+)", re.search(r"VERILOG_DEFINES=([^']*)'", env).group(1)))
        ports = rtl_ports(k, defs)

        def cmp(x, y):
            miss = sorted(set(x) - set(y)); extra = sorted(set(y) - set(x))
            moved = sorted(n for n in set(x) & set(y) if max(abs(x[n][0] - y[n][0]), abs(x[n][1] - y[n][1])) > TOL)
            return dict(missing=miss, extra=extra, moved=moved, ok=not (miss or extra or moved))

        r["n_decl"] = len(decl)
        r["decl_vs_gen"] = cmp(decl, gen)
        r["decl_vs_kit_pins"] = cmp(decl, pins)
        r["kit_pin_layers"] = sorted(layers)
        r["decl_vs_rtl_ports"] = dict(missing=sorted(set(decl) - ports), extra=sorted(ports - set(decl)),
                                      ok=set(decl) == ports, defines=sorted(d for d in defs if d.startswith("OT_A0_CK")))
        oks = [r["decl_vs_gen"]["ok"], r["decl_vs_kit_pins"]["ok"], r["decl_vs_rtl_ports"]["ok"]]
        if plan is not None:
            pr = []
            pts = plan["partition_types"]
            for tn, t in (pts.items() if isinstance(pts, dict) else ((t.get("name", "?"), t) for t in pts)):
                for hc in t.get("hard_cores", []):
                    mod = hc.get("module", "")
                    if not mod.startswith(f"qfd_tile_{k}_a0c"):
                        continue
                    cw, _ = hc["outline_um"]; ox, oy = hc["origin_um"]; dx, dy = hc.get("track_offset_um", [0.0, 0.0])
                    have = {}
                    for tp in t["clock"].get("taps", []):
                        if tp.get("kind") == "core" and tp["name"].startswith(hc["inst"] + "."):
                            x = tp["xy"][0] - ox - dx
                            x = cw - x if hc.get("orient") == "MY" else x
                            have[tp["name"].split(".", 1)[1]] = (round(x, 3), round(tp["xy"][1] - oy - dy, 3))
                    c = cmp(decl, have)
                    pr.append(dict(type=tn, inst=hc["inst"], n=len(have), **c))
            r["plan"] = dict(cores=len(pr), cores_mismatched=sum(1 for p in pr if not p["ok"]),
                             ok=all(p["ok"] for p in pr) and bool(pr),
                             first_mismatch=next((p for p in pr if not p["ok"]), None))
            oks.append(r["plan"]["ok"])
        r["ok"] = all(oks)
        rep["ok"] &= r["ok"]
        rep["variants"][k] = r
    txt = json.dumps(rep, indent=1)
    if a.out:
        Path(a.out).write_text(txt + "\n")
    print(txt)


if __name__ == "__main__":
    main()
