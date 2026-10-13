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
import sys
import math
import os
import sys
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
    consumer_wpc=64,                                    # a consumer reads 64 words / cycle (SPEC 5.0)
    # SPEC v0.5 (main 87eead465) die address map, decoded by RANGE: slice addr[17:16] below repl_base, REPL mirror,
    # HC weight aperture moved to 294,912..360,447; the simulated / image address space is spec_words
    repl_base=262144, repl_w=32768, hcap_base=294912, hcap_w=65536, spec_words=360448,
)
READ_OPS = ("A", "B", "C", "I")


def params(p: Path | None = None) -> dict:
    out = dict(DEFAULT)
    for f in ([p] if p else []) + ([SPEC_PARAMS] if SPEC_PARAMS.exists() else []):
        out.update(json.loads(Path(f).read_text()))
        out["source"] = str(f)
    return out


def slice_of(a: np.ndarray, P: dict, smap: np.ndarray | None = None) -> np.ndarray:
    """slice of every VM word address; -1 = mirror (local everywhere). With a B2 vector's slice map (b2/slice.npy: per
    LOGICAL word, slice 0..3, -1 REPL mirror, -2 untouched) the compiler's placement decides, else the address bits."""
    s = np.where(a < VM_WORDS, a // P["slice_words"], (a // P["aperture_stripe_words"]) % P["nclust"]).astype(np.int64)
    s = np.minimum(s, P["nclust"] - 1)
    if smap is not None:
        lo = a < VM_WORDS
        m = smap[a[lo]].astype(np.int64)
        s[lo] = np.where(m < 0, -1, m)
    for lo, hi in P["mirror"]:
        s[(a >= lo) & (a < hi)] = -1
    return s


def spec_slice_of(a: np.ndarray, P: dict) -> np.ndarray:
    """slice of SPEC v0.5 die addresses (the compiler's vm*_spec.bin / sub-descriptor 'spec' fields), range decode:
    slice addr[17:16] below REPL_BASE, -1 = REPL mirror (local everywhere), HC aperture = STRIPE4 by sector (fed from
    the local slice, vmap_<q>); any other address raises (a fault in RTL)"""
    a = np.asarray(a, np.int64)
    rb, hb = P["repl_base"], P["hcap_base"]
    rep = (a >= rb) & (a < rb + P["repl_w"])
    hc = (a >= hb) & (a < hb + P["hcap_w"])
    lo = (a >= 0) & (a < rb)
    if not np.all(lo | rep | hc):
        raise ValueError("SPEC v0.5 address outside slice / REPL / HC aperture")
    s = np.where(lo, (a >> 16) & 3, -1)
    return np.where(hc, ((a - hb) // P["aperture_stripe_words"]) % P["nclust"], s).astype(np.int64)


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


def lag(H: int, lead: int, R: int, b: float, c: float) -> float:
    """consumer stall (cycles) reading `lead` local words then R remote words in order at c words/cycle, the remote ones
    arriving after H hop cycles at b words/cycle (cut-through): max over remote words of t_arrive - t_need, >= 0"""
    if R <= 0:
        return 0.0
    return max(0.0, H + 1 / b - lead / c, H + R / b - (lead + R - 1) / c)


def _arrivals(t0: float, H: float, n: int, b: float) -> np.ndarray:
    """cut-through stream of n words leaving at t0: word i lands at t0 + H + (i + 1) / b"""
    return t0 + H + (np.arange(n) + 1) / b


def record_traffic(r, waddr: np.ndarray, P: dict, smap: np.ndarray | None = None, avail: np.ndarray | None = None) -> dict:
    """one record's cross-cluster traffic and EXPOSED cycles (SPEC 5.0: sum of max(0, t_arrive - t_need)).

    Timing anchors on the vector's die schedule (s2_start / s2_end per record).  PULL traffic (a consumer reading a
    remote slice, a split record's operand outside every participant) is charged at the consumer from its start, local
    words read first.  PUSH traffic (a remote write, a mirror-window broadcast, a COLL result on the star) leaves the
    producer at its s2_end and is charged at the record that actually READS the word, at the time that consumer
    reaches it (`avail`: per logical word, the cycle it lands; updated here) -- not at the producer as if the very next
    record consumed it.  `exposed_producer` keeps the old producer-side figure for comparison."""
    n = P["nclust"]
    ra = reads(r)
    r_sl, w_sl = slice_of(ra, P, smap), slice_of(waddr, P, smap)
    home = place(r, w_sl, r_sl, P)
    pair = defaultdict(int)                          # (src slice, dst cluster) -> words over the ring
    bcast = 0
    split_rd = None
    if len(home) > 1:
        # a split record: every participant needs every non-mirror read word; one broadcast per word (tree)
        # (with the compiler's slice map a participant reads its own slice's share locally: only words in a slice
        # outside every participant cross)
        split_rd = ((r_sl >= 0) & ~np.isin(r_sl, home)) if smap is not None else (r_sl >= 0)
        bcast += int(split_rd.sum())
        for s in w_sl[(w_sl >= 0) & ~np.isin(w_sl, home)]:
            pair[(int(s), home[0])] += 1             # a write outside every participant's slice
    else:
        h = home[0]
        for s, c in zip(*np.unique(r_sl[(r_sl >= 0) & (r_sl != h)], return_counts=True)):
            pair[(int(s), h)] += int(c)              # remote read: slice s -> cluster h
        if r["unit"] != "COLL":                      # a collective's result rides the COLL star (bcast below), not the ring
            for s, c in zip(*np.unique(w_sl[(w_sl >= 0) & (w_sl != h)], return_counts=True)):
                pair[(h, int(s))] += int(c)          # remote write: cluster h -> slice s
    mirror_w = int((w_sl < 0).sum())
    if r.get("b2mode") in ("REPLX", "QSPLIT"):
        mirror_w = 0                                 # every cluster writes / loads its own mirror copy: no broadcast
    bcast += mirror_w                                # a mirror-window write is broadcast to every slice
    coll_res = r["unit"] == "COLL" and len(home) == 1
    if coll_res:
        bcast += int((w_sl >= 0).sum())              # the collective's result broadcast (tree) to every cluster
    wpl = P["ring_link_bits"] // 32
    ring = max((P["ring_hop_cycles"] * hops(s, d, n) + math.ceil(w / wpl) for (s, d), w in pair.items()), default=0)
    bc = (P["ring_hop_cycles"] * P["bcast_hops"] + math.ceil(bcast / (P["bcast_bits"] // 32))) if bcast else 0
    c, bw, Hb = P["consumer_wpc"], P["bcast_bits"] // 32, P["ring_hop_cycles"] * P["bcast_hops"]

    # ---- old producer-side figure (each remote write / broadcast charged as if the next record read it at once)
    exp_old = 0.0
    if len(home) == 1:
        h = home[0]
        loc = int(((r_sl < 0) | (r_sl == h)).sum())
        for s in sorted(set(int(x) for x in r_sl[(r_sl >= 0) & (r_sl != h)])):
            exp_old = max(exp_old, lag(P["ring_hop_cycles"] * hops(s, h, n), loc, int((r_sl == s).sum()), wpl, c))
    for s, d in pair:
        if len(home) > 1 or s == home[0]:
            exp_old = max(exp_old, lag(P["ring_hop_cycles"] * hops(s, d, n), 0, pair[(s, d)], wpl, c))
    if bcast:
        nb = mirror_w + (int((w_sl >= 0).sum()) if coll_res else 0)
        nb = nb or bcast
        for q in range(n):
            lead = nb // len(home) if q in home else 0
            exp_old = max(exp_old, lag(Hb, lead, nb - lead, bw, c))

    # ---- SPEC 5.0 accounting on the die schedule
    T0 = float(r.get("s2_start", 0.0))
    T1 = float(r.get("s2_end", T0 + float(r.get("cost", 0.0))))
    lo = ra < VM_WORDS
    pend = np.full(ra.size, -np.inf)
    if avail is not None:
        pend[lo] = avail[ra[lo]]                     # landing cycle of words still in flight from a PUSH
    ex_pull, ex_push = 0.0, 0.0
    if len(home) == 1:                               # PULL: remote operand reads of a single-home record, local first
        h = home[0]
        loc = int(((r_sl < 0) | (r_sl == h)).sum())
        for s in sorted(set(int(x) for x in r_sl[(r_sl >= 0) & (r_sl != h)])):
            m = r_sl == s
            late = max(0.0, float(pend[m].max()) - T0)   # a pulled word not yet landed at its own slice
            ex_pull = max(ex_pull, lag(P["ring_hop_cycles"] * hops(s, h, n) + late, loc, int(m.sum()), wpl, c))
    elif split_rd is not None and split_rd.any():    # PULL: split record's operand outside every participant (tree)
        R = int(split_rd.sum())
        lead = int((~split_rd).sum()) // len(home)
        late = max(0.0, float(pend[split_rd].max()) - T0)
        ex_pull = lag(Hb + late, lead, R, bw, c)
    # PUSH consumption: words this record reads locally that an earlier PUSH has not landed yet; each participant reads
    # its local words (its slice + mirror) in operand order at c words / cycle from T0
    if np.isfinite(pend).any():
        for q in home:
            mq = (r_sl < 0) | (r_sl == q)
            idx = np.nonzero(mq)[0]
            if idx.size == 0:
                continue
            p = pend[idx]
            f = np.isfinite(p)
            if f.any():
                need = T0 + np.arange(idx.size)[f] / c
                ex_push = max(ex_push, float((p[f] - need).max()))
    ex = max(ex_pull, ex_push, 0.0)
    # ---- this record's writes, COMMITTED at T1 (the caller applies them once the schedule passes T1, so a record that
    # overlaps this one never sees them): local ones are valid at T1 (the schedule orders local deps); pushes land later
    commit = []
    if avail is not None:
        wl = waddr[waddr < VM_WORDS]
        wsl = w_sl[waddr < VM_WORDS]
        commit.append((wl, np.full(wl.size, -np.inf)))
        if len(home) > 1:
            out = (wsl >= 0) & ~np.isin(wsl, home)
            for s in sorted(set(int(x) for x in wsl[out])):
                m = np.nonzero(wsl == s)[0]
                commit.append((wl[m], _arrivals(T1, P["ring_hop_cycles"] * hops(s, home[0], n), m.size, wpl)))
        else:
            h = home[0]
            if r["unit"] != "COLL":
                for s in sorted(set(int(x) for x in wsl[(wsl >= 0) & (wsl != h)])):
                    m = np.nonzero(wsl == s)[0]
                    commit.append((wl[m], _arrivals(T1, P["ring_hop_cycles"] * hops(h, s, n), m.size, wpl)))
        bmask = np.zeros(wl.size, bool)
        if mirror_w:
            bmask |= wsl < 0
        if coll_res:
            bmask |= wsl >= 0
        if bmask.any():
            m = np.nonzero(bmask)[0]
            commit.append((wl[m], _arrivals(T1, Hb, m.size, bw)))
    return dict(k=r["k"], unit=r["unit"], op=r["op"], tag=r.get("tag", ""), home=home, read_words=int(ra.size),
                write_words=int(waddr.size), remote_words=int(sum(pair.values())), bcast_words=bcast,
                ring_cycles=ring, bcast_cycles=bc, cycles=ring + bc, exposed=round(ex, 1),
                exposed_pull=round(ex_pull, 1), exposed_push=round(max(ex_push, 0.0), 1),
                exposed_producer=round(exp_old, 1), s2_start=T0, s2_end=T1, cost=float(r.get("cost", 0)),
                derived=r.get("cluster") is None, _commit=(T1, commit))


def traffic(vec: Path, P: dict) -> dict:
    meta = json.loads((vec / "meta.json").read_text())
    vmw = np.frombuffer((vec / "vmw.bin").read_bytes(), "<u4").reshape(-1, 2)[:, 0].astype(np.int64)
    smp = vec / "b2" / "slice.npy"
    smap = np.load(smp) if smp.exists() else None
    spi = vec / "b2" / "vm0_spec.bin"
    if spi.exists() and spi.stat().st_size // 4 != P["spec_words"]:
        print(f"WARNING {spi}: {spi.stat().st_size // 4} words, SPEC v0.5 die image is {P['spec_words']} (pre-v0.5 "
              f"compiler; traffic uses logical addresses + slice.npy, unaffected)", file=sys.stderr)
    avail = np.full(VM_WORDS, -np.inf)               # per logical word: cycle a PUSH lands (-inf: valid)
    recs = sorted(meta["records"], key=lambda r: (float(r.get("s2_start", 0.0)), r["k"]))   # producers before consumers
    rows, queue = [], []
    for r in recs:                                   # a write becomes visible once the schedule reaches its s2_end
        T0 = float(r.get("s2_start", 0.0))
        due = sorted((q for q in queue if q[0] <= T0 + 1e-6), key=lambda q: q[0])
        queue = [q for q in queue if q[0] > T0 + 1e-6]
        for _, cm in due:
            for ad, t in cm:
                avail[ad] = t
        x = record_traffic(r, vmw[r["vm_off"]:r["vm_off"] + r["vm_n"]], P, smap, avail)
        queue.append(x.pop("_commit"))
        rows.append(x)
    rows.sort(key=lambda x: x["k"])
    model = "qwen" if "qwen" in str(meta.get("model", "")).lower() else "ds"
    budget = P["budget_cycles_per_layer"][model]
    per = defaultdict(lambda: dict(records=0, remote_records=0, remote_words=0, bcast_words=0, cycles=0, exposed=0.0))
    for x in rows:
        p = per[f"{x['unit']}.{x['op']}"]
        p["records"] += 1
        p["remote_records"] += int(x["cycles"] > 0)
        p["remote_words"] += x["remote_words"]
        p["bcast_words"] += x["bcast_words"]
        p["cycles"] += x["cycles"]
        p["exposed"] = round(p["exposed"] + x["exposed"], 1)
    exposed = round(sum(x["exposed"] for x in rows), 1)
    exposed_producer = round(sum(x["exposed_producer"] for x in rows), 1)
    tot = sum(x["cycles"] for x in rows)
    b2vec = any(not x["derived"] for x in rows)
    out = dict(schema="opentallas.hgi_e2e.b2_traffic.v1", vector=str(vec), model=model, layer=meta.get("layer"),
               position=meta.get("position"), rank=meta.get("rank"), params=P,
               placement="B2 vector (compiler cluster field)" if b2vec else
               "OLD-VM: derived from the current allocator's addresses (not the B2 allocator) -- harness proof only",
               records=len(rows), remote_records=sum(int(x["cycles"] > 0) for x in rows),
               remote_words=sum(x["remote_words"] for x in rows), bcast_words=sum(x["bcast_words"] for x in rows),
               slice_map=str(smp) if smap is not None else None,
               ring_cycles_serial=tot, exposed_cycles=exposed,
               accounting="SPEC 5.0: arrival-after-need on the vector's s2 schedule (push charged at its reader)",
               exposed_cycles_producer_side=exposed_producer, budget_cycles_per_layer=budget,
               within_budget=exposed <= budget, ratio=round(exposed / budget, 3) if budget else None,
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
              f"{o['remote_words']} ring words + {o['bcast_words']} bcast words, {o['ring_cycles_serial']} cycles serial, "
              f"{o['exposed_cycles']} EXPOSED (producer-side {o['exposed_cycles_producer_side']}) vs budget {o['budget_cycles_per_layer']} ({o['placement'].split(':')[0]})")


if __name__ == "__main__":
    main()
