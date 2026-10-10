#!/usr/bin/env python3
"""Cycle model of the HGI-1 VM (VM-512, hgi-1010/f): DMA format expansion beside the banks, edge-scheduled wide lanes.

Organisation modelled (docs/HBM_GENERIC_INTERFACE.md 2.4, VM microarchitecture):
  * NB = 512 banks, sector s -> bank s[8:0], row s[SB-1:9]; each bank one 1R1W 312-bit row (8 FP32 words, (39,32)
    SECDED a word) = 2 ot_sram_1r1w_128x256 macros.  A read and a write to one bank in one cycle never conflict.
  * 128 tiles; tile t = banks 4t .. 4t+3 (sectors 4t' .. 4t'+3 of one 512-sector block).  DMA lane t feeds tile t
    only: one RAW source sector a cycle, expanded beside the banks to e = 4 / esz destination sectors (FP32/U32 1,
    BF16 2, FP8/INT8/UE8M0 4).  A raw sector whose destinations straddle two tiles is sent to both (two lane beats).
  * Wide lanes (32 a group; lane b serves sectors with s[4:0] = b, i.e. banks b + 32 j): read groups and write groups
    are scheduled at the VM edge: in a cycle, the requests of lane b launched by all groups (and packets) target
    distinct banks (s[8:5]); a loser waits in its lane queue (reader / drain back-pressure).  Everything launched
    reaches its bank after a fixed latency, so lanes see in-order fixed-latency service.
  * Bank write priority: wide write groups and packet writes (edge-scheduled) > DMA.  A DMA lane beat whose target
    banks include one taken this cycle waits in the tile's 2-entry skid (DMA back-pressure stays local to the tile).

HBM delivery: 4 stacks x 32 PCs, sector s from PC s mod 128, each PC returning at most one sector a cycle with the
probability that makes the aggregate the sustained 3,166.7 B/cycle (3.80 TB/s at 1.2 GHz); the front keeps a per-tile
queue (FQ) and stalls a PC whose next sector's tile queue is full.  Output: sustained DMA source B/cycle and its
fraction of 3,166.7, plus the wide-lane service rates, for each format, with and without concurrent drain/stage traffic,
and the real token programs' DMA.LOAD lists (tools/hgi_vm/vm_census.py).
"""
import argparse, json, random, math

HZ = 1.2e9
HBM_BPC = 3.80e12 / HZ                 # 3,166.7 B/cycle sustained (owner calibration)
NB, NT, LANES = 512, 128, 32
E = {"FP32": 1, "U32": 1, "BF16": 2, "FP8E4M3": 4, "INT8": 4, "UE8M0": 4, "FP4E2M1": 8}
ESZ = {"FP32": 4, "U32": 4, "BF16": 2, "FP8E4M3": 1, "INT8": 1, "UE8M0": 1, "FP4E2M1": 0.5}


def tiles_of(dsec0, e):
    """Lane beats of one raw sector whose first destination sector is dsec0: [(tile, banks)]."""
    out = {}
    for k in range(e):
        d = dsec0 + k
        out.setdefault((d >> 2) % NT, set()).add(d % NB)
    return list(out.items())


