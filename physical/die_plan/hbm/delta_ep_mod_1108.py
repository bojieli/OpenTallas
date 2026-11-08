"""HBM plan event EP-MOD-1108 (DIE-HBM-92-EP, class EP HARD-CORE MODULE MISMATCH).

The as-built native top binds NW_io's two endpoints as two successor modules (HBM-BIND 10-24, OWNER "host in-band":
host control frames ride the N0 die link as virtual channel 1):

    ep_N0   = hfd_ep_static_vc2 #(.IDLE_K(204), .HQ(4))   (= its parameter defaults)
    host_ep = hfd_ep_host_vc

The plan declared both as hfd_ep_static with the hfd_ep_static pin table, so the kit placed macros of a module the
bound netlist does not have (KIT_PREFLIGHT macro_instances: u_ep_N0 / u_host_ep unresolvable).  hfd_ep_static cannot
stand in for them (different ports and function: vc2 adds the 612-b VC1 frame face h_*, host_vc has no SerDes face and
adds the vc_* face), so the plan declares the bound modules:

* partition_types.NW_io contents[] + hard_cores[] u_ep_N0 / u_host_ep: module -> the as-built module; hard_cores get
  port-exact pin tables on the SAME outline, origin and obs_max.  Every pin shared with hfd_ep_static keeps its site
  (vc2: all 2288; host_vc: all but the removed sd_* face).  The new VC1 face is placed pair-aligned across the gap:
  ep_N0 h_* on its N face, host_ep vc_* on its S face at the same die x (M5, 0.192 um steps on the pin lattice,
  4.584 um corner inset), so each pair is one straight vertical route.
* clock.taps budget_owner of those two taps, clock_entries.json NW_io.<inst>.module: the new module (entry kept).
* core_macros.json / core_clock_regions.json: entries for the two modules copied from hfd_ep_static (same
  ot_hep_rx_pingpong u_rxb store, same SRAM paths, same outline); hfd_ep_static instance count 6 -> 4.

Nothing else changes: other types, geometry, buses, stations, cycles.  Ports are read from the module RTL headers and
checked (fail closed) against the hfd_ep_static table.  The children have no signed view; the parent builds on
PROVISIONAL contract views (KW-PROV-1) exactly as it did for hfd_ep_static.
"""
import argparse
import copy
import gzip
import hashlib
import json
import os
import re
import shutil
import sys
from pathlib import Path

EVENT = "EP-MOD-1108"
TYPE = "NW_io"
BASE = "hfd_ep_static"
SWAP = {"u_ep_N0": "hfd_ep_static_vc2", "u_host_ep": "hfd_ep_host_vc"}
TAG = "epmod1108"
# VC1 face pairs (ep_N0 port -> host_ep port), in pin order
PAIRS = [("h_tx_v", "vc_tx_v"), ("h_tx_frame", "vc_tx_frame"), ("h_rx_v", "vc_rx_v"), ("h_rx_frame", "vc_rx_frame"),
         ("h_up", "vc_up"), ("h_cause", "vc_cause")]
STEP, INSET, CLEAR, LAYER = 0.192, 4.584, 0.576, "M5"
NOTE = (f" | {EVENT} (DIE-HBM-92-EP 11-08): module = as-built {{m}} (bound netlist; hfd_ep_static is not this "
        "endpoint), port-exact pin table, outline/origin kept")


def module_ports(text, module):
    """[(dir, name, width)] of `module`'s ANSI header in text."""
    m = re.search(r"\bmodule\s+" + re.escape(module) + r"\b\s*(#\s*\((?:[^()]|\([^()]*\))*\))?\s*\((.*?)\);", text, re.S)
    if not m:
        raise ValueError(f"module {module} not found")
    out = []
    for line in re.sub(r"//[^\n]*", "", m.group(2)).split(","):
        p = re.match(r"\s*(input|output|inout)\s+(?:wire|reg|logic)?\s*(?:\[(\d+):0\])?\s*(\w+)\s*$", line)
        if p:
            out.append((p.group(1), p.group(3), int(p.group(2)) + 1 if p.group(2) else 1))
    if not out:
        raise ValueError(f"module {module}: no ports parsed")
    return out


def bits(name, w):
    return [name] if w == 1 else [f"{name}[{i}]" for i in range(w)]


def _face_sites(n, lo, hi, taken, other_taken, shift):
    """n x positions on the lattice from lo, STEP apart, clear of taken (this face) and of other_taken at x - shift."""
    out, x = [], lo
    while len(out) < n:
        if x > hi:
            raise ValueError(f"VC1 face: only {len(out)} of {n} sites fit")
        y = round(x - shift, 3)
        if all(abs(x - t) >= CLEAR for t in taken) and all(abs(y - t) >= CLEAR for t in other_taken):
            out.append(round(x, 3))
        x = round(x + STEP, 3)
    return out


