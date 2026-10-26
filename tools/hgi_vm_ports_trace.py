#!/usr/bin/env python3
"""VM.PORTS production-shape throughput trace (hgi-1010/vm, 2026-10-10).

The VM unit has no price of its own: every priced op assumes its VM traffic is served inside the op's price.  This tool
replays the DS AR 1M token's VM traffic (the same G25 rank-0 program, dyn counts and S2 schedule that
tools/throughput_budget/build.py prices) on the VM's client ports, so the RTL bench (rtl/hbm_accel/generic/vm/
tb_hgi_vm_ports_tput.sv) measures how long the VM really takes to serve each record that the schedule gives
[start, end) cycles.

Ports (the production client plan, hgi_vm5 view / ot_hgi_vm_die: RP 96 = 3 read groups, W2 96 = 3 write groups):
  R0 / W0  lane group lgW   SU, SFU, HC, and COLL (the collective's slices are SU-addressed: hgi_vmaddr -> SU)
  R1 / W1  lane group lgE   SM (x-load), ATT, FUSED (quant)
  R2       DMA source reads (DMA.STORE / KVWB_DS)          W2   COLL.ROW_GATHER sink (list-order rows)
  WP       the DMA wide write port (DMA.LOAD)
  P0 / P1 / P2  packet clients IDX / ARGMAX / COLL list reads (OUT 4 outstanding)
Each record's VM descriptors (exact effective base / n / m / strides, dyn counts applied) give its sector list
(word >> 3, unique, in order); reads (every desc but O / R) go to the port's read side, writes (O / R) to its write side.

  python3 tools/hgi_vm_ports_trace.py --out DIR [--idx-port lgE]  -> DIR/{cfg.svh, *.hex, manifest.json}
  python3 tools/hgi_vm_ports_trace.py --report DIR RUNLOG  -> ratio report from the bench's REC lines
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))

NSEC = 32768
LANES = 32
# stream id -> (name, kind): kind r = wide read group, w = wide write group, d = DMA wide write port, p = packet client
STREAMS = [("R0_lgW", "r"), ("R1_lgE", "r"), ("R2_dma", "r"), ("W0_lgW", "w"), ("W1_lgE", "w"), ("W2_coll", "w"),
           ("WP_dma", "d"), ("P0_idx", "p"), ("P1_argmax", "p"), ("P2_coll", "p")]
SID = {n: i for i, (n, _) in enumerate(STREAMS)}


IDX_PORT = "packet"                                # --idx-port lgE: IDX as a node of the lgE read/write chain


def ports_of(unit, op):
    """(read stream, write stream) of a record."""
    if unit in ("SU", "SFU", "HC"):
        return "R0_lgW", "W0_lgW"
    if unit in ("SM", "ATT", "FUSED"):
        return "R1_lgE", "W1_lgE"
    if unit == "DMA":
        return "R2_dma", "WP_dma"
    if unit == "COLL":
        if op == "ROW_GATHER":
            return "P2_coll", "W2_coll"
        return "R0_lgW", "W0_lgW"
    if unit == "IDX":
        return ("R1_lgE", "W1_lgE") if IDX_PORT == "lgE" else ("P0_idx", "P0_idx")
    if unit == "ARGMAX":
        return "P1_argmax", "P1_argmax"
    return None, None


def build_schedule():
    from throughput_budget import build as B
    from hgi_sim import timing as T
    from hgi_sim import ds_native_timing as DT
    d, recs = DT.load(B.PROG)
    recs = T.rebuild_waits(recs)
    rg = {}
    for x in json.loads(B.RUN.read_text())["results"]:
        for s_ in x.get("row_gather") or []:
            rg[x["layer"]] = s_
    DT.apply_dyn_counts(recs, rg)
    cf = DT.NativeCost(d["ops"], recs, row_gather=rg)
    s = T.schedule(recs, DT.POS, "S2", cost_fn=cf)
    return T, DT, recs, s


def sectors(T, d, dyn, L):
    base, n, m, st, ist = T.eff(d, dyn, L)
    out, seen = [], set()
    for o in range(max(m, 1)):
        rb = base + o * st
        if ist == 1:
            lo, hi = rb >> 3, (rb + max(n, 1) - 1) >> 3
            it = range(lo, hi + 1)
        else:
            it = ((rb + i * ist) >> 3 for i in range(max(n, 1)))
        for sct in it:
            sct %= NSEC
            if sct not in seen:
                seen.add(sct)
                out.append(sct)
    return out


def gen(out: Path):
    T, DT, recs, s = build_schedule()
    dyn = T.Dyn(DT.POS, 0)
    out.mkdir(parents=True, exist_ok=True)
    rec_tab = []                                   # global record id -> manifest row
    per = {n: [] for n, _ in STREAMS}              # stream -> [(rid, we, sector)]
    for i, (k, L, L1) in enumerate(s["ex"]):
        r = recs[k]
        dyn.v[4], dyn.v[8] = L, L1
        rs, ws = ports_of(r.unit, r.op)
        if rs is None:
            continue
        rd, wr = [], []
        for kk, d in r.desc.items():
            if d.space != "VM":
                continue
            (wr if kk in ("O", "R") else rd).extend(sectors(T, d, dyn, L))
        if not rd and not wr:
            continue
        rid = len(rec_tab)
        rec_tab.append(dict(rid=rid, op=f"{r.unit}.{r.op}", tag=r.tag, layer=L, start=int(round(s["start"][i])),
                            end=int(round(s["end"][i])), rd=len(rd), wr=len(wr), rs=rs, ws=ws))
        for sct in rd:
            per[rs].append((rid, 0, sct))
        for sct in wr:
            per[ws].append((rid, 1, sct))
    # wide streams: per-lane lists (lane = bank = sector[4:0]), record order; packet streams: one list
    cfg = [f"// generated by tools/hgi_vm_ports_trace.py: DS AR 1M token VM traffic on the S2 schedule",
           f"localparam integer NREC = {len(rec_tab)};"]
    for name, kind in STREAMS:
        ents = per[name]
        if kind in ("r", "w", "d"):
            lanes = [[] for _ in range(LANES)]
            for rid, we, sct in ents:
                lanes[sct % LANES].append((rid, sct))
            flat, offs = [], []
            for l in range(LANES):
                offs.append(len(flat))
                flat.extend(lanes[l])
            offs.append(len(flat))
            with open(out / f"{name}.hex", "w") as f:
                for rid, sct in flat or [(0, 0)]:
                    f.write(f"{(rid << 15) | sct:09x}\n")
            with open(out / f"{name}_off.hex", "w") as f:
                for o in offs:
                    f.write(f"{o:08x}\n")
            cfg.append(f"localparam integer N_{name} = {max(len(flat), 1)};")
        else:
            with open(out / f"{name}.hex", "w") as f:
                for rid, we, sct in ents or [(0, 0, 0)]:
                    f.write(f"{(rid << 16) | (we << 15) | sct:09x}\n")
            cfg.append(f"localparam integer N_{name} = {max(len(ents), 1)}; localparam integer E_{name} = {len(ents)};")
    with open(out / "rec.hex", "w") as f:
        for r in rec_tab:
            f.write(f"{r['start']:08x}\n")
    with open(out / "rec_n.hex", "w") as f:
        for r in rec_tab:
            f.write(f"{r['rd'] + r['wr']:08x}\n")
    (out / "cfg.svh").write_text("\n".join(cfg) + "\n")
    man = dict(schema="hgi_vm_ports_trace/1", S2_cycles=round(s["total_cycles"], 1), records=rec_tab,
               streams={n: len(per[n]) for n, _ in STREAMS})
    (out / "manifest.json").write_text(json.dumps(man))
    print(json.dumps(dict(records=len(rec_tab), S2=man["S2_cycles"], streams=man["streams"])))


def report(trace: Path, runlog: Path, out: Path | None):
    man = json.loads((trace / "manifest.json").read_text())
    meas = {}
    summary = {}
    for line in runlog.read_text(errors="replace").splitlines():
        p = line.split()
        if p[:1] == ["REC"] and len(p) >= 3:
            meas[int(p[1])] = int(p[2])
        elif p[:1] == ["HGI_VM_PORTS"]:
            summary["verdict"] = " ".join(p[1:])
        elif p[:1] == ["PKT_RTT"]:
            summary["packet_rtt"] = " ".join(p[1:])
    by = collections.defaultdict(lambda: dict(n=0, priced=0, served=0, late=0, worst=0.0))
    tp = ts = 0
    missing = 0
    for r in man["records"]:
        if r["rid"] not in meas:
            missing += 1
            continue
        pr = max(r["end"] - r["start"], 1)
        sv = max(meas[r["rid"]] - r["start"], 0)
        b = by[r["op"]]
        b["n"] += 1
        b["priced"] += pr
        b["served"] += max(sv, pr)
        b["late"] += sv > pr
        b["worst"] = max(b["worst"], sv / pr)
        tp += pr
        ts += max(sv, pr)
    ops = {k: dict(v, ratio=round(v["served"] / v["priced"], 4), worst=round(v["worst"], 3)) for k, v in by.items()}
    rep = dict(schema="hgi_vm_ports_report/1", element="ot_hgi_vm_unit", op="VM.PORTS", model="DS AR 1M (HBM)",
               metric="sum over VM-touching records of max(VM service time, priced time) / sum of priced time "
                      "(a record's VM traffic offered from its S2 start on its production port)",
               ratio=round(ts / tp, 4) if tp else None, records=len(man["records"]), missing=missing,
               priced_cycles=tp, served_cycles=ts, S2_cycles=man["S2_cycles"], ops=ops, **summary)
    js = json.dumps(rep, indent=1)
    if out:
        out.write_text(js + "\n")
    print(js)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    ap.add_argument("--report", nargs=2, metavar=("TRACE", "RUNLOG"))
    ap.add_argument("--json")
    ap.add_argument("--idx-port", choices=("packet", "lgE"), default="packet")
    a = ap.parse_args()
    global IDX_PORT
    IDX_PORT = a.idx_port
    if a.out:
        gen(Path(a.out))
    if a.report:
        report(Path(a.report[0]), Path(a.report[1]), Path(a.json) if a.json else None)


if __name__ == "__main__":
    main()
