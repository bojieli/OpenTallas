#!/usr/bin/env python3
"""QC-S28-BIND guarded clock_merge inject (DIE-QC-100 approved 11-12, EDGE-CLOCK-LATE / QC-COLL-HOLD).
bind.py reads clock_merge from self.ab, and with --asbuilt MANIFEST that is the manifest: load_plan replaces the
plan's own `asbuilt` section, so a plan-side clock_merge would be dropped silently.  This script carries it across.
The key {partition: {manifest SOURCE domain: target domain}} (bind.py looks up s[1], e.g. 'coll' / 'serdes', whose
partition port is clk_coll / clk_serdes) comes from, in order:
  $CM_FILE (opentallas.qc_clock_merge.v1: {"clock_merge": ..., "manifest_sha256": ...}; bind_fix.sh sets it to the
  sibling <input plan stem>.clock_merge.json), else the sibling of PLAN, else plan.asbuilt.clock_merge.
  has PLAN                                print True/False
  inject PLAN MANIFEST OUT_MANIFEST REF   fail closed (exit 3): partition not in the plan; bad pair; manifest sha differs
      from the file's manifest_sha256; a source domain that is not a clock input (clk_<src>) of the partition's module
      in REF (a no-merge bind: a wrong name merges nothing, silently); OUT_MANIFEST not beside MANIFEST (map_file
      resolves relative to the manifest folder); a different clock_merge already in the manifest.
  check PLAN BIND_OUT REF                 after the bind, fail closed (exit 4) unless, for every merged partition:
      bound module clock-domain set (clk -> default, clk_<d> -> d; taps clk_t<i> / clk_c<i> excluded)
        == REF set - merged sources | targets      (coll_s/coll_n -> {core}; coll_ucie -> {core, coll_blk})
      and, when BIND_OUT/kit_rtl/<type>/kit_rtl.json exists, its bound_only_pins carry no clk_<source>.
"""
import hashlib
import json
import os
import re
import sys
from pathlib import Path

TAP = re.compile(r"^clk_[tc]\d+$")


def die(rc, msg):
    print("CM FAIL", msg)
    sys.exit(rc)


def load(pl):
    """(clock_merge or None, source description, manifest_sha256 or None)"""
    cands = [os.environ.get("CM_FILE") or "", re.sub(r"\.json$", ".clock_merge.json", pl)]
    for c in cands:
        if c and Path(c).exists():
            d = json.loads(Path(c).read_text())
            return d.get("clock_merge"), c, d.get("manifest_sha256")
    plan = json.loads(Path(pl).read_text())
    ab = plan.get("asbuilt") or {}
    return (ab.get("clock_merge") if isinstance(ab, dict) else None), "plan.asbuilt.clock_merge", None


def clock_ports(o, tn):
    """(file, {clock input ports}) of type tn's bound module in bind dir o, or (None, None)"""
    for c in (Path(o) / "rtl" / f"{tn}.sv", Path(o) / "rtl" / f"qfd_qc_{tn}_part.sv"):
        if c.exists():
            txt = re.sub(r"//[^\n]*|/\*.*?\*/", "", c.read_text(), flags=re.S)   # comments hold ");" too
            mm = re.search(r"\bmodule\s+\w+\s*(?:#\s*\(.*?\)\s*)?\((.*?)\);", txt, re.S)
            return c, (set(re.findall(r"\binput\s+wire\s+(clk\w*)", mm.group(1))) if mm else None)
    return None, None


def doms(ports, default):
    return {default if p == "clk" else p[4:] for p in ports if not TAP.match(p)}


def parts_of(pl):
    return {p["name"]: p["type"] for p in json.loads(Path(pl).read_text())["partitions"]}


def inject(pl, man, out, ref):
    cm, src, msha = load(pl)
    if not cm:
        print("CM none")
        return
    parts = parts_of(pl)
    for p, m in cm.items():
        if p not in parts:
            die(3, f"clock_merge partition {p} is not a plan partition")
        if not isinstance(m, dict) or not m:
            die(3, f"clock_merge.{p} must be a non-empty {{domain: domain}}")
        for s, t in m.items():
            if not isinstance(s, str) or not isinstance(t, str) or s == t:
                die(3, f"clock_merge.{p}: bad pair {s!r} -> {t!r}")
    have = hashlib.sha256(Path(man).read_bytes()).hexdigest()
    if msha and msha != have:
        die(3, f"{src} was made for manifest {msha[:12]}, the bind manifest is {have[:12]}")
    for p, m in cm.items():                         # a wrong domain name merges nothing, silently: refuse it
        f, ports = clock_ports(ref, parts[p])
        if ports is None:
            die(3, f"reference bind {ref} has no bound module for {p} ({parts[p]})")
        for s in m:
            if f"clk_{s}" not in ports:
                die(3, f"clock_merge.{p}: source domain {s} has no clock input clk_{s} on {f.name} in the no-merge "
                       f"reference bind ({sorted(ports)})")
    if Path(out).resolve().parent != Path(man).resolve().parent:
        die(3, "OUT_MANIFEST must sit beside MANIFEST")
    ab = json.loads(Path(man).read_text())
    if ab.get("clock_merge") not in (None, cm):
        die(3, "manifest already has a different clock_merge")
    ab["clock_merge"] = cm
    Path(out).write_text(json.dumps(ab, indent=1) + "\n")
    print("CM inject from", src, cm)


def check(pl, o, ref):
    cm, src, _ = load(pl)
    if not cm:
        print("CM_CHECK none")
        return
    parts = parts_of(pl)
    bad, ok = [], []
    for p, m in sorted(cm.items()):
        tn = parts[p]
        f, ports = clock_ports(o, tn)
        fr, rports = clock_ports(ref, tn)
        if ports is None or rports is None:
            bad.append(f"{p}: no bound module header for type {tn} (bind {ports is not None}, ref {rports is not None})")
            continue
        default = "core" if "core" in m.values() else next(iter(m.values()))
        got = doms(ports, default)
        want = (doms(rports, default) - set(m)) | set(m.values())
        if got != want:
            bad.append(f"{p}: {f.name} clock domains {sorted(got)} != expected {sorted(want)}")
        kj = Path(o) / "kit_rtl" / tn / "kit_rtl.json"
        if kj.exists():
            bo = json.loads(kj.read_text()).get("bound_only_pins") or []
            names = {x.get("port") if isinstance(x, dict) else str(x) for x in bo}
            left = sorted(n for n in names if any(n == f"clk_{s}" for s in m))
            if left:
                bad.append(f"{p}: kit_rtl bound_only_pins still carry {left}")
            ok.append(f"{p}: domains {sorted(got)}; kit_rtl bound_only clean")
        else:
            ok.append(f"{p}: domains {sorted(got)} (no kit_rtl.json)")
    if bad:
        die(4, "; ".join(bad))
    print("CM_CHECK ok", ok)


if __name__ == "__main__":
    if sys.argv[1] == "types":
        cm = load(sys.argv[2])[0] or {}
        print(" ".join(sorted({parts_of(sys.argv[2])[p] for p in cm})))
    elif sys.argv[1] == "has":
        print(bool(load(sys.argv[2])[0]))
    elif sys.argv[1] == "inject":
        inject(*sys.argv[2:6])
    elif sys.argv[1] == "check":
        check(*sys.argv[2:5])
    else:
        die(2, "usage: has PLAN | inject PLAN MANIFEST OUT REF | check PLAN BIND_OUT REF")