def pin_tables(base_pins, outline, vc2_ports, host_ports, base_ports, dx):
    """(vc2 table, host_vc table).  dx = host_ep origin x - ep_N0 origin x."""
    W, H = outline
    bp = {n for _, n, _ in base_ports}
    v2 = {n: (d, w) for d, n, w in vc2_ports}
    hv = {n: (d, w) for d, n, w in host_ports}
    bpd = {n: (d, w) for d, n, w in base_ports}
    extra_v2 = [n for n in v2 if n not in bp]
    gone_h = [n for n in bp if n not in hv]
    extra_h = [n for n in hv if n not in bp]
    want_v2, want_h = [a for a, _ in PAIRS], [b for _, b in PAIRS]
    if any(v2[n] != bpd[n] for n in bp if n in v2) or sorted(extra_v2) != sorted(want_v2) or not bp <= set(v2):
        raise ValueError(f"vc2 ports are not hfd_ep_static + {want_v2}: extra {extra_v2}")
    if sorted(gone_h) != ["sd_rx", "sd_st", "sd_tx"] or sorted(extra_h) != sorted(want_h) or \
            any(hv[n] != bpd[n] for n in bp if n in hv):
        raise ValueError(f"host_vc ports are not hfd_ep_static - sd_* + {want_h}: gone {gone_h} extra {extra_h}")
    for a, b in PAIRS:
        if v2[a][1] != hv[b][1] or v2[a][0] == hv[b][0]:
            raise ValueError(f"VC1 pair {a}/{b}: width/direction mismatch {v2[a]} {hv[b]}")
    tbl_names = {p["name"] for p in base_pins}
    if tbl_names != {b for _, n, w in base_ports for b in bits(n, w)}:
        raise ValueError("base pin table does not match the hfd_ep_static ports")
    ytop = round(H - 0.096, 3)
    n_top = [p["x"] for p in base_pins if p["y"] > H - 0.5]
    host_keep = [p for p in base_pins if p["name"].split("[")[0] not in gone_h]
    s_bot = [p["x"] for p in host_keep if p["y"] < 0.5]
    order = [(a, b, v2[a][1]) for a, b in PAIRS]
    n = sum(w for _, _, w in order)
    xs = _face_sites(n, INSET + max(0.0, dx), W - INSET + min(0.0, dx), n_top, s_bot, dx)
    vc2_tbl, host_tbl, k = copy.deepcopy(base_pins), copy.deepcopy(host_keep), 0
    for a, b, w in order:
        for ba, bb in zip(bits(a, w), bits(b, w)):
            vc2_tbl.append(dict(name=ba, layer=LAYER, x=xs[k], y=ytop))
            host_tbl.append(dict(name=bb, layer=LAYER, x=round(xs[k] - dx, 3), y=0.096))
            k += 1
    for tbl, ports in ((vc2_tbl, vc2_ports), (host_tbl, host_ports)):
        names = [p["name"] for p in tbl]
        if sorted(names) != sorted(b for _, nm, w in ports for b in bits(nm, w)) or len(set(names)) != len(names):
            raise ValueError("generated pin table is not port-exact")
        sites = [(p["layer"], round(p["x"], 3), round(p["y"], 3)) for p in tbl]
        if len(set(sites)) != len(sites):
            raise ValueError("generated pin table has coincident pins")
        if any(not (0 <= p["x"] <= W and 0 <= p["y"] <= H) for p in tbl):
            raise ValueError("generated pin outside outline")
    return vc2_tbl, host_tbl


