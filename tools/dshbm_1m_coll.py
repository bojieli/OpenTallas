#!/usr/bin/env python3
"""DS-V4.1 HBM accelerator, 1M token: the on-path collectives measured on ONE die's switched-tier endpoint RTL
(rtl/hbm_accel/tu/ot_hbm_accel_tu_endpoint.sv, bench tb_hbm_accel_tu_endpoint.sv) with only the Ethernet PHY +
Tomahawk-Ultra switch + cable traversal kept as a labelled vendor budget (tools/uarch_model.TU).

    python3 tools/dshbm_1m_coll.py fixtures DIR            # golden fixtures (AR: hdc_golden tree + to_bf16; gathers)
    python3 tools/dshbm_1m_coll.py campaign DIR > run.sh    # builds + runs (remote host)
    python3 tools/dshbm_1m_coll.py record DIR --out results/rtl/dshbm_1m_allmeasured_20261004/collectives.json

Each run measures, from the die's issue (go at the hub) to the last word of the result committed at the hub and
checked: endpoint TX (hub stages, port queues, wire stages, TX CDC, serializer pacing), the labelled budget per
crossing (BUDGET ns from this die's serializer to the far die's RX CDC), endpoint RX (RX CDC, wire stages, receive
buffer, reduction tree / delivery, hub stages) and every serialisation at the RTL port rate.  The other 95 dies are
replayed symmetrically by the stub (the bench header explains why that is exact for this static schedule).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

TP, FLIT_B, LANES = 96, 64, 16
CLK = 1.2e9
# TU tier (tools/uarch_model.TU, VENDOR BUDGET, RM104 App. A): what stays a budget
TU_PHY_NS, TU_SWITCH_NS, TU_CABLE_NS, TU_BRIDGE_NS, TU_TAIL_US = 100.0, 250.0, 27.6, 100.0, 0.15
BUDGET_NS = TU_PHY_NS + TU_SWITCH_NS + TU_CABLE_NS          # 377.6 ns a crossing
CRED_NS = TU_PHY_NS + TU_CABLE_NS / 2                       # reverse-link credit return (labelled)
PORT_GBPS_PAYLOAD = 800 * 0.9                               # TU: 800G port x 0.9 framing efficiency (ASSUMED in TU)
# the on-path collective classes of the executed program (results/rtl/dshbm_baseline_measured_20261004/program.json)
GATHER_BYTES = [768, 1536, 3584, 3648, 4672, 7744, 8192, 10240, 32256, 147456, 393216]
AR_BYTES, AR_E = 32768, 1024                                # o-group: 8 groups x 8 contributors x 1,024 FP32
HUBS = {"ha2hub": dict(INJ=2, DEL=4), "matched": dict(INJ=8, DEL=10)}
SRCS = ["rtl/link/ot_link_afifo.sv", "rtl/hdc/ot_hdc_fastfp.sv", "rtl/hdc/ot_hdc_prefix.sv",
        "rtl/hdc/ot_hdc_fp32_add_lat.sv", "rtl/hbm_accel/ha2_ar/ot_ha2_prims.sv",
        "rtl/hbm_accel/tu/ot_hbm_accel_tu_endpoint.sv", "rtl/hbm_accel/tu/tb_hbm_accel_tu_endpoint.sv"]


def gather_pf(nbytes, P):
    return max(1, math.ceil(P * nbytes / TP / FLIT_B))


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def hexword(vals, bits):
    w = 0
    for i, v in enumerate(vals):
        w |= int(v) << (bits * i)
    return f"{w:0{len(vals) * bits // 4}x}"


def cmd_fixtures(a):
    import ha2_ar_fixture as HF
    out = Path(a.dir) / "fx"
    meta = {}
    for P in (1, 6):
        HF.SHAPES[f"ds_p{P}"] = dict(HF.SHAPES["ds"], E=AR_E * P)
        meta[f"ar_p{P}"] = HF.write(out / f"ar_p{P}", f"ds_p{P}", 20261004 + P)
    rng = np.random.default_rng(96)
    pfmax = max(gather_pf(b, P) for b in GATHER_BYTES for P in (1, 6))
    words = rng.integers(0, 2 ** 32, size=(TP * pfmax, LANES), dtype=np.uint64)
    # the bench indexes part[rank * PF + m]; one file per PF value keeps the indexing exact
    for pf in sorted({gather_pf(b, P) for b in GATHER_BYTES for P in (1, 6)}):
        d = out / f"gather_pf{pf}"
        d.mkdir(parents=True, exist_ok=True)
        (d / "part.hex").write_text("\n".join(hexword(list(words[i]), 32) for i in range(TP * pf)) + "\n")
        meta[f"gather_pf{pf}"] = dict(pf=pf, lines=TP * pf, sha256=sha(d / "part.hex"))
    (out / "fixtures.json").write_text(json.dumps(meta, indent=1, default=str) + "\n")
    print(json.dumps({k: v.get("sha256", v.get("pf")) for k, v in meta.items()}, indent=0)[:2000])


def cmd_campaign(a):
    D = lambda kv: " ".join(f"+define+TU_{k}={v}" for k, v in kv.items())   # noqa: E731
    lines = ["#!/bin/bash", "set -u", f"cd {a.dir}", "V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator",
             f"SRC=\"{' '.join('src/' + s for s in SRCS)}\"", "mkdir -p b runs",
             "sha256sum $SRC > runs/input_sha256.txt"]
    builds = {}
    for hub, hp in HUBS.items():
        builds[f"ar_{hub}"] = dict(NC=8, NOG=8, PFMAX=384, BF16=1, **hp)
        builds[f"ga_{hub}"] = dict(NC=1, NOG=96, PFMAX=384, BF16=0, **hp)
    for b, kv in builds.items():
        lines.append(f"( /usr/bin/time -v $V --binary --timing -j 8 -Wno-fatal -Wno-lint -Wno-style --x-assign fast "
                     f"--x-initial fast --top-module tb_hbm_accel_tu_endpoint --Mdir b/{b} {D(kv)} $SRC "
                     f"> runs/build_{b}.log 2>&1; echo $? > runs/build_{b}.exit ) &")
    lines.append("wait")
    jobs = []
    for hub in HUBS:
        for P in (1, 6):
            for rank in (0, 3, 13, 62, 63):
                for s in (1, 2):
                    jobs.append(f"b/ar_{hub}/Vtb_hbm_accel_tu_endpoint +VEC=fx/ar_p{P} +PF={AR_E * P // LANES} "
                                f"+RANK={rank} +SEED={s} > runs/ar_{hub}_p{P}_r{rank}_s{s}.log 2>&1")
        for pf in sorted({gather_pf(b, P) for b in GATHER_BYTES for P in (1, 6)}):
            for rank in (0, 47, 95):
                for s in (1, 2):
                    jobs.append(f"b/ga_{hub}/Vtb_hbm_accel_tu_endpoint +VEC=fx/gather_pf{pf} +PF={pf} +RANK={rank} "
                                f"+SEED={s} > runs/ga_{hub}_pf{pf}_r{rank}_s{s}.log 2>&1")
    # budget sensitivity: the endpoint-side time must not depend on the budget (pure delay)
    for hub in HUBS:
        jobs.append(f"b/ar_{hub}/Vtb_hbm_accel_tu_endpoint +VEC=fx/ar_p1 +PF=64 +RANK=0 +SEED=1 +BUDGET=477.6 "
                    f"> runs/ar_{hub}_p1_r0_s1_b477.log 2>&1")
        jobs.append(f"b/ga_{hub}/Vtb_hbm_accel_tu_endpoint +VEC=fx/gather_pf2 +PF=2 +RANK=0 +SEED=1 +BUDGET=477.6 "
                    f"> runs/ga_{hub}_pf2_r0_s1_b477.log 2>&1")
    lines.append("cat > runs/jobs.txt <<'EOF'")
    lines += jobs
    lines.append("EOF")
    lines.append("xargs -P 32 -I{} bash -c '[ -x $(echo {} | cut -d\" \" -f1) ] && {}' < runs/jobs.txt")
    lines.append("sha256sum -c runs/input_sha256.txt > runs/pins_after.log 2>&1; echo $? > runs/pins_after.exit")
    lines.append("echo done > runs/campaign.exit")
    print("\n".join(lines))


PAT = re.compile(r"TUDONE (.*)")


def parse(p):
    m = PAT.search(Path(p).read_text(errors="replace"))
    if not m:
        return None
    d = {}
    for kv in m.group(1).split():
        k, v = kv.split("=")
        d[k] = float(v) if "." in v else int(v)
    return d


def cmd_record(a):
    runs = Path(a.dir) / "runs"
    res = {}
    bad = []
    for f in sorted(runs.glob("*.log")):
        if not f.name.startswith(("ar_", "ga_")) or f.name.endswith("_b477.log"):
            continue
        r = parse(f)
        if r is None:
            bad.append(f.name)
            continue
        key = f.stem.rsplit("_r", 1)[0]          # e.g. ar_ha2hub_p1 / ga_matched_pf24
        res.setdefault(key, []).append(dict(r, log=f.name))
    sens = {f.stem: parse(f) for f in runs.glob("*_b477.log")}
    out = dict(schema="opentallas.dshbm-1m.collectives.v1",
               scope="DS-V4.1 HBM accelerator, TP-96, Tomahawk-Ultra-protocol tier: ONE die's collective endpoint in "
                     "RTL (ot_hbm_accel_tu_endpoint: HA2's hub/slots/golden reduction tree/delivery + switched port "
                     "side), far side a behavioural TU stub (labelled budget) replaying the other 95 dies symmetrically",
               clock_hz=CLK, budget=dict(per_crossing_ns=BUDGET_NS, endpoint_phy_ns=TU_PHY_NS, switch_ns=TU_SWITCH_NS,
                                         cable_ns=TU_CABLE_NS, credit_return_ns=CRED_NS,
                                         basis="VENDOR BUDGET (uarch_model.TU, Broadcom SUE RM104 App. A); the TU "
                                               "'endpoint bridge 100 ns' is REPLACED by the measured RTL"),
               port=dict(ports=8, payload_gbps=PORT_GBPS_PAYLOAD, flit_bits=545, payload_bits=512,
                         note="serializer pacing in RTL at 720 Gb/s payload a port (TU 800G x 0.9 framing, ASSUMED in "
                              "TU); 545-bit flit (512 data + 33-bit header); egress to the die paced at the same rate"),
               runs={}, failed_logs=bad, sensitivity_budget_477=sens)
    for k, v in sorted(res.items()):
        lat = [x["lat_ns"] for x in v]
        out["runs"][k] = dict(n=len(v), lat_ns_max=max(lat), lat_ns_min=min(lat),
                              exact=all(x["mismatches"] == 0 and x["faults"] == 0 for x in v),
                              own_exact_words=sum(x.get("own_exact", 0) for x in v),
                              credit_stall_max=max(x["credit_stall"] for x in v),
                              tx_first_ns=max(x["tx_first_ns"] for x in v), tx_last_ns=max(x["tx_last_ns"] for x in v),
                              rx_first_ns=max(x["rx_first_ns"] for x in v), rx_last_ns=max(x["rx_last_ns"] for x in v),
                              deliver_tail_ns=max(x["deliver_tail_ns"] for x in v),
                              res_first_ns=max(x["res_first_ns"] for x in v), res_last_ns=max(x["res_last_ns"] for x in v),
                              got=v[0]["got"])
    # per collective class and P
    classes = []
    for hub in HUBS:
        for P in (1, 6):
            r = out["runs"].get(f"ar_{hub}_p{P}")
            if r:
                classes.append(_row("all_reduce", AR_BYTES, P, hub, r, 2))
            for B in GATHER_BYTES:
                pf = gather_pf(B, P)
                r = out["runs"].get(f"ga_{hub}_pf{pf}")
                if r:
                    kind = {393216: "topk_merge(sel)", 768: "topk_merge(argmax)", 147456: "kv_gather"}.get(B, "all_gather")
                    classes.append(_row(kind, B, P, hub, r, 1, pf=pf))
    out["classes"] = classes
    out["exact_all"] = all(r["exact"] for r in out["runs"].values()) and not bad
    out["still_budget"] = [
        "Ethernet PHY/FEC Tx+Rx 100 ns, Tomahawk Ultra switch 250 ns, 2 x 3 m twinax 27.6 ns: one 377.6 ns budget a "
        "crossing (VENDOR BUDGET, RM104)",
        "credit return over the reverse link 113.8 ns (labelled; sizes the 256-flit receive buffer)",
        "port payload rate 720 Gb/s (TU's 0.9 Ethernet/SUE framing efficiency, ASSUMED)",
        "striping tail 0.15 us over ~8 switch chips (TU _TAIL_US): the RTL stripes over 8 ports with identical port "
        "latency, so inter-chip skew is NOT captured -- kept as a labelled budget term"]
    out["per_token"] = per_token(out)
    out["as_built_baseline_endpoint"] = (
        "rtl/gpu_sys/ot_gpu_coll_endpoint (the GPU-organised endpoint, also HA3's base) cannot carry the DS TP-96 "
        "collectives: coll_count is 8 bits and NL <= 255 lanes (<= 1,020 B a request), a gather needs count x R <= NL, "
        "so at R = 96 a request carries <= 2 lanes = 8 B a rank, with ONE collective outstanding and 64-B records; the "
        "on-path gathers are 8-4,096 B a rank at P = 1 (1-512 requests each, every request a full switch round trip). "
        "Its routed context (HA3 phys3, 0.833 ns) fails SS -1.70 ns on its RX CDC -> asmb path.")
    out["physical"] = (
        "ot_hbm_accel_tu_endpoint has NO area/route/SS-FF evidence (new). Its blocks: ot_hdc_fp32_add_lat LAT 7 closes "
        "SS at 1.2 GHz standalone (w11_fp nm_fadd7, +40.1 ps); ot_link_afifo / ot_ha2_* never routed (HA2 G-route / "
        "G-timing NOT RUN). The hub stages (35 + 14 at 430 um) are floorplan-derived (results/floorplan/hbm_gpu/"
        "v41_hbm_die.json). The 256-flit receive buffer a port (8 x 256 x 545 b = 1.1 Mb) is sized to the 113.8 ns "
        "credit loop at 720 Gb/s and is not in any area ledger.")
    out["lookup"] = ("tools/dshbm_1m_coll.lookup(rec, kind, nbytes, P, hub='ha2hub', tail=True): every on-path size is "
                     "a measured class (gathers by flits a rank = ceil(P x bytes / 96 / 64)); topk_merge(sel) adds the "
                     "separately measured 96 x 512 select, P x 419 cycles")
    out["inputs"] = {s: sha(ROOT / s) for s in SRCS}
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, indent=1) + "\n")
    for c in classes:
        print(f"{c['hub']:8s} P{c['P']} {c['kind']:20s} {c['bytes']:7d}B  total {c['total_us']:.4f} us  ep_only "
              f"{c['endpoint_only_cycles']:.0f} cyc  exact {c['exact']}")
    print("exact_all", out["exact_all"], "failed", bad)


def _row(kind, B, P, hub, r, crossings, pf=None):
    lat = r["lat_ns_max"]
    ep = lat - crossings * BUDGET_NS
    tx = r["tx_first_ns"]                                   # issue -> first flit off the serializer
    rx = r["deliver_tail_ns"]                               # last flit into RX CDC -> last word at the hub
    # arrival stream at the RTL port rate (+ credit effects); AR: the multicast phase (results of the 64 owners)
    ser = r["rx_last_ns"] - (r["res_first_ns"] + BUDGET_NS if kind == "all_reduce" else r["rx_first_ns"])
    return dict(kind=kind, bytes=B, P=P, hub=hub, flits_per_rank=pf, crossings=crossings, lat_ns=round(lat, 3),
                endpoint_tx_cycles=round(tx * CLK * 1e-9, 1), endpoint_rx_cycles=round(rx * CLK * 1e-9, 1),
                serialisation_cycles=round(ser * CLK * 1e-9, 1),
                endpoint_only_cycles=round(ep * CLK * 1e-9, 1), tu_budget_ns=crossings * BUDGET_NS,
                total_us=round(lat / 1e3, 4), total_with_tail_us=round(lat / 1e3 + TU_TAIL_US, 4),
                exact=r["exact"], n_runs=r["n"], credit_stall_max=r["credit_stall_max"])


def per_token(rec):
    """Sum over the executed program's on-path collectives (the W19 composer's OFF_PATH_COLL excluded), against the
    TU vendor-budget model it replaces (uarch_model.tu_transport_us + the same measured select)."""
    import uarch_model as U
    import w19_hbm_token_compose as WC
    prog = json.loads((ROOT / "results/rtl/dshbm_baseline_measured_20261004/program.json").read_text())
    out = {}
    for hub in HUBS:
        for P in (1, 6):
            t = t0 = mdl = 0.0
            n = 0
            for lay in prog["layers"]:
                for op in lay["ops"]:
                    if op["kind"] in ("all_gather", "all_reduce", "topk_merge", "kv_gather") and \
                            not op["tag"].startswith(WC.OFF_PATH_COLL):
                        sel = P * 419 / CLK * 1e6 if (op["kind"] == "topk_merge" and op.get("what") == "sel") else 0.0
                        t += lookup(rec, op["kind"], op["bytes"], P, hub, True) + sel
                        t0 += lookup(rec, op["kind"], op["bytes"], P, hub, False) + sel
                        mdl += U.tu_transport_us(op["kind"], P * op["bytes"]) + sel
                        n += 1
            out[f"{hub}_P{P}"] = dict(collectives=n, measured_us=round(t, 2), measured_without_tail_us=round(t0, 2),
                                      model_tu_us=round(mdl, 2))
    out["primary"] = "ha2hub (INJ 2 / DEL 4 flits a cycle: HA2's sized hub), with the 0.15 us tail budget"
    return out


def lookup(rec, kind, nbytes, P, hub="ha2hub", tail=True):
    """us of one collective (kind as in program.json, nbytes = op bytes) from the record: gathers by their flit count
    a rank (the measured classes cover every on-path size); AR by its P."""
    for c in rec["classes"]:
        if c["hub"] != hub or c["P"] != P:
            continue
        if kind == "all_reduce" and c["kind"] == "all_reduce":
            return c["total_with_tail_us" if tail else "total_us"]
        if kind != "all_reduce" and c["kind"] != "all_reduce" and c["flits_per_rank"] == gather_pf(nbytes, P):
            return c["total_with_tail_us" if tail else "total_us"]
    raise KeyError((kind, nbytes, P, hub))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=("fixtures", "campaign", "record"))
    ap.add_argument("dir")
    ap.add_argument("--out", default=str(ROOT / "results/rtl/dshbm_1m_allmeasured_20261004/collectives.json"))
    a = ap.parse_args()
    {"fixtures": cmd_fixtures, "campaign": cmd_campaign, "record": cmd_record}[a.step](a)
