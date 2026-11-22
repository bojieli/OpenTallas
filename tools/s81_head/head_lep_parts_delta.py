#!/usr/bin/env python3
"""hd_lep0N as six wrapper CONTENTS joined by type nets (FABLE-FIX-HEAD-LEP0N-R4/R5 11-21), 0 added cycles.

    python3 -I tools/s81_head/head_lep_parts_delta.py PLAN.json OUT.json [--rxa "16'h0330"] [--report R.json]

The base plan has ONE content u_core (ot_s81hd_lep0N_noidx_core).  This delta declares the composition proven equal to
it (parts_gen.py / prove_parts.sh, PARTS_EQUIV_PASS): u_core = ot_s81hd_lep0N_noidx_hub, u_io = ot_s81hd_lep0N_io,
u_rg0..3 = ot_s81hd_lep0N_rgn, wired by whole-net type nets, and renames every instance path the plan carries
(hard cores, core taps, tap group regex, native stage group prefixes -> v2 form, bus leaves, internal stations).
No geometry, lane, port or cycle changes: it is the base of the type split (type_split.py net_drivers), not the split.
"""
import argparse
import copy
import json
import re
from collections import Counter
from pathlib import Path

TYPE = "hd_lep0N"
D = r"(\\?\.)"                                   # a dot, plain or regex-escaped
LB = r"((?:\\\\\\|\\\\\?\\|\\)?\[)"              # [ plain, \[ , \\\[ (escaped twice) or \\?\[ (tap group form)
RB = r"((?:\\\\\\|\\\\\?\\|\\)?\])"
IX = r"(\d+|\[0-3\])"                            # a lane index or the class [0-3]
IO_BUSES = ("lepk_i0", "unit_i0", "lepf_i0", "lepk_o0", "ctrl_o0", "fault_o0")


def nib(v, i):
    return (int(re.fullmatch(r"16'h([0-9a-fA-F]{4})", v).group(1), 16) >> (4 * i)) & 15


def renamer(krx, rxa, hits):
    def r_pair(m):
        hits["pair"] += 1
        return f"u_rg{m[4]}{m[6]}u_pair"

    def r_tx(m):
        hits["tx"] += 1
        return f"u_rg{m[6]}{m[1]}u_txl{m[1]}g_tx{m[5]}{m[6]}{m[7]}"

    def r_ktx(m):
        hits["ktx"] += 1
        return f"u_rg{m[4]}{m[6]}{m[7]}"

    def r_krx(m):
        i, leg, j = int(m[4]), m[7], int(m[10])
        kr, ra = nib(krx, i), nib(rxa, i)
        if (leg == "g_rxf" and j < ra) or (leg == "g_rxr" and j >= kr - ra):
            hits["krx_region"] += 1
            return f"u_rg{i}{m[6]}{leg}{m[8]}g_s{m[9]}{j}{m[11]}"
        hits["krx_hub"] += 1
        return m[0]

    def r_io(m):
        hits["io"] += 1
        return f"u_io{m[1]}u{m[2]}{m[3]}"

    rules = [(re.compile(rf"u_core{D}u{D}g_pp{LB}{IX}{RB}{D}u_pair"), r_pair),
             (re.compile(rf"u_core{D}u{D}u_lep{D}u{D}g_tx{LB}{IX}{RB}"), r_tx),
             (re.compile(rf"u_core{D}u{D}g_kl{LB}{IX}{RB}{D}(g_txf|g_txr)"), r_ktx),
             (re.compile(rf"u_core{D}u{D}g_kl{LB}(\d+){RB}{D}(g_rxf|g_rxr){D}g_s{LB}(\d+){RB}"), r_krx),
             (re.compile(rf"u_core{D}u{D}(g_pin|g_pout)\b"), r_io)]

    def rn(s):
        for rx, f in rules:
            s = rx.sub(f, s)
        return s
    return rn