def run(fmt, n_raw, dbase=0, wgroups=0, rgroups=0, packets=0, fq=4, nb=NB, seed=1, bq=0, lockstep=False):
    """Simulate one DMA.LOAD of n_raw source sectors in fmt into VM sector dbase (+ concurrent lane traffic).
    bq = 0: a tile takes a whole lane beat only when all its target banks are free this cycle;
    bq > 0: the tile splits each beat into per-bank chunk queues of depth bq (accepted when every target queue has
    room) and each bank drains its queue whenever its write port is free (the RTL organisation).
    lockstep: all lanes of a wide group walk together (a record's stage / drain); else independent random phases.
    Returns cycles from the first PC delivery to the last bank write, and the lane service counts."""
    rng = random.Random(seed)
    e = E[fmt]
    p = min(1.0, HBM_BPC / 32 / 128)               # per-PC delivery probability
    # raw sector i is delivered by PC i mod 128 in order per PC
    pc_next = [i for i in range(128)]
    tq = [[] for _ in range(NT)]                   # front per-tile queue of (banks)
    skid = [[] for _ in range(NT)]                 # tile 2-entry skid
    delivered = written = 0
    beats_total = 0
    cyc = 0
    # wide groups walk long spans: group g lane b next sector index k (sector = base_g + 32 k + b)
    wg_base = [rng.randrange(0, 1 << 15) for _ in range(wgroups)]
    rg_base = [rng.randrange(0, 1 << 15) for _ in range(rgroups)]
    ph = (lambda: 0) if lockstep else (lambda: rng.randrange(16))
    wk = [[ph() for _ in range(LANES)] for _ in range(wgroups)]
    rk = [[ph() for _ in range(LANES)] for _ in range(rgroups)]
    bqs = [[] for _ in range(nb)]                  # per-bank DMA chunk queues (bq > 0)
    w_served = [0] * wgroups
    r_served = [0] * rgroups
    while written < beats_total or delivered < n_raw or cyc == 0 or any(bqs):
        cyc += 1
        if cyc > 50 * n_raw + 1000:
            raise RuntimeError("no progress")
        # ---- edge scheduling of the wide lanes (lane b: distinct s[8:5] per cycle, groups in priority order)
        wbank = set()
        for lb in range(LANES):
            used = set()
            for g in range(wgroups):
                s = wg_base[g] + 32 * wk[g][lb] + lb
                col = (s >> 5) & 15
                if col in used:
                    continue
                used.add(col)
                wk[g][lb] += 1
                w_served[g] += 1
                wbank.add(s % nb)
            used = set()
            for g in range(rgroups):
                s = rg_base[g] + 32 * rk[g][lb] + lb
                col = (s >> 5) & 15
                if col in used:
                    continue
                used.add(col)
                rk[g][lb] += 1
                r_served[g] += 1
        # packet writes (random sectors), one a client a cycle, also above DMA
        for _ in range(packets):
            wbank.add(rng.randrange(nb))
        # ---- tiles: one DMA beat a tile a cycle, unless a target bank is taken
        for t in range(NT if bq else 0):
            for b in range(4 * t, 4 * t + 4):
                if bqs[b] and b not in wbank:
                    bqs[b].pop(0)
            if skid[t]:
                banks = skid[t][0]
                if all(len(bqs[b]) < bq for b in banks):
                    skid[t].pop(0)
                    for b in banks:
                        bqs[b].append(1)
                    written += 1
            if len(skid[t]) < 2 and tq[t]:
                skid[t].append(tq[t].pop(0))
        for t in range(0 if bq else NT):
            if skid[t]:
                banks = skid[t][0]
                if not (banks & wbank):
                    skid[t].pop(0)
                    written += 1
            if len(skid[t]) < 2 and tq[t]:
                skid[t].append(tq[t].pop(0))
        # ---- HBM delivery into the front's per-tile queues
        for pc in range(128):
            i = pc_next[pc]
            if i >= n_raw or rng.random() >= p:
                continue
            d0 = dbase + i * e
            beats = tiles_of(d0, e)
            if any(len(tq[t]) >= fq for t, _ in beats):
                continue                           # PC stalls (front credit)
            for t, bk in beats:
                tq[t].append(set(bk))
            beats_total += len(beats)
            delivered += 1
            pc_next[pc] += 128
    src_B = n_raw * 32
    # steady rate: the load's span minus the HBM-delivery ramp (the first sector's fill is priced separately, as
    # hbm.first_access, by the simulator); the ideal span at the sustained rate is src_B / HBM_BPC
    ideal = src_B / HBM_BPC
    return dict(fmt=fmt, n_raw=n_raw, cycles=cyc, ideal_cycles=ideal, src_Bpc=src_B / cyc, frac_of_hbm=ideal / cyc,
                beats=beats_total, wgroups=wgroups, rgroups=rgroups, packets=packets,
                wide_write_rate=[w / cyc / LANES for w in w_served], wide_read_rate=[r / cyc / LANES for r in r_served])


def program_loads(path):
    c = json.load(open(path))
    return c


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    ap.add_argument("--raw", type=int, default=131072, help="raw sectors in the steady-state load (4 MiB)")
    a = ap.parse_args()
    res = dict(model="tools/hgi_vm/vm_bank_model.py", hbm_Bpc=HBM_BPC, gate_frac=0.90, steady=[], misaligned=[],
               lanes={})
    for bq in (0, 2, 4):
        for fmt in ("FP32", "BF16", "FP8E4M3", "FP4E2M1"):
            for wg, rg, pk, ls in ((0, 0, 0, False), (1, 1, 1, True), (1, 1, 1, False), (2, 2, 2, True), (2, 2, 2, False)):
                r = run(fmt, a.raw, wgroups=wg, rgroups=rg, packets=pk, bq=bq, lockstep=ls)
                r.update(bq=bq, lockstep=ls)
                res["steady"].append(r)
                print(f"bq{bq} {fmt:8s} wg{wg} rg{rg} pk{pk} {'lock' if ls else 'rand'}: {r['src_Bpc']:7.1f} B/cyc = "
                      f"{100 * r['frac_of_hbm']:5.1f}% of HBM; wide w {['%.3f' % x for x in r['wide_write_rate']]}"
                      f" r {['%.3f' % x for x in r['wide_read_rate']]}")
    for fmt, db in (("FP8E4M3", 1), ("FP8E4M3", 2), ("BF16", 1), ("FP32", 3)):
        r = run(fmt, a.raw, dbase=db, wgroups=1, rgroups=1, packets=1, bq=2)
        r["dbase_sector"] = db
        res["misaligned"].append(r)
        print(f"{fmt:8s} dest base sector {db} (misaligned): {r['src_Bpc']:7.1f} B/cyc = {100 * r['frac_of_hbm']:5.1f}%")
    if a.out:
        json.dump(res, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