def apply(plan, base_pins, vc2_ports, host_ports, base_ports):
    """-> (new plan, {module: pin table}, changes).  Pure; plan unchanged."""
    out = copy.deepcopy(plan)
    t = out["partition_types"][TYPE]
    hc = {h["inst"]: h for h in t["hard_cores"]}
    ct = {c["inst"]: c for c in t["contents"]}
    for inst in SWAP:
        if hc[inst]["module"] != BASE or ct[inst]["module"] != BASE:
            raise ValueError(f"{TYPE}.{inst}: plan module {hc[inst]['module']} / {ct[inst]['module']} is not {BASE}")
    if hc["u_ep_N0"]["outline_um"] != hc["u_host_ep"]["outline_um"] or \
            hc["u_ep_N0"]["pins_file"] != hc["u_host_ep"]["pins_file"]:
        raise ValueError("u_ep_N0 / u_host_ep do not share one outline + pin table")
    dx = round(hc["u_host_ep"]["origin_um"][0] - hc["u_ep_N0"]["origin_um"][0], 3)
    if not hc["u_host_ep"]["origin_um"][1] > hc["u_ep_N0"]["origin_um"][1] + hc["u_ep_N0"]["outline_um"][1]:
        raise ValueError("host_ep is not north of ep_N0: VC1 face sides would be wrong")
    vc2_tbl, host_tbl = pin_tables(base_pins, hc["u_ep_N0"]["outline_um"], vc2_ports, host_ports, base_ports, dx)
    W, H = hc["u_ep_N0"]["outline_um"]
    tables = {SWAP["u_ep_N0"]: vc2_tbl, SWAP["u_host_ep"]: host_tbl}
    changes = []
    for inst, mod in SWAP.items():
        pf = f"cores/{mod}__{W:g}x{H:g}__{TAG}.json"
        for kind, e in (("hard_cores", hc[inst]), ("contents", ct[inst])):
            before = dict(module=e["module"], pins_file=e.get("pins_file"))
            e["module"] = mod
            if kind == "hard_cores":
                e["pins_file"] = pf
            e["note"] = (e.get("note") or "") + NOTE.format(m=mod)
            changes.append(dict(type=TYPE, kind=kind, inst=inst, before=before,
                                after=dict(module=mod, pins_file=e.get("pins_file"))))
    for tp in (t.get("clock") or {}).get("taps", []):
        inst = str(tp.get("name", "")).split(".")[0]
        if inst in SWAP and tp.get("budget_owner") == BASE:
            tp["budget_owner"] = SWAP[inst]
            changes.append(dict(type=TYPE, kind="clock.taps", tap=tp["name"], budget_owner=[BASE, SWAP[inst]]))
    return out, tables, changes


def side_files(ce, cm, ccr):
    """clock_entries / core_macros / core_clock_regions updated in place copies -> (ce, cm, ccr, changes)."""
    ce, cm, ccr, ch = copy.deepcopy(ce), copy.deepcopy(cm), copy.deepcopy(ccr), []
    for inst, mod in SWAP.items():
        e = ce[TYPE][inst]
        if e.get("module") != BASE:
            raise ValueError(f"clock_entries {TYPE}.{inst} module {e.get('module')} != {BASE}")
        e["module"] = mod
        e["source"] = e.get("source", "") + f" | {EVENT}: module {mod}, entry kept"
        ch.append(dict(file="clock_entries.json", key=f"{TYPE}.{inst}.module", before=BASE, after=mod))
    for mod in SWAP.values():
        if mod in cm["cores"] or mod in ccr["modules"]:
            raise ValueError(f"{mod} already in core_macros / core_clock_regions")
        c = copy.deepcopy(cm["cores"][BASE])
        c["basis"] = (f"{EVENT}: copied from {BASE} (same ot_hep_rx_pingpong u_rxb store, same SRAM paths, same outline "
                      "427.68x246.24); " + c.get("basis", ""))
        cm["cores"][mod] = c
        r = copy.deepcopy(ccr["modules"][BASE])
        r["instances"] = 1
        r["note"] = f"{EVENT}: copied from {BASE} (sinks unmeasured for {mod})"
        ccr["modules"][mod] = r
        ch += [dict(file="core_macros.json", key=f"cores.{mod}", copied_from=BASE),
               dict(file="core_clock_regions.json", key=f"modules.{mod}", copied_from=BASE, instances=1)]
    ccr["modules"][BASE]["instances"] -= len(SWAP)
    ch.append(dict(file="core_clock_regions.json", key=f"modules.{BASE}.instances",
                   after=ccr["modules"][BASE]["instances"]))
    return ce, cm, ccr, ch


def fsha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def _write(path, obj, indent=1):
    path = Path(path)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(obj, indent=indent) + "\n")
    if path.exists() or path.is_symlink():
        path.unlink()                          # never write through a hardlink into the base plan dir
    os.replace(tmp, path)


def _gz(path):
    path = Path(path)
    gz = path.with_name(path.name + ".gz")
    if gz.exists():
        gz.unlink()
        with open(path, "rb") as src, gzip.open(gz, "wb") as dst:
            shutil.copyfileobj(src, dst)


