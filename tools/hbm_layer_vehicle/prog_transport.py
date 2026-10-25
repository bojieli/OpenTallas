#!/usr/bin/env python3
"""TOK-HBM 10-24: programme-install transport profile of a post-relay die (SU programme port + HC launch/config lanes).

coll_transport.py gave the COLL gather compiler the die's own lane timing.  The SU and HC emitters still assume the
GEN2 pin timing:
  * layer_images.py SU: su_prog (root) -> pgp_SW (pslice_c5) configuration write and start reach the consumer with the
    root contract "a write on root pin edge e pairs with a start on root pin edge e" and start -> line 0 = START_ADVANCE 9;
  * hc_images.py HC: launch D at cL on host_cp_ingress__launch_v -> hleaf_SW 2 flops -> target pin flop -> start.
On r18h5 every one of those legs is a forwarded relay chain (half-cycle lane stages + landing + L12 pads).  This tool
traces each lane in die.v (coll_transport.trace) and prices it with the same K/N landing rule as
d4g_bank_latency.Graph.lane_latency, reading K from the landing's own k2/k1/k0 ties in die.v (no contract needed; on
r18h5 the tie K equals the contract-note K: hcollgi_SW.launch_v prices 48 here and in transport_r18h5_kq.json).

Reported groups (a group whose members must land on one edge relative to each other):
  su_cfg    pgp_<q>.{cfg_we, cfg_bank, cfg_row, cfg_data, start, length}  (root bundles {r_we,r_bank} / {r_start,r_row}
            / {r_len,r_data}); skew != 0 means configuration writes pair a bank with another drive's row/data.
  hc_launch hc_<q>.launch_v and hc_eng.launch_v from host_cp_ingress__launch_v (through the hleaf of each target).
  hc_cfg    hc_<q>.cfg_v / cfg_addr and hc_eng.cfg_v from host_cp_ingress__cfg_v.
  hc_root_to_quarter  hc_eng -> hc_<q>.{d_v, i_v} lanes; hc_quarter_to_root: hc_eng.qps_v element lanes (MSB first).
            ot_hbm_hc_root_static prices these legs with its XRD / XRU parameters (root -> quarter / quarter -> root die
            relay stages, SYS_LAT); a die that relays them but binds XRD = XRU = 0 mis-times the root.

  python3 tools/hbm_layer_vehicle/prog_transport.py --die-v die.v --out prog_transport.json
Source-functional lane timing only (K/N model), never a physical-clock qualification.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import coll_transport as CT  # noqa: E402

SCHEMA = "opentallas.hbm_prog_transport.v1"
QS = ("SW", "SE", "NW", "NE")
SU_PORTS = ("cfg_we", "cfg_bank", "cfg_row", "cfg_data", "start", "length")
TIE = re.compile(r"1'd([01])")


def tie_k(ports):
    """landing K from its k2/k1/k0 constant ties (None when not tied to constants)."""
    bits = []
    for k in ("k2", "k1", "k0"):
        m = TIE.fullmatch((ports.get(k) or "").strip())
        if not m:
            return None
        bits.append(m[1])
    return int("".join(bits), 2)


PAD_N = {}        # l12p pad instance -> N stages (die.v header #(.W, .N) or hier-wrap module localparam N)
PAD_MOD_N = {}    # hier-wrap pad module (hbfd_pad_hw<k>) -> N


def load_pads(die_v):
    """fill PAD_N / PAD_MOD_N for die_v: hbfd_pad equal-age pads (L12) are N registered stages each."""
    PAD_N.clear(); PAD_MOD_N.clear()
    die_v = Path(die_v)
    for line in die_v.open():
        m = re.match(r"\s*hbfd_pad\s*#\((.*?)\)\s+(\w+)\s*\(", line)
        if m:
            n = re.search(r"\.N\((\d+)\)", m[1])
            if n:
                PAD_N[m[2]] = int(n[1])
    for hw in (die_v.parent / "hier_wraps.sv", die_v.parent / "slice" / "hier_wraps.sv"):
        if hw.exists():
            for m in re.finditer(r"module (hbfd_pad_hw\d+)\s*#\([^)]*?N\s*=\s*(\d+)", hw.read_text()):
                PAD_MOD_N[m[1]] = int(m[2])


def lane_latency(inst, hops):
    """d4g_bank_latency.Graph.lane_latency with K from the die.v ties: relay 1 edge; half-cycle lane stages N then a
    landing: ceil(N/2) + 1 + E, E = (K - ceil(N/2)) mod 8 or 8."""
    lat, half, notes = 0, 0, []
    for h in hops:
        m, ports = inst[h]
        if m.startswith("hbfd_rly"):
            lat += 1
        elif m.startswith("hbfd_pad"):
            n = PAD_N.get(h, PAD_MOD_N.get(m))
            if n is None:
                notes.append(f"{h}: pad N unknown ({m})")
            else:
                lat += n
        elif re.match(r"^hbfd_lh0?_", m):
            half += 1
        elif re.match(r"^hbfd_(land0?|lnd)_", m):
            k = tie_k(ports)
            if k is None:
                notes.append(f"{h}: landing K not tied"); lat += math.ceil(half / 2) + 2
            else:
                lat += math.ceil(half / 2) + 1 + ((k - math.ceil(half / 2)) % 8 or 8)
            half = 0
        else:
            notes.append(f"{h}: unpriced master {m}")
    if half:
        notes.append(f"{half} half-cycle hops without a landing"); lat += math.ceil(half / 2)
    return lat, notes


def lane(inst, name, port, through=None):
    """latency of name.port back to the slice/root pin; through = (inst, port) map for leaf hops (hleaf a_/b_ outputs
    re-enter at the hleaf's own input port, + the leaf's fixed latency)."""
    hops, root = CT.trace(inst, name, port)
    lat, notes = lane_latency(inst, hops)
    out = dict(latency_edges=lat, wrappers=len(hops), root=root[:160], notes=notes)
    if through:
        m = re.search(r"\b(hleaf_\w\w)__[ab]_(\w+?)\b", root)
        if m:
            up = lane(inst, m[1], m[2])
            out.update(leaf=m[1], leaf_in=up, latency_edges=lat + through + up["latency_edges"])
    return out


def lanes_of_concat(inst, name, port):
    """one lane per element of a {a, b, ...} port concatenation (MSB first), each traced like coll_transport.trace."""
    expr = inst[name][1][port].strip()
    elems = [e.strip() for e in expr.strip("{}").split(",")] if expr.startswith("{") else [expr]
    out = []
    for e in elems:
        tmp = dict(inst); tmp["__probe"] = ("probe", {"p": e})
        hops, root = CT.trace(tmp, "__probe", "p")
        lat, notes = lane_latency(inst, hops)
        out.append(dict(latency_edges=lat, wrappers=len(hops), root=root[:120], notes=notes))
    return out


def downstream_profile(die_v):
    """Expose every distinct command/data/calendar leg below the programme sequencer.

    Concatenations are traced element by element: one shortest component would hide
    the R8 skew that corrupts commands even when the programme start is aligned.
    """
    names = set()
    for line in Path(die_v).open():
        m = re.match(r"\s*\w+\s*(?:#\(.*?\))?\s+(\w+)\s*\(\s*$", line)
        if m and re.match(r"(?:su_|vmb_|calendar_|pgp_|suc|pg|vmd|vmstat|fr_)", m[1]):
            names.add(m[1])
    inst = CT.parse_instances(die_v, names)
    out = {}
    interesting = re.compile(r"control|command|vm[wr]_cmd|tree_cmd|lg_(read|write|rr|w_done)|rslot|wslot|rq[0-4]|wq[01]|launch_v|bank_enable|bank_client|client_seq|response|in$")
    for name in sorted(names & inst.keys()):
        ports = {}
        for port in inst[name][1]:
            if not interesting.search(port):
                continue
            legs = lanes_of_concat(inst, name, port)
            unique = {(x['latency_edges'], x['root']): x for x in legs}
            ports[port] = list(unique.values())
        if ports:
            out[name] = ports
    return out


def profile(die_v, leaf_lat=2):
    names = {f"pgp_{q}" for q in QS} | {f"hc_{q}" for q in QS} | {f"hleaf_{q}" for q in QS} | {"hc_eng"}
    load_pads(die_v)
    inst = CT.parse_instances(die_v, names)
    su = {}
    for q in QS:
        if f"pgp_{q}" not in inst:
            continue
        ls = {p: lane(inst, f"pgp_{q}", p) for p in SU_PORTS}
        vals = {p: v["latency_edges"] for p, v in ls.items()}
        su[q] = dict(lanes=ls, edges=vals, skew=max(vals.values()) - min(vals.values()),
                     we_minus_row=vals["cfg_we"] - vals["cfg_row"], start_edges=vals["start"])
    hc = {}
    for t in [f"hc_{q}" for q in QS] + ["hc_eng"]:
        if t not in inst:
            continue
        hc[t] = {p: lane(inst, t, p, through=leaf_lat) for p in ("launch_v", "cfg_v", "cfg_addr") if p in inst[t][1]}
        for p in ("d_v", "i_v"):                     # root -> quarter descriptor / issue lanes (qhub DRLY parameter)
            if p in inst[t][1]:
                hc[t][p] = lane(inst, t, p)
    xru = lanes_of_concat(inst, "hc_eng", "qps_v") if "hc_eng" in inst and "qps_v" in inst["hc_eng"][1] else []
    launch = {t: v["launch_v"]["latency_edges"] for t, v in hc.items() if "launch_v" in v}
    return dict(schema=SCHEMA, die_v=str(die_v), leaf_latency_edges=leaf_lat,
                downstream=downstream_profile(die_v),
                su_cfg={q: {k: v[k] for k in ("edges", "skew", "we_minus_row", "start_edges")} for q, v in su.items()},
                hc_launch_edges=launch, hc_launch_skew=(max(launch.values()) - min(launch.values())) if launch else None,
                hc_cfg_edges={t: v["cfg_v"]["latency_edges"] for t, v in hc.items() if "cfg_v" in v},
                hc_quarter_to_root_edges=[x["latency_edges"] for x in xru],
                hc_root_to_quarter_edges={t: {p: v[p]["latency_edges"] for p in ("d_v", "i_v") if p in v} for t, v in hc.items()},
                scope="source-functional lane timing (K/N model, K from die.v landing ties)",
                lanes=dict(su={q: v["lanes"] for q, v in su.items()}, hc=hc, hc_eng_qps_v=xru))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--die-v", type=Path, required=True)
    ap.add_argument("--leaf-latency", type=int, default=2, help="hleaf input -> a_/b_ output edges (ST_LAT, host_cfg_leaf.sv:18)")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    t = profile(a.die_v, a.leaf_latency)
    a.out.write_text(json.dumps(t, indent=1) + "\n")
    print(json.dumps({k: t[k] for k in ("su_cfg", "hc_launch_edges", "hc_launch_skew", "hc_cfg_edges", "hc_root_to_quarter_edges", "hc_quarter_to_root_edges")}))


if __name__ == "__main__":
    main()
