#!/usr/bin/env python3
"""KV-CORES 10-24: publish the clock insertion of every KV hard core with a routed DB, for lane CLOCK (BRIEFING decision
5(e): hard-core internal latency is compensated at the core clock pin = core-latency contract).

    publish_core_latency.py [--out ../core_latency.json] [MODULE ...]      (default: every results/<module>.json)

Per core, from the collected record (results/<module>.json + results/<module>.signoff.json, both written from the
ROUTED DB by tools/die_plan/signoff.py and collect_core.py) and the published views (physical/ref_tile/<module>/views/):
  clock_pins.<pin>: xy_um (core-local, R0, LEF pin shape centre), face, and the ETM liberty clock-tree arcs per corner
     (max/min_clock_tree_path rise/fall = what tools/die_plan/cores.clock_pins() / early_core_taps.py read);
  measured.<tt|ff>: clock-pin -> register clock-pin arrival over ALL registers and over the PIN FLOPS (min / mean / max /
     spread, propagated clock on the routed RCX SPEF);
  early_tap: TT max_clock_tree_path rise vs the plan common latency (250 ps): > 250 means the parent needs an early core
     tap (pair.add_core_taps / early_core_taps.py), the parent tap is then (250 - core insertion) ps earlier.
The verdict and views_status are carried: abstract_only views are placement abstracts, NOT timing sign-off.
"""
import argparse
import datetime
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
sys.path.insert(0, str(REPO / "tools" / "die_plan"))
from cores import lib_clocks  # noqa: E402
import re  # noqa: E402


def lef_pin_xy(path, names):
    """{pin name: (x, y)} centre of the first PORT RECT of each named pin (bit-exact names, e.g. ck or clk[0])."""
    out, cur, layer = {}, None, None
    for line in open(path, errors="replace"):
        s = line.strip()
        m = re.match(r"^PIN\s+(\S+)", s)
        if m:
            cur = m.group(1).replace("\\", "") if m.group(1).replace("\\", "") in names else None
            continue
        if cur and s.startswith("LAYER"):
            layer = s.split()[1]
        m = re.match(r"^RECT\s+([-0-9.]+)\s+([-0-9.]+)\s+([-0-9.]+)\s+([-0-9.]+)", s)
        if cur and m and cur not in out:
            x0, y0, x1, y1 = map(float, m.groups())
            out[cur] = ((x0 + x1) / 2, (y0 + y1) / 2, layer)
    return out

COMMON_PS = 250.0


def face(xy, w, h):
    x, y = xy
    d = dict(W=x, E=w - x, S=y, N=h - y)
    return min(d, key=d.get)


def one(mod):
    rec = json.loads((HERE / "results" / f"{mod}.json").read_text())
    sop = HERE / "results" / f"{mod}.signoff.json"
    so = json.loads(sop.read_text()) if sop.is_file() else {}
    vd = REPO / rec["views"] if rec.get("views") else REPO / "physical/ref_tile" / mod / "views" / mod
    lef, libs = vd / f"{mod}.lef", {c: vd / f"{mod}_{c}.lib" for c in ("tt", "ff")}
    w, h = rec["outline_um"]
    arcs = {c: (lib_clocks(p) if p.is_file() else {}) for c, p in libs.items()}
    names = sorted(set(arcs["tt"]) | set(arcs["ff"]))
    pins = lef_pin_xy(lef, set(names)) if lef.is_file() else {}
    ck = {}
    for n in names:
        xy = pins.get(n)
        ck[n] = dict(xy_um=[round(xy[0], 3), round(xy[1], 3)] if xy else None, layer=xy[2] if xy else None,
                     face=face(xy[:2], w, h) if xy else None,
                     **{c: {k: round(v, 2) for k, v in (arcs[c].get(n) or {}).items()} for c in ("tt", "ff")})
    used = {n: v for n, v in ck.items() if (v["tt"].get("rise") or 0) > 0}
    meas = {}
    for c in ("tt", "ff"):
        x = (so.get("corners") or {}).get(c) or {}
        meas[c] = dict(pinflops=x.get("insertion_pinflops"), all_registers=x.get("insertion_all"))
    worst = max((v["tt"].get("rise") or 0 for v in used.values()), default=0.0)
    return dict(module=mod, verdict=rec.get("verdict"), views_status=rec.get("views_status"), run=rec.get("run"),
                kit_hash=rec.get("kit_hash"), outline_um=rec["outline_um"], views=str(vd.relative_to(REPO)),
                lef=str(lef.relative_to(REPO)), lib_tt=str(libs["tt"].relative_to(REPO)),
                lib_ff=str(libs["ff"].relative_to(REPO)), clock_pins=used,
                unused_clock_pins=sorted(set(ck) - set(used)), measured=meas,
                contract=(so.get("core_latency") or {}).get("contract", {}).get("kind"),
                signoff_generated=so.get("generated"), signoff_tool_commit=so.get("tool_commit"),
                early_tap=dict(tt_max_clock_tree_rise_ps=round(worst, 2), common_latency_ps=COMMON_PS,
                               needs_early_tap=worst > COMMON_PS,
                               parent_tap_earlier_by_ps=round(max(0.0, worst - COMMON_PS), 2)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(HERE.parent / "core_latency.json"))
    ap.add_argument("modules", nargs="*")
    a = ap.parse_args()
    mods = a.modules or sorted(p.stem for p in (HERE / "results").glob("*.json")
                               if p.stem.count(".") == 0)
    out = dict(schema="opentallas.kv.core_latency.v1", generated=datetime.datetime.now().astimezone()
               .isoformat(timespec="seconds"), producer="physical/die_plan/qwen_kvsys/cores/harden/publish_core_latency.py",
               rule="BRIEFING decision 5(e) core-latency contract: the parent compensates the core insertion at the core "
                    "clock pin (early core tap); the 250 +- 40 plan target applies at the partition tap",
               cores={m: one(m) for m in mods})
    Path(a.out).write_text(json.dumps(out, indent=1) + "\n")
    for m, c in out["cores"].items():
        ms = c["measured"]
        print(f"{m}: {c['verdict'][:11]} pins {list(c['clock_pins'])} TT lib rise {c['early_tap']['tt_max_clock_tree_rise_ps']}"
              f" pinflops TT {(ms['tt']['pinflops'] or {}).get('mean')} FF {(ms['ff']['pinflops'] or {}).get('mean')}")


if __name__ == "__main__":
    main()
