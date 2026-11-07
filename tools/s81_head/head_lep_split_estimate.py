#!/usr/bin/env python3
"""DIE-HEAD-76 hd_lep0N_vC (Codex REMEDY Variant B): pre-build cell estimate of splitting hd_lep0N into four
pair-local regions + one LEP hub, from the measured synthesized netlist of the failed wave kit (1_synth_odb.v).

Every named cell is put in a region by its instance path; every anonymous (yosys _NNN_) cell inherits the region of
the named cells it drives (fixed point).  Two split forms are priced:

  D1  regions = pair k + coll_ik landing + coll_ok boundary; the LEP (with all four TX FIFOs) stays whole in the hub;
  D2  as D1, plus the LEP per-lane TX FIFO g_tx[k] (credit sender, 5 SRAM, lo_k face) moves into region k.  The
      g_tx[k] interface to the rest of the LEP is only {push copies, wd = {sq, frame half} 553 b, ovf}, so the cut is
      the push bundle (hub -> region) and the li_k credit link (region -> hub); the RX re-assembly (shared pair
      release) stays in the hub.

Each new crossing is priced twice: same clock region (boundary flops only, 1 cell/bit each side) and own clock
region (count-aligned landing ring at the receiver, per-bit cost measured on the coll_i landings of this netlist).

    python3 -I tools/s81_head/head_lep_split_estimate.py NETLIST.v --out estimate.json
"""
import argparse
import collections
import json
import re

OUTS = {"Y", "QN", "Q", "CON", "SN", "CO"}


def region(inst):
    m = re.match(r"u_core\.u\.u_lep\.u\.g_(tx|rx)\[(\d)\]", inst)
    if m:
        return f"lep_lane{m.group(2)}_{m.group(1)}"
    m = re.match(r"u_core\.u\.u_lep\.u\.lo(\d)_d", inst)
    if m:
        return f"lep_lo{m.group(1)}"
    if inst.startswith("u_core.u.u_lep"):
        return "lep_shared"
    if inst.startswith("u_core.u.u_land"):
        return "mu_land"
    m = re.search(r"u_(?:cland|bin|bout)_(coll_[io]\d)", inst)
    if m:
        return m.group(1)
    m = re.search(r"_(lepk_[io]0|lepf_i0|unit_i0|ctrl_o0|fault_o0|lw_o)\b", inst)
    if m:
        return "hub_io_" + m.group(1)
    if inst.startswith("u_core.u.g_pp"):
        return "pair"
    return "hub_misc"


def attribute(path):
    txt = open(path).read()
    body = txt[txt.index(");") + 2:]
    cells = []
    for m in re.finditer(r"\n\s*(\w+)\s+(\\\S+|\w+)\s*\((.*?)\);", body, re.S):
        cell, inst, pins = m.groups()
        if cell in ("wire", "input", "output", "assign", "module"):
            continue
        pp = dict((a, b.strip()) for a, b in re.findall(r"\.(\w+)\((.*?)\)\s*(?:,|$)", pins, re.S))
        cells.append((cell, inst.lstrip("\\"), pp))
    loads = collections.defaultdict(list)
    for i, (_, _, pp) in enumerate(cells):
        for p, net in pp.items():
            if p not in OUTS:
                loads[net].append(i)
    reg = [None if n.startswith("_") else region(n) for _, n, _ in cells]
    changed = True
    while changed:
        changed = False
        for i, (_, n, pp) in enumerate(cells):
            if reg[i] is not None:
                continue
            cand = collections.Counter(reg[j] for p, net in pp.items() if p in OUTS for j in loads.get(net, []) if reg[j])
            if not cand:
                for p, net in pp.items():
                    if p in OUTS and not net.lstrip("\\").startswith("_"):
                        cand[region(net.lstrip("\\"))] += 1
            if cand:
                reg[i] = cand.most_common(1)[0][0]
                changed = True
    std, mac = collections.Counter(), collections.Counter()
    for (cell, _, _), r in zip(cells, reg):
        (mac if cell.startswith("ot_") else std)[r or "hub_misc"] += 1
    return std, mac


def estimate(std, mac):
    land_bit = std["coll_i0"] / 517.0          # measured: coll_i0 landing ring + pin flops, 514 data + 3 ring bits
    push_w, li_w = 555, 558                      # {psh, sq, half 552, ovf back} / {li_v, li_d 553, flt 3, rxv-path}
    total = sum(std.values())
    coll = {k: std[f"coll_i{k}"] + std[f"coll_o{k}"] for k in range(4)}
    tx = {k: std[f"lep_lane{k}_tx"] + std[f"lep_lo{k}"] for k in range(4)}
    out = {"netlist_stdcells": total, "landing_cells_per_bit": round(land_bit, 2), "attribution": dict(std),
           "macros": dict(mac)}
    forms = {}
    for form in ("D1", "D2"):
        for xing in ("same_region", "own_region"):
            w_in_region = 553 + 3 if form == "D1" else push_w
            per_in = land_bit if xing == "own_region" else 1.0
            regions = {}
            for k in range(4):
                c = coll[k] + (tx[k] if form == "D2" else 0)
                c += round(w_in_region * per_in) + li_w   # receiver of the hub->region bundle + li out-flops
                regions[f"r{k}"] = c
            hub = total - sum(coll.values()) - (sum(tx.values()) if form == "D2" else 0)
            hub += 4 * (round(li_w * per_in) + w_in_region)
            forms[f"{form}_{xing}"] = {"hub": hub, **regions, "max_piece": max([hub, *regions.values()]),
                                       "cap_150k": max([hub, *regions.values()]) <= 150000}
    out["forms"] = forms
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("netlist")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    std, mac = attribute(a.netlist)
    r = estimate(std, mac)
    open(a.out, "w").write(json.dumps(r, indent=1) + "\n")
    print(json.dumps(r["forms"], indent=1))


if __name__ == "__main__":
    main()
