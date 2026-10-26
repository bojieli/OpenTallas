#!/usr/bin/env python3
"""Q-CLUSTER16 region audit of qfd_c_b16_dv (16 regional clocks, one per A0 tile).

Reads the generated RTL (fabric + cluster) and the contract, and checks:
  R1  every fabric register (station, relay, soft reset stage, xstn) is clocked by the root of the region its planned
      site lies in (qc_gen.quad), and every A0 clock entry of tile (c, r) takes ck_c<c>r<r>;
  R2  every net that crosses a region seam goes straight from one register to the next register (a single registered
      hop: fixed one-edge latency, no logic, no flow control);
  R3  every crossing joins NEIGHBOURING regions (|dc| <= 1 and |dr| <= 1), so the die's neighbour-skew check covers it;
  R4  every crossing hop is within reach (<= 405 um, planned sites / tile faces);
  R5  (Q-CL16-LAND) every LANDED crossing of the contract (cluster_contract_dv.json "landings") is a ring
      (qfd_c_land_w on the source region root, fed flop-first by a source-region register) and a read half
      (qfd_c_land_r on the destination root, o consumed only by destination-region registers), and it is the ONLY path of
      that ordered region pair (the kit SDC's set_multicycle_path -from ck_<src> -to ck_<dst> covers exactly its
      bank -> o paths).
Writes the crossing list (for the compiler: added edges per link, 0 for a plain hop, E + 1 for a landed one; for the
die: the communicating region pairs).

  region_audit.py [--fabric F] [--cluster C] [--out JSON] [--mutate station|tile|landclk]   (fail-witness self-test:
      'station' rebinds one c0r0 station to ck_c3r3, 'tile' rebinds tile (0,0)'s ck entry to ck_c2r0, 'landclk' reads
      the first landing's ring on its WRITE clock, 'unland' bypasses the first landing)
  R6  (Q-CLUSTER-LANDALL) with the contract's landings mode 'all', every multi-bit crossing is landed; only the 1-bit
      reset-tree hops cross a seam as plain registered hops.
  R7  (Q-CB16RST 10-19) with landings resets 'region' (16 die-delivered regional resets), NO plain crossing remains:
      every seam crossing is landed.  Mutant 'rsthop' feeds c1r2's reset pin register from c1r1's (R7 FAIL).
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
    ap.add_argument("--mutate", choices=["station", "tile", "landclk", "unland", "rsthop"])
    a = ap.parse_args()
    fab = Path(a.fabric).read_text()
    clu = Path(a.cluster).read_text()
    C = json.loads((ARCH / "cluster_contract_dv.json").read_text())
    sites = {s["inst"].split(".", 1)[1]: s for s in json.loads((ARCH / "relay_sites_dv.json").read_text())["sites"]}
    if a.mutate == "station":
        fab = re.sub(r"(u_dn0_rly1 \(\.ck\()ck_c0r\d", r"\1ck_c3r3", fab, count=1)
    if a.mutate == "tile":
        clu = re.sub(r"(u_t_0_0 \(\n\s+\.ck\()ck_c0r0", r"\1ck_c2r0", clu, count=1)
    lands = {L["name"]: L for L in C.get("landings", {}).get("list", [])}
    if a.mutate == "landclk":
        if not lands:
            raise SystemExit("--mutate landclk: the contract lists no landing")
        L0 = next(iter(lands.values()))
        fab = re.sub(rf"(u_land_{L0['name']}_r \(\.ck\()ck_\w+?\)", rf"\1ck_{L0['src_region']})", fab, count=1)
    if a.mutate == "unland":
        # bypass the first landing: its consumer takes the ring's input (an unlanded multi-bit crossing again)
        if not lands:
            raise SystemExit("--mutate unland: the contract lists no landing")
        L0 = next(iter(lands.values()))
        i0 = re.search(rf"u_land_{L0['name']}_w \(.*?\.i\((\w+)\)", fab).group(1)
        fab = fab.replace(f".o(land_{L0['name']}))", f".o(land_{L0['name']}_dead))") + f"\n    assign land_{L0['name']} = {i0};\n"
    if a.mutate == "rsthop":
        # Q-CB16RST fail witness: region c1r2's reset pin register fed from c1r1's (a plain 1-bit reset hop across a seam)
        fab, n_ = re.subn(r"(u_rpin_c1r2 \(\.ck\(ck_c1r2\), \.d\()\w+\)", r"\1rpin_c1r1_q)", fab, count=1)
        if not n_:
            raise SystemExit("--mutate rsthop: no u_rpin_c1r2 (regional resets not generated)")
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
    PAR = r"#\((?:[^()]|\([^()]*\))*\)"
    for m in re.finditer(rf"qfd_c_land_w {PAR} (\w+) \(\.ck\(ck_(\w+)\), \.rsi\((\w+)\), \.i\((\w+)\), \.bank\((\w+)\), "
                         r"\.epo\((\w+)\), \.vld\((\w+)\)\)", fab):
        regs[m.group(1)] = dict(region=m.group(2), d=[m.group(3), m.group(4)], q=[m.group(5), m.group(6), m.group(7)],
                                kind="qfd_c_land_w", i=m.group(4))
    for m in re.finditer(rf"qfd_c_land_r {PAR} (\w+) \(\.ck\(ck_(\w+)\), \.rsi\((\w+)\), \.bank\((\w+)\), \.epo\((\w+)\), "
                         r"\.vld\((\w+)\), \.o\((\w+)\)\)", fab):
        # the ring -> read crossing is ONE landed link: bank is its data; epo / vld travel with it (checked in R5)
        regs[m.group(1)] = dict(region=m.group(2), d=[m.group(3), m.group(4)], q=[m.group(7)], kind="qfd_c_land_r",
                                side=[m.group(5), m.group(6)])
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
    # Q-CL16-LAND audit gap (Q-CL16-EARLY): a bench-mutant select 'assign x = (MUT == n ? y : z);' is z at MUT 0
    # (missed before: u_t_0_0.t_out -> u_t_1_0.n_a, c0r0 -> c1r0, 514 b)
    alias.update((m.group(1), m.group(2)) for m in re.finditer(r"assign (\w+) = \(MUT == \d+ \? \w+ : (\w+)\);", fab))

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
    for m in re.finditer(r"assign ((tap|trst|n_a|n_b)_(\d)_(\d)) = (\w+|\(MUT == \d+ \? \w+ : \w+\));", fab):
        # the fabric's trst_<c>_<r> drives the A0 tile's rst_n pin (Q-CL16-EARLY audit gap: was named 'trst')
        pin = "rst_n" if m.group(2) == "trst" else m.group(2)
        cons.append((res(m.group(1)), f"u_t_{m.group(3)}_{m.group(4)}.{pin}", f"c{m.group(3)}r{m.group(4)}"))
    for m in re.finditer(r"\.tap_d\((tap_(\d)_(\d))\)", fab):
        cons.append((m.group(1), f"u_t_{m.group(2)}_{m.group(3)}.tap", f"c{m.group(2)}r{m.group(3)}"))
    crossings, nreg = [], 0
    for net, dst, dreg in cons:
        if net in ("rst_n", "far", "far_n") or net.startswith(("bc", "rs_i")) or re.fullmatch(r"rst_c\dr\d", net):
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
                 diagonal=(c0 != c1 and r0 != r1), added_edges=0, landed=False)
        if regs.get(dst, {}).get("kind") == "qfd_c_land_r":
            nm = re.fullmatch(r"u_land_(\w+)_r", dst).group(1)
            L = lands.get(nm)
            if L is None:
                fails.append(f"R5 {dst}: landing not in the contract")
            else:
                x.update(landed=True, landing=nm, bits=L["bits"], ring_wires=bits, D=L["D"], E=L["E"], K=L["K"],
                         added_edges=L["added_edges"], crossing=L["crossing"])
        crossings.append(x)
        if abs(c0 - c1) > 1 or abs(r0 - r1) > 1:
            fails.append(f"R3 {src} ({sreg}) -> {dst} ({dreg}): not neighbouring regions")
        if hop is not None and hop > LIMIT:
            fails.append(f"R4 {src} -> {dst}: hop {hop} um > {LIMIT}")
    # R5 landings
    for nm, L in lands.items():
        w_, r_ = f"u_land_{nm}_w", f"u_land_{nm}_r"
        if w_ not in regs or r_ not in regs:
            fails.append(f"R5 landing {nm}: ring / read instance missing")
            continue
        if regs[w_]["region"] != L["src_region"] or regs[r_]["region"] != L["dst_region"]:
            fails.append(f"R5 landing {nm}: ring on ck_{regs[w_]['region']} / read on ck_{regs[r_]['region']}, contract "
                         f"{L['src_region']} -> {L['dst_region']}")
        src_i = prod.get(res(regs[w_]["i"]))
        if src_i is None or src_i[1] != L["src_region"]:
            fails.append(f"R5 landing {nm}: ring input {regs[w_]['i']} not from a {L['src_region']} register ({src_i})")
        if res(regs[r_]["d"][1]) != regs[w_]["q"][0] or [res(v) for v in regs[r_]["side"]] != regs[w_]["q"][1:]:
            fails.append(f"R5 landing {nm}: read half not fed by its own ring")
        oc = [(d_, dr) for n_, d_, dr in cons if n_ == regs[r_]["q"][0]]
        if not oc or any(dr != L["dst_region"] for _, dr in oc):
            fails.append(f"R5 landing {nm}: o consumers {oc} not all in {L['dst_region']}")
        # Q-CLUSTER-LANDALL: the kit SDC's multicycle is CELL-based (-from the ring's cells -to the read half's cells),
        # so other crossings of the same region pair stay single-cycle; they must be 1-bit reset-tree hops (R6)
        other = [x for x in crossings if x["src_region"] == L["src_region"] and x["dst_region"] == L["dst_region"]
                 and not x["landed"] and (x["bits"] or 0) > 1]
        if other:
            fails.append(f"R5 landing {nm}: {len(other)} other multi-bit {L['src_region']} -> {L['dst_region']} "
                         f"crossings, unlanded: {[o_['net'] for o_ in other][:4]}")
    # R6 (Q-CLUSTER-LANDALL): with landings 'all', EVERY multi-bit crossing is landed; only 1-bit reset hops cross plain
    # R7 (Q-CB16RST): with regional resets, NO crossing is plain: every seam crossing is landed (1-bit reset hops included)
    if C.get("landings", {}).get("resets") == "region":
        for x in crossings:
            if not x["landed"] and (x["bits"] or 0) <= 1:
                fails.append(f"R7 unlanded 1-bit crossing {x['src']} ({x['src_region']}) -> {x['dst']} ({x['dst_region']}) "
                             f"net {x['net']} (regional resets: no reset hop may cross a seam)")
    if C.get("landings", {}).get("mode") == "all":
        for x in crossings:
            if not x["landed"] and (x["bits"] or 0) > 1:
                fails.append(f"R6 unlanded {x['bits']}-b crossing {x['src']} ({x['src_region']}) -> {x['dst']} "
                             f"({x['dst_region']}) net {x['net']}")
    pairs = {}
    for x in crossings:
        k = "-".join(sorted((x["src_region"], x["dst_region"])))
        p = pairs.setdefault(k, dict(links=0, bits=0, diagonal=x["diagonal"]))
        p["links"] += 1
        p["bits"] += x["bits"] or 0
    out = dict(schema="opentallas.qcluster.region_audit.v1", master="qfd_c_b16_dv", regions=16,
               rule="Q-CLUSTER-LANDALL: every multi-bit seam crossing LANDED (R6), 1-bit reset hops plain; was: single registered hop per seam crossing, neighbouring regions only; fixed one-edge latency "
                    "(added edges 0 vs the 8-region fabric) between regional clocks the die delivers phase-aligned "
                    "(+/-60 ps, contract obligation 2); Q-CL16-LAND: a crossing whose in-cluster skew does not fit one "
                    "edge is LANDED (ring on the source root, read slot (rc - K) mod D on the destination root, "
                    "added E + 1 edges, multicycle -setup E -hold D-1; R5)",
               landed=sum(1 for x in crossings if x["landed"]),
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