def changed_types(a, b):
    sa, sb = a["partition_types"], b["partition_types"]
    out = sorted(t for t in set(sa) | set(sb) if json.dumps(sa.get(t), sort_keys=True) != json.dumps(sb.get(t), sort_keys=True))
    rest = sorted(k for k in set(a) | set(b) if k != "partition_types" and json.dumps(a.get(k), sort_keys=True) != json.dumps(b.get(k), sort_keys=True))
    return out, rest


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("plan_dir")
    ap.add_argument("--rtl", required=True, help="source holding the hfd_ep_static_vc2 + hfd_ep_host_vc headers")
    ap.add_argument("--base-rtl", required=True, help="source holding the hfd_ep_static header")
    ap.add_argument("--out-dir", required=True, help="new plan dir (hardlink copy of plan_dir + changed files)")
    a = ap.parse_args(argv)
    src, dst = Path(a.plan_dir), Path(a.out_dir)
    if dst.exists():
        raise SystemExit(f"{dst} exists")
    plan = json.loads((src / "die_plan.json").read_text())
    rtl = Path(a.rtl).read_text()
    vc2_ports, host_ports = module_ports(rtl, SWAP["u_ep_N0"]), module_ports(rtl, SWAP["u_host_ep"])
    base_ports = module_ports(Path(a.base_rtl).read_text(), BASE)
    hc0 = next(h for h in plan["partition_types"][TYPE]["hard_cores"] if h["inst"] == "u_ep_N0")
    base_pins = json.loads((src / hc0["pins_file"]).read_text())
    new, tables, changes = apply(plan, base_pins, vc2_ports, host_ports, base_ports)
    ce, cm, ccr, side = side_files(*(json.loads((src / f).read_text())
                                     for f in ("clock_entries.json", "core_macros.json", "core_clock_regions.json")))
    shutil.copytree(src, dst, copy_function=os.link, symlinks=True)
    files_in = {f: fsha(src / f) for f in ("die_plan.json", "clock_entries.json", "core_macros.json",
                                            "core_clock_regions.json")}
    _write(dst / "die_plan.json", new)
    _gz(dst / "die_plan.json")
    _write(dst / "clock_entries.json", ce)
    _gz(dst / "clock_entries.json")
    _write(dst / "core_macros.json", cm, indent=1)
    _write(dst / "core_clock_regions.json", ccr, indent=1)
    pins_out = {}
    for inst, mod in SWAP.items():
        h = next(x for x in new["partition_types"][TYPE]["hard_cores"] if x["inst"] == inst)
        _write(dst / h["pins_file"], tables[mod], indent=None)
        pins_out[h["pins_file"]] = dict(sha256=fsha(dst / h["pins_file"]), pins=len(tables[mod]), module=mod)
    types, rest = changed_types(plan, new)
    files_out = {f: fsha(dst / f) for f in files_in}
    receipt = dict(event=EVENT, lane="DIE-HBM-92-EP", plan_in=str(src / "die_plan.json"),
                   sha_in=files_in["die_plan.json"], sha_out=files_out["die_plan.json"], files_in=files_in,
                   files_out=files_out, pins_files=pins_out, changed_types=types, changed_top_level=rest,
                   changes=changes, side_changes=side,
                   rtl=dict(vc2_and_host=a.rtl, vc2_sha256=fsha(a.rtl), base=a.base_rtl, base_sha256=fsha(a.base_rtl)),
                   note="as-built modules declared for NW_io u_ep_N0 / u_host_ep; no geometry/bus/station/cycle change; "
                        "children PROVISIONAL (no signed view of hfd_ep_static_vc2 / hfd_ep_host_vc)")
    _write(dst / "ep_mod_1108_event.json", receipt)
    with open(dst / "README.md", "r") as f:
        readme = f.read()
    (dst / "README.md").unlink()
    (dst / "README.md").write_text(readme + f"\n## {EVENT} (DIE-HBM-92-EP 2026-11-08)\n{src.name} "
                                   f"({files_in['die_plan.json'][:12]}) + {EVENT}: NW_io u_ep_N0 -> hfd_ep_static_vc2, "
                                   f"u_host_ep -> hfd_ep_host_vc (as-built modules, port-exact pin tables, outline kept); "
                                   f"die_plan.json sha256 {files_out['die_plan.json'][:12]}; types changed {types}. "
                                   "Receipt ep_mod_1108_event.json.\n")
    sums = []
    for line in (dst / "SHA256SUMS").read_text().splitlines():
        h, _, name = line.partition("  ")
        p = dst / name
        sums.append(f"{fsha(p) if p.is_file() else h}  {name}")
    for name in list(pins_out) + ["ep_mod_1108_event.json"]:
        if not any(s.endswith("  " + name) for s in sums):
            sums.append(f"{fsha(dst / name)}  {name}")
    (dst / "SHA256SUMS").unlink()
    (dst / "SHA256SUMS").write_text("\n".join(sums) + "\n")
    print(f"{EVENT}: sha {files_in['die_plan.json'][:12]} -> {files_out['die_plan.json'][:12]} types {types} "
          f"top-level {rest} pins {[(k, v['pins']) for k, v in pins_out.items()]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
