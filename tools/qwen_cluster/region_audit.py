#!/usr/bin/env python3
"""Q-CLUSTER16 region audit of qfd_c_b16_dv (16 regional clocks, one per A0 tile).

Reads the generated RTL (fabric + cluster) and the contract, and checks:
  R1  every fabric register (station, relay, soft reset stage, xstn) is clocked by the root of the region its planned
      site lies in (qc_gen.quad), and every A0 clock entry of tile (c, r) takes ck_c<c>r<r>;
  R2  every net that crosses a region seam goes straight from one register to the next register (a single registered
      hop: fixed one-edge latency, no logic, no flow control);
  R3  every crossing joins NEIGHBOURING regions (|dc| <= 1 and |dr| <= 1), so the die's neighbour-skew check covers it;
  R4  every crossing hop is within reach (<= 405 um, planned sites / tile faces).
Writes the crossing list (for the compiler: added edges per link = 0; for the die: the communicating region pairs whose
regional clocks must be neighbour-matched).

  region_audit.py [--fabric F] [--cluster C] [--out JSON] [--mutate station|tile]   (fail-witness self-test:
      'station' rebinds one c0r0 station to ck_c3r3, 'tile' rebinds tile (0,0)'s ck entry to ck_c2r0)
Prints REGION_AUDIT_PASS / REGION_AUDIT_FAIL <n>.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RTL = ROOT / "rtl/physical/qcluster"
ARCH = ROOT / "results/arch/qwen_cluster_1017"
LIMIT = 405.0


def rc(q):
    m = re.fullmatch(r"c(\d)r(\d)", q)
    return int(m.group(1)), int(m.group(2))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fabric", default=str(RTL / "qfd_c_b16_dv_fabric.sv"))
    ap.add_argument("--cluster", default=str(RTL / "qfd_c_b16_dv.sv"))
    ap.add_argument("--out")
    ap.add_argument("--mutate", choices=["station", "tile"])
    a = ap.parse_args()
    fab = Path(a.fabric).read_text()
    clu = Path(a.cluster).read_text()
    C = json.loads((ARCH / "cluster_contract_dv.json").read_text())
    sites = {s["inst"].split(".", 1)[1]: s for s in json.loads((ARCH / "relay_sites_dv.json").read_text())["sites"]}
    if a.mutate == "station":
        fab = re.sub(r"(u_dn0_rly1 \(\.ck\()ck_c0r\d", r"\1ck_c3r3", fab, count=1)
    if a.mutate == "tile":
        clu = re.sub(r"(u_t_0_0 \(\n\s+\.ck\()ck_c0r0", r"\1ck_c2r0", clu, count=1)
    xs, ys = C["region_seams"]["x"], C["region_seams"]["y"]

    def region_at(x, y):
        return f"c{sum(x >= v - 1e-6 for v in xs)}r{sum(y >= v for v in ys)}"

    fails = []
    # ---- registers: inst -> (clock region, d nets, q nets)
    regs = {}
    for m in re.finditer(r"(qfd_c_stn\d+|qfd_q3h_(?:stn|run) #\((?:[^()]|\([^()]*\))*\)) (\w+) \(\.ck\(ck_(\w+)\), \.d\((\w+)\), \.q\((\w+)\)\)", fab):
        regs[m.group(2)] = dict(region=m.group(3), d=[m.group(4)], q=[m.group(5)], kind=m.group(1).split(" ")[0])
    for m in re.finditer(r"(qfd_c_xstnw?) (\w+) \(\.ck\(ck_(\w+)\), \.rst_n\((\w+)\), \.sidx\([^)]*\), \.b_d\((\w+)\), \.a_d\((\w+)\), \.tap_d\((\w+)\)\)", fab):
        regs[m.group(2)] = dict(region=m.group(3), d=[m.group(5), m.group(4)], q=[m.group(6), m.group(7)], kind=m.group(1))
    n_sv = len(re.findall(r"\.ck\(ck_", fab))
    if n_sv != len(regs):
        fails.append(f"R1 parse: {n_sv} clocked instances in the fabric, {len(regs)} parsed")
    # R1 fabric
    for inst, r in regs.items():
        st = sites.get(inst)
        if st is None:
            continue      # MUT-only delay cells (qfd_q3h_run D=0) carry no site: they take their neighbour's clock
        x, y = st["at"]
        # a register planned ON a seam (rounded site within 0.01 um, e.g. a leg along a row-gap centre) may take either side
        want = {region_at(x + dx, y + dy) for dx in (-0.01, 0, 0.01) for dy in (-0.01, 0, 0.01)}
        if r["region"] not in want:
            fails.append(f"R1 {inst} clocked by ck_{r['region']} but sits in {want} at {st['at']}")
    # R1 tiles
    tiles = {}
    for m in re.finditer(r"(qfd_tile_n[kl]_rp2_romleaf_rr) u_t_(\d)_(\d) \((.*?)\);", clu, re.S):
        c, r_ = int(m.group(2)), int(m.group(3))
        cks = set(re.findall(r"\.ck\w*\(ck_(\w+)\)", m.group(4)))
        tiles[(c, r_)] = cks
        if cks != {f"c{c}r{r_}"}:
            fails.append(f"R1 tile ({c},{r_}) clock entries take {sorted(cks)}, want ck_c{c}r{r_}")
    if len(tiles) != 16:
        fails.append(f"R1 parse: {len(tiles)} A0 tiles")
    # ---- nets: alias resolution (assign a = b;  and the MUT=0 qfd_q3h_run D=0 pass-through is a register only if D=1)
    alias = dict((m.group(1), m.group(2)) for m in re.finditer(r"(?:assign|wire) (\w+) = (\w+);", fab))
    alias.update((m.group(1), m.group(2)) for m in re.finditer(r"wire \[\d+:0\] (\w+) = \(MUT == \d\) \? \{[^}]*\} : (\w+);", fab))

    def res(n):
        while n in alias:
            n = alias[n]
        return n
    # qfd_q3h_run (MUT delay) is a zero-depth wire at MUT 0: treat d -> q as an alias, not a register
    for inst in [i for i, r in regs.items() if r["kind"] == "qfd_q3h_run"]:
        alias[regs[inst]["q"][0]] = regs[inst]["d"][0]
        del regs[inst]
    prod = {}
    for inst, r in regs.items():
        for q in r["q"]:
            prod[q] = (inst, r["region"])
    for (c, r_) in tiles:
        for pfx in ("t_out", "n_y"):
            prod[f"{pfx}_{c}_{r_}"] = (f"u_t_{c}_{r_}", f"c{c}r{r_}")
    # consumers: registers (d), tiles (tap / trst / n_a / n_b via fabric outputs), cluster ports
    cons = []
    for inst, r in regs.items():
        for d in r["d"]:
            cons.append((res(d), inst, r["region"]))
    for m in re.finditer(r"assign ((tap|trst|n_a|n_b)_(\d)_(\d)) = (\w+);", fab):
        cons.append((res(m.group(5)), f"u_t_{m.group(3)}_{m.group(4)}.{m.group(2)}", f"c{m.group(3)}r{m.group(4)}"))
    for m in re.finditer(r"\.tap_d\((tap_(\d)_(\d))\)", fab):
        cons.append((m.group(1), f"u_t_{m.group(2)}_{m.group(3)}.tap", f"c{m.group(2)}r{m.group(3)}"))
    crossings, nreg = [], 0
    for net, dst, dreg in cons:
        if net in ("rst_n", "far", "far_n") or net.startswith(("bc", "rs_i")):
            continue        # die ports: pin register in its own region (boundary matched by the die)
        if net not in prod:
            fails.append(f"R2 {dst} input {net} is not driven by a register / tile output (comb path across a seam?)")
            continue
        src, sreg = prod[net]
        nreg += 1
        if sreg == dreg:
            continue
        (c0, r0), (c1, r1) = rc(sreg), rc(dreg)
        a_ = sites.get(src, {}).get("at")
        b_ = sites.get(dst, {}).get("at")
        hop = round(abs(a_[0] - b_[0]) + abs(a_[1] - b_[1]), 1) if a_ and b_ else None
        bits = int(re.search(rf"wire \[(\d+):0\] {re.escape(net)}\b", fab).group(1)) + 1 if re.search(
            rf"wire \[(\d+):0\] {re.escape(net)}\b", fab) else None
        x = dict(net=net, src=src, src_region=sreg, dst=dst, dst_region=dreg, bits=bits, hop_um=hop,
                 diagonal=(c0 != c1 and r0 != r1), added_edges=0)
        crossings.append(x)
        if abs(c0 - c1) > 1 or abs(r0 - r1) > 1:
            fails.append(f"R3 {src} ({sreg}) -> {dst} ({dreg}): not neighbouring regions")
        if hop is not None and hop > LIMIT:
            fails.append(f"R4 {src} -> {dst}: hop {hop} um > {LIMIT}")
    pairs = {}
    for x in crossings:
        k = "-".join(sorted((x["src_region"], x["dst_region"])))
        p = pairs.setdefault(k, dict(links=0, bits=0, diagonal=x["diagonal"]))
        p["links"] += 1
        p["bits"] += x["bits"] or 0
    out = dict(schema="opentallas.qcluster.region_audit.v1", master="qfd_c_b16_dv", regions=16,
               rule="single registered hop per seam crossing, neighbouring regions only; fixed one-edge latency "
                    "(added edges 0 vs the 8-region fabric); no landing inside the cluster: every crossing is a "
                    "zero-station root->root hop (LANDING-CONTRACT s2: zero-stage links need none) between regional "
                    "clocks that the die delivers neighbour-matched (<= 80 ps at the child flops, TT and FF)",
               register_edges_checked=nreg, crossings=len(crossings), crossing_bits=sum(x["bits"] or 0 for x in crossings),
               communicating_pairs=dict(sorted(pairs.items())), fails=fails, crossing_list=crossings,
               mutate=a.mutate)
    if a.out:
        Path(a.out).write_text(json.dumps(out, indent=1) + "\n")
    print(f"region audit: {nreg} register edges, {len(crossings)} seam crossings "
          f"({out['crossing_bits']} b) over {len(pairs)} region pairs ({sum(p['diagonal'] for p in pairs.values())} diagonal)")
    for f in fails[:20]:
        print("FAIL", f)
    print("REGION_AUDIT_PASS" if not fails else f"REGION_AUDIT_FAIL {len(fails)}")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