def delta(plan, rxa="16'h0330"):
    t = plan["partition_types"][TYPE]
    if len(t["contents"]) != 1 or t["contents"][0]["module"] != "ot_s81hd_lep0N_noidx_core" or t.get("nets"):
        raise ValueError("base form changed: one content u_core (ot_s81hd_lep0N_noidx_core), no nets")
    t = copy.deepcopy(t)
    core = t["contents"][0]
    P = core["params"]
    if P.get("CH_B") != "4'b1111" or int(P.get("RFAN", 0)) <= 0 or int(P.get("PAIR", 0)) != 1:
        raise ValueError("parts form needs CH_B 4'b1111, PAIR 1, RFAN > 0")
    for i in range(4):
        if nib(rxa, i) > nib(P["KRX"], i):
            raise ValueError("RXA_i <= KRX_i")
    hits = Counter()
    rn = renamer(P["KRX"], rxa, hits)
    core["module"] = "ot_s81hd_lep0N_noidx_hub"
    core["params"] = dict(RXA=rxa, **P)
    nets = [("c0i", 514), ("c0o", 512), ("io_rs", int(P["PIN"]) + int(P["POUT"])), ("pin", 1150), ("pout", 1137)]
    core["bind"].update(c0i_x="net:c0i", c0o_x="net:c0o", io_rs="net:io_rs", pin_x="net:pin", pout_x="net:pout")
    rows = [dict(inst="u_io", module="ot_s81hd_lep0N_io", status="new", params=dict(PIN=P["PIN"], POUT=P["POUT"], RV=1),
                 bind=dict(ck="clk", rst_n="rst_n", rs="net:io_rs", pin_x="net:pin", pout_x="net:pout"),
                 note="controller-facing stage banks (inner u = ot_s81hd_lep0N_io_stages)")]
    drivers = {"c0i": "u_core.c0i_x", "c0o": "u_rg0.coll_o", "io_rs": "u_core.io_rs", "pin": "u_io.pin_x", "pout": "u_core.pout_x"}
    for i in range(4):
        for n, w, d in ((f"h2r{i}", 574, f"u_core.h2r{i}"), (f"rs{i}", 123, f"u_core.rs{i}"), (f"r2h{i}", 558, f"u_rg{i}.r2h")):
            nets.append((n, w))
            drivers[n] = d
            core["bind"][n] = "net:" + n
        bind = dict(ck="clk", rst_n="rst_n", h2r=f"net:h2r{i}", rs=f"net:rs{i}", r2h=f"net:r2h{i}")
        if i == 0:
            bind.update(coll_i="net:c0i", coll_o="net:c0o")
        rows.append(dict(inst=f"u_rg{i}", module="ot_s81hd_lep0N_rgn", status="new", bind=bind,
                         params=dict(K=i, CHB="1'b1", KCRED=P["KCRED"], IDX_EN=0, TXI=P["TXI"], RXH=P["RXH"],
                                     KT=nib(P["KTX"], i), KQ=nib(P["KTR"], i), KR=nib(P["KRX"], i), RA=nib(rxa, i), RV=1),
                         note=f"pair region {i}: TX lane (u_txl) + K TX stages + RA RX stages + pair macro (u_pair)"))
    t["contents"] += rows
    t["nets"] = [dict(name=n, width=w) for n, w in nets]
    for b in t["buses"]:
        inst, port = b["leaf"].split(".", 1)
        m = re.fullmatch(r"coll_([io])([1-3])", port)
        if inst != "u_core":
            raise ValueError("bus leaf " + b["leaf"])
        if m:
            b["leaf"] = f"u_rg{m[2]}.coll_{m[1]}"
        elif port in IO_BUSES:
            b["leaf"] = "u_io." + port
        elif port not in ("coll_i0", "coll_o0", "lw_o"):
            raise ValueError("bus leaf " + b["leaf"])
        hits["bus_leaf"] += b["leaf"].split(".")[0] != "u_core"
    for r in t.get("internal_stations", []):
        for k in ("capture", "launch"):
            m = re.fullmatch(r"u_core\.coll_([io])([1-3])", r.get(k) or "")
            if m:
                r[k] = f"u_rg{m[2]}.coll_{m[1]}"
                hits["istation"] += 1
    for h in t["hard_cores"]:
        h["inst"] = rn(h["inst"])
    ck = t["clock"]
    for tp in ck.get("taps", []):
        tp["name"] = rn(tp["name"])
    if "tap_group" in ck:
        ck["tap_group"]["re"] = rn(ck["tap_group"]["re"])
    g = ck["landing_contract"]["native_stage_groups"]
    if g["content"] != "u_core" or g["params"] != P:
        raise ValueError("native_stage_groups base form changed")
    seen = []
    for row in g["groups"]:
        row["prefix"] = rn(row["prefix"])
        o = row["prefix"].split("\\.")[0]
        if o not in seen:
            seen.append(o)
    by = {c["inst"]: c for c in t["contents"]}
    order = [c["inst"] for c in t["contents"] if c["inst"] in seen]
    if set(order) != set(seen):
        raise ValueError(f"native stage group owners {seen}")
    ck["landing_contract"]["native_stage_groups"] = dict(
        schema="opentallas.native_stage_groups.v2",
        contents=[dict(content=o, module=by[o]["module"], params=copy.deepcopy(by[o]["params"])) for o in order],
        groups=g["groups"])
    moved = [k for k in t.get("relay_sites", {}) if rn(k) != k]
    if moved:
        raise ValueError(f"relay sites in a region: {moved[:3]}")
    left = json.dumps(t).count("u_core.u.g_pp") + json.dumps(t).count("g_xl")
    if left:
        raise ValueError("stale pair paths left")
    out = copy.deepcopy(plan)
    out["partition_types"][TYPE] = t
    rep = dict(type=TYPE, rxa=rxa, renamed=dict(hits), contents=[c["inst"] for c in t["contents"]],
               nets={n: w for n, w in nets}, net_drivers=drivers,
               hard_cores=dict(Counter(h["inst"].split(".")[0] for h in t["hard_cores"])),
               stage_groups=dict(Counter(r["prefix"].split("\\.")[0] for r in g["groups"])))
    return out, rep


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("out")
    ap.add_argument("--rxa", default="16'h0330")
    ap.add_argument("--report")
    a = ap.parse_args(argv)
    out, rep = delta(json.loads(Path(a.plan).read_text()), a.rxa)
    Path(a.out).write_text(json.dumps(out, indent=1) + "\n")
    if a.report:
        Path(a.report).write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps(rep))


if __name__ == "__main__":
    main()
