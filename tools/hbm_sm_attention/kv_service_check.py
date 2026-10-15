#!/usr/bin/env python3
"""32-SM concurrent KV service check for attention on the SM engines (H-SM-ATT r2 2026-10-15).

Every SM streams its own KV rows from its OWN stack through its OWN PC group (stack-local KV, T_band2: one 4-PC group per SM
on the die edge, the SM staging buffer behind it), so with all 32 SMs streaming at once the only shared resources are the
per-stack PHY (8 SMs) and the quadrant VM hub's KV_DESC issue (one 64-bit descriptor port per SM, one word per op).  This
script states, per record type and per SM under the SU slice placement rule (position i -> quadrant (i mod 512)//128):
  lines per op (canonical rows: KV8 528 B, KV4 288 B, Qwen 128 B; 136-B lines), stream cycles at the physical 99 B/cycle/SM
  (8 lines / 11 cycles), staging-block fit (2 banks x 64 lines, ot_hbm_svc_static_sm_packed136), and the per-stack aggregate
  demand of its 8 SMs against 8 x 99 B/cycle.  It is a MODEL of the off-chip boundary (the PHY/DRAM side is declared modeled);
  the on-die part (converter consumption at 8/11 with zero faults) is measured by sm_attn_bench / sm_elem_bench.
  kv_service_check.py [--out R.json]
"""
import argparse
import json
import math

LINE = 136
BW = 99.0                    # B/cycle/SM physical
RATE = 8 / 11                # lines/cycle/SM (98.9 B/cycle)
BLOCK_LINES, BANKS = 64, 2


def lines(nbytes):
    return math.ceil(nbytes / LINE)


def per_sm(rows_by_sm, row_bytes):
    out = []
    for sm, rows in enumerate(rows_by_sm):
        b = sum(row_bytes(r) for r in rows)
        n = lines(b)
        out.append(dict(sm=sm, rows=len(rows), bytes=b, lines=n, stream_cycles=math.ceil(n / RATE),
                        staging_blocks=math.ceil(n / BLOCK_LINES)))
    return out


def stack_of(sm):
    return sm // 8           # quadrant q = stack q (8 SMs each)


def summarise(name, ops):
    busiest = max(ops, key=lambda o: o["stream_cycles"])
    stacks = {}
    for o in ops:
        s = stack_of(o["sm"])
        stacks.setdefault(s, []).append(o)
    agg = {s: dict(bytes=sum(o["bytes"] for o in v), window=max(o["stream_cycles"] for o in v)) for s, v in stacks.items()}
    for s, v in agg.items():
        v["demand_B_per_cycle"] = round(v["bytes"] / v["window"], 1) if v["window"] else 0.0
        v["physical_B_per_cycle"] = 8 * BW
        v["fits"] = v["demand_B_per_cycle"] <= 8 * BW + 1e-9
    return dict(record=name, busiest_sm=busiest["sm"], busiest_lines=busiest["lines"], busiest_stream_cycles=busiest["stream_cycles"],
                busiest_staging_blocks=busiest["staging_blocks"], staging_fits_double_buffer=busiest["staging_blocks"] <= BANKS,
                stacks=agg, all_stacks_fit=all(v["fits"] for v in agg.values()))


def ds_t640(balanced):
    T8, T4 = 128, 512
    rb = lambda r: 528 if r < T8 else 288
    if balanced:   # current component plan: 4 window + 16 top-k rows per SM (needs SU balanced-tail lowering)
        qk = [list(range(4 * s, 4 * s + 4)) + list(range(T8 + 16 * s, T8 + 16 * s + 16)) for s in range(32)]
    else:          # SU slice rule as is: block k = i // 128 on quadrant k % 4, rows of a quadrant spread over its 8 SMs
        qk = [[] for _ in range(32)]
        for k in range(5):
            q = k % 4
            blk = list(range(128 * k, 128 * k + 128))
            nsm = 8
            for j in range(nsm):
                qk[8 * q + j] += blk[16 * j: 16 * j + 16]
    pv = [[] for _ in range(32)]
    runs = [list(range(32 * u, 32 * u + 32)) for u in range(20)]          # aligned 4-chunk runs
    used = {q: 0 for q in range(4)}
    for u, r in enumerate(runs):
        q = (r[0] // 128) % 4
        pv[8 * q + used[q]] = r
        used[q] += 1
    return summarise(f"DS T640 QK ({'balanced 20 rows/SM' if balanced else 'SU slice rule'})", per_sm(qk, rb)), \
        summarise("DS T640 PV (aligned 4-chunk runs, quadrant of their block)", per_sm(pv, rb))


def qwen():
    qk = [[] for _ in range(32)]
    for k in range(64):
        q, j = k % 4, (k // 4) // 2
        qk[8 * q + j] += list(range(128 * k, 128 * k + 128))
    rb = lambda r: 128
    pv = [[] for _ in range(32)]
    for k in range(64):                      # one PV op per block; the busiest op is one block
        q, j = k % 4, (k // 4) // 2
        if not pv[8 * q + j]:
            pv[8 * q + j] = list(range(128 * k, 128 * k + 128))
    return summarise("Qwen T8192 QK per KV head (2 blocks/SM, standard 128-B rows)", per_sm(qk, rb)), \
        summarise("Qwen T8192 PV op (one block)", per_sm(pv, rb))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    a = ap.parse_args()
    recs = list(ds_t640(True)) + [ds_t640(False)[0]] + list(qwen())
    out = dict(scope="MODEL of the off-chip PHY/DRAM boundary; per-SM dedicated PC group + stack-local KV; on-die consumption measured separately",
               physical_B_per_cycle_per_SM=BW, line_bytes=LINE, line_rate=RATE, records=recs,
               shared_resources=["per-stack PHY: 8 SMs x 99 B/cycle", "VM hub KV_DESC: 1 x 64-b word per SM per op (no per-line traffic)"],
               note="DS QK under the unmodified SU slice rule puts window+top-k block 0 and 4 on quadrant 0 (32 rows/SM vs 16): busiest SM 96 lines vs 50 balanced; "
                    "balanced needs the SU balanced-tail lowering (H-ELEM-B 09:21) -- SU decision.")
    s = json.dumps(out, indent=1)
    print(s)
    if a.out:
        open(a.out, "w").write(s)


if __name__ == "__main__":
    main()
