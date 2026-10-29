#!/usr/bin/env python3
"""HEAD-KITS-1: kit land_slots.json (face_guard --land) from the kit landing_contract.json.

Every landing band <b> of the contract is a declared landing-ring input bus with D = forwarded_write_flops / ring_width
slots (hold_mux slot form, as DIE-HEAD-9 face/land_slots_hd_tile.json), and so are its in-band monitor inputs
cland_dn_ready_<b> / cland_dn_fault_<b> when the contract declares them.  face_guard still proves every slot flop
(D loads per bit, own-Q hold, write condition) on the netlist; this only declares which buses are landing buses."""
import json, re, sys
from pathlib import Path

# declared START inputs (COORD 10-28 21:38 ASK1): cland_fstart_in_<b> wired to a ring t_rst_n / an origin p_start
START_PINS = ("t_rst_n", "p_start")
START_LOADS_PER_INST = 8      # direct-load cap per receiving instance (face_guard proves the cone beyond it)
_INST = re.compile(r"\b([A-Za-z_]\w*)\s*(?:#\s*\((?:[^()]|\([^()]*\))*\))?\s+([A-Za-z_]\w*)\s*\((.*?)\)\s*;", re.S)
_CONN = re.compile(r"\.(" + "|".join(START_PINS) + r")\s*\(\s*([A-Za-z_]\w*)\s*\)")
_WIRE = re.compile(r"\b(?:wire|assign)\s+([A-Za-z_]\w*)\s*=\s*([^;]*);")
_FSTART = re.compile(r"\bcland_fstart_in_\w+")


def start_decls(rtl_texts, ports):
    """{port: {insts, max_loads}} for every cland_fstart_in_* input port in `ports`, from the generated top RTL:
    the instances whose t_rst_n / p_start pin is that port, directly or through one generated select wire
    (`wire cland_pstart = strap ? cland_fstart_in_a : cland_fstart_in_b`); face_guard proves the netlist cone."""
    hit = {}
    for t in rtl_texts:
        t = re.sub(r"//[^\n]*", "", t)
        expr = {w: set(_FSTART.findall(e)) for w, e in _WIRE.findall(t)}   # one level: wire x = sel ? fs_a : fs_b
        for m in _INST.finditer(t):
            for pin, net in _CONN.findall(m.group(3)):
                for port in ({net} if net.startswith("cland_fstart_in_") else expr.get(net, set())):
                    if port in ports:
                        hit.setdefault(port, set()).add(m.group(2))
    miss = sorted(p for p in ports if p.startswith("cland_fstart_in_") and p not in hit)
    if miss:
        raise SystemExit(f"START port(s) with no t_rst_n/p_start instance in the kit RTL: {miss}")
    return {p: {"insts": sorted(v), "max_loads": START_LOADS_PER_INST * len(v)} for p, v in sorted(hit.items())}


def land_slots(contract):
    pins = {p["name"] for p in contract.get("pins", []) if p.get("dir") == "in"}
    buses = {}
    for b, v in sorted(contract.get("bands", {}).items()):
        w, fw = int(v["ring_width"]), int(v["clock_roles"]["forwarded_write_flops"])
        if fw % w or fw // w < 2:
            raise SystemExit(f"band {b}: forwarded_write_flops {fw} / ring_width {w} is not a slot count >= 2")
        spec = {"D": fw // w, "form": "hold_mux"}
        buses[b] = spec
        for m in ("ready", "fault"):
            if f"cland_dn_{m}_{b}" in pins:
                buses[f"cland_dn_{m}_{b}"] = dict(spec)
    return {"schema": "opentallas.land_slots.v1", "buses": buses}


if __name__ == "__main__":
    for kd in map(Path, sys.argv[1:]):
        c = json.loads((kd / "landing_contract.json").read_text())
        d = land_slots(c)
        ins = {p["name"] for p in c.get("pins", []) if p.get("dir") == "in"}
        d["starts"] = start_decls([f.read_text() for f in sorted((kd / "rtl").glob("*.sv"))], ins)
        (kd / "land_slots.json").write_text(json.dumps(d, indent=1, sort_keys=True) + "\n")
        print(kd / "land_slots.json", len(d["buses"]), "starts", len(d["starts"]))
