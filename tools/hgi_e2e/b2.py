"""B2 die (4 clusters, distributed VM) layer of the native die e2e harness: slice map, cross-cluster traffic, ring cycles.

    python3 tools/hgi_e2e/b2.py traffic VEC_DIR [--params P.json] [--out b2_traffic.json]   -> VEC_DIR/b2.txt + report

B2 (owner 2026-10-12; results/arch/hbm_die_phy_study_1012/STUDY.md section 4, SPEC results/arch/hbm_b2_1012/SPEC.md when it
lands): the HBM die is 4 clusters, one per HBM stack, each with a LOCAL VM slice; VM stays ONE compiler address space
(HGI-1 unchanged), the word address selects the slice (high bits) or the mirror window; clusters exchange over a slice
ring (2 links across any cut, 2,048 b each way) and a collective broadcast tree (2 x 1,088 b).

Modes (tb_hgi_e2e B2 parameter):
  B2 0  legacy single VM, no accounting.
  B2 1  OLD-VM mode (until B2 RTL lands): the central VM model, but every record is placed on a home cluster (or split
        over several, an SM / SU record whose writes span slices) and every VM word it touches is classed local / remote /
        mirror.  Static traffic (this script, from the vector's operand descriptors + golden write set) gives each record's
        ring / broadcast words and cycles; the DPI counts what the REAL units actually read / write per slice (dynamic,
        `b2_dyn.json`) and, with +B2_RING, a stub record's hold time includes its ring cycles.
  B2 2  native B2 RTL (units on their local slice ports): reserved for when the cluster RTL lands; then the cycles are
        measured, not added.
Record placement: a B2 vector (compiler stream exporter, results/rtl/hbm_b2_1012/) carries `cluster` (int, or a list for a
split record) on each meta.json record; an old vector does not, and the home is derived (owner computes: the slices
of its golden writes; split if an SM/SU/COLL record writes several slices; else the majority read slice; CTL/DMA.FENCE 0).
"""
from __future__ import annotations

import argparse
import json
import math
import os
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

VM_WORDS = 1 << 18
_P = Path(__file__).resolve().parents
R = _P[2] if len(_P) > 2 else _P[-1]
SPEC_PARAMS = R / "results/arch/hbm_b2_1012/b2_params.json"

# Provisional (PHY study f6467cb82); SPEC_PARAMS overrides key by key once the B2 lead publishes it.
DEFAULT = dict(
    source="results/arch/hbm_die_phy_study_1012/STUDY.md (provisional until results/arch/hbm_b2_1012/SPEC.md)",
    nclust=4, slice_words=65536, mirror=[],             # mirror window(s) [lo, hi) word ranges: local in every slice
    aperture_stripe_words=8,                            # HC weight aperture (>= 2^18): STRIPE4 by 8-word sector
    ring_link_bits=2048, ring_hop_cycles=16,            # one link each way per neighbour pair; 2x2 ring, <= 2 hops
    bcast_bits=1024, bcast_hops=2,                      # broadcast tree 2 x 1,088 b (1,024 data); depth 2 hops
    # budgets: B2 worst +11.6k cycles / DS token (40 layers) -> 290 / layer; Qwen >= 943 vs 945.5 tok/s -> 3,365 / token
    # (36 layers) -> 93 / layer (tok_model.py; SPEC.md replaces these)
    budget_cycles_per_layer=dict(ds=290, qwen=93),
)
READ_OPS = ("A", "B", "C", "I")


def params(p: Path | None = None) -> dict:
    out = dict(DEFAULT)
    for f in ([p] if p else []) + ([SPEC_PARAMS] if SPEC_PARAMS.exists() else []):
        out.update(json.loads(Path(f).read_text()))
        out["source"] = str(f)
    return out


def slice_of(a: np.ndarray, P: dict) -> np.ndarray:
    """slice of every VM word address; -1 = mirror (local everywhere)"""
    s = np.where(a < VM_WORDS, a // P["slice_words"], (a // P["aperture_stripe_words"]) % P["nclust"]).astype(np.int64)
    s = np.minimum(s, P["nclust"] - 1)
    for lo, hi in P["mirror"]:
        s[(a >= lo) & (a < hi)] = -1
    return s


def hops(a: int, b: int, n: int) -> int:
    d = abs(a - b)
    return min(d, n - d)


def op_addrs(e) -> np.ndarray:
    b, n, m, st, ist = e[:5]
    o, i = np.meshgrid(np.arange(max(m, 1)), np.arange(max(n, 1)), indexing="ij")
    return (b + o * st + i * ist).reshape(-1).astype(np.int64)


def reads(r) -> np.ndarray:
    xs = []
    for nm, e in r["eff"].items():
        if e[5] != "VM":
            continue
        if nm in READ_OPS or (nm == "D" and (r["unit"] == "SU" or (r["unit"] == "IDX"))):
            xs.append(op_addrs(e))
    return np.unique(np.concatenate(xs)) if xs else np.zeros(0, np.int64)


def place(r, w_sl: np.ndarray, r_sl: np.ndarray, P: dict) -> list[int]:
    c = r.get("cluster")
    if c is not None:
        return [int(x) for x in (c if isinstance(c, list) else [c])]
    if r["unit"] == "CTL" or (r["unit"], r["op"]) == ("DMA", "FENCE"):
        return [0]
    ws = sorted(set(int(x) for x in w_sl if x >= 0))
    if len(ws) > 1 and r["unit"] in ("SM", "SU", "COLL", "ATT", "SFU"):
        return ws                                    # split: each cluster computes its own slice of the output
    if ws:
        return [Counter(int(x) for x in w_sl if x >= 0).most_common(1)[0][0]]
    rs = [int(x) for x in r_sl if x >= 0]
    return [Counter(rs).most_common(1)[0][0]] if rs else [0]


def record_traffic(r, waddr: np.ndarray, P: dict) -> dict:
    n = P["nclust"]
    ra = reads(r)
    r_sl, w_sl = slice_of(ra, P), slice_of(waddr, P)
    home = place(r, w_sl, r_sl, P)
    pair = defaultdict(int)                          # (src slice, dst cluster) -> words over the ring
    bcast = 0
    if len(home) > 1:
        # a split record: every participant needs every non-mirror read word; one broadcast per word (tree)
        bcast += int((r_sl >= 0).sum())
        for s in w_sl[(w_sl >= 0) & ~np.isin(w_sl, home)]:
            pair[(int(s), home[0])] += 1             # a write outside every participant's slice
    else:
        h = home[0]
        for s, c in zip(*np.unique(r_sl[(r_sl >= 0) & (r_sl != h)], return_counts=True)):
            pair[(int(s), h)] += int(c)              # remote read: slice s -> cluster h
        for s, c in zip(*np.unique(w_sl[(w_sl >= 0) & (w_sl != h)], return_counts=True)):
            pair[(h, int(s))] += int(c)              # remote write: cluster h -> slice s
    mirror_w = int((w_sl < 0).sum())
    bcast += mirror_w                                # a mirror-window write is broadcast to every slice
    if r["unit"] == "COLL" and len(home) == 1:
        bcast += int((w_sl >= 0).sum())              # the collective's result broadcast (tree) to every cluster
    wpl = P["ring_link_bits"] // 32
    ring = max((P["ring_hop_cycles"] * hops(s, d, n) + math.ceil(w / wpl) for (s, d), w in pair.items()), default=0)
    bc = (P["ring_hop_cycles"] * P["bcast_hops"] + math.ceil(bcast / (P["bcast_bits"] // 32))) if bcast else 0
    return dict(k=r["k"], unit=r["unit"], op=r["op"], tag=r.get("tag", ""), home=home, read_words=int(ra.size),
                write_words=int(waddr.size), remote_words=int(sum(pair.values())), bcast_words=bcast,
                ring_cycles=ring, bcast_cycles=bc, cycles=ring + bc, cost=float(r.get("cost", 0)),
                derived=r.get("cluster") is None)


def traffic(vec: Path, P: dict) -> dict:
    meta = json.loads((vec / "meta.json").read_text())
    vmw = np.frombuffer((vec / "vmw.bin").read_bytes(), "<u4").reshape(-1, 2)[:, 0].astype(np.int64)
    rows = [record_traffic(r, vmw[r["vm_off"]:r["vm_off"] + r["vm_n"]], P) for r in meta["records"]]
    model = "qwen" if "qwen" in str(meta.get("model", "")).lower() else "ds"
    budget = P["budget_cycles_per_layer"][model]
    per = defaultdict(lambda: dict(records=0, remote_records=0, remote_words=0, bcast_words=0, cycles=0))
    for x in rows:
        p = per[f"{x['unit']}.{x['op']}"]
        p["records"] += 1
        p["remote_records"] += int(x["cycles"] > 0)
        p["remote_words"] += x["remote_words"]
        p["bcast_words"] += x["bcast_words"]
        p["cycles"] += x["cycles"]
    tot = sum(x["cycles"] for x in rows)
    b2vec = any(not x["derived"] for x in rows)
    out = dict(schema="opentallas.hgi_e2e.b2_traffic.v1", vector=str(vec), model=model, layer=meta.get("layer"),
               position=meta.get("position"), rank=meta.get("rank"), params=P,
               placement="B2 vector (compiler cluster field)" if b2vec else
               "OLD-VM: derived from the current allocator's addresses (not the B2 allocator) -- harness proof only",
               records=len(rows), remote_records=sum(int(x["cycles"] > 0) for x in rows),
               remote_words=sum(x["remote_words"] for x in rows), bcast_words=sum(x["bcast_words"] for x in rows),
               ring_cycles_serial=tot, budget_cycles_per_layer=budget,
               within_budget=tot <= budget, ratio=round(tot / budget, 3) if budget else None,
               sim_cost_cycles=round(sum(x["cost"] for x in rows), 1),
               per_op=dict(sorted(per.items())), rows=rows)
    tmp = vec / f".b2.txt.{os.getpid()}"                # atomic: concurrent runs of one vector share b2.txt
    tmp.write_text("".join(f"{x['k']} {sum(1 << h for h in x['home'])} {x['cycles']}\n" for x in rows))
    os.replace(tmp, vec / "b2.txt")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sp = ap.add_subparsers(dest="cmd", required=True)
    t = sp.add_parser("traffic"); t.add_argument("vec", type=Path); t.add_argument("--params", type=Path)
    t.add_argument("--out", type=Path)
    a = ap.parse_args()
    if a.cmd == "traffic":
        o = traffic(a.vec, params(a.params))
        txt = json.dumps(o, indent=1)
        (a.out or a.vec / "b2_traffic.json").write_text(txt + "\n")
        print(f"B2 {o['model']} L{o['layer']}: {o['remote_records']}/{o['records']} records cross clusters, "
              f"{o['remote_words']} ring words + {o['bcast_words']} bcast words, {o['ring_cycles_serial']} cycles serial "
              f"vs budget {o['budget_cycles_per_layer']} ({o['placement'].split(':')[0]})")


if __name__ == "__main__":
    main()
