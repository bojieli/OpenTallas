#!/usr/bin/env python3
"""How many (row, pos) can be OPEN at one S81 gather root at once, from the REAL field order (s81-gather 2026-10-13).

A (row, pos) is open at a root from the arrival of its first partial that is not a complete row until its last
sibling add retires.  A row whose matrix has ONE K segment arrives complete and is never open.  The field order is
the compiler's: the S81 binding (matrix_map.jsonl.gz: per plan [segment, pair, superrow0, count, stride, base, words])
through tools/dsrom_1m_field.layer_groups / phase_groups (the phase partition the measured field runs use), the golden
router's experts of the 1M token (ctx1048576_LNN.json), rank 0.  A phase is die-global and the VM issues the next
phase word only after the capture is drained, so partials of two phases never meet in a root.

Per phase and region (root r = superrow % 128, rows 2s, 2s + 1):
  static   = rows of the region whose matrix has >= 2 segments (x positions).  Upper bound, order-free.
  stream   = peak of open rows under the x-stream order: the spine streams x at VRD = 64 elements a cycle, a segment
             [e0, e0 + elems) yields its partial after its last unit passed (cycle ceil((e0 + elems) / 64) + C_ELEM,
             the same constant for every segment), the pair emits one partial a cycle, the root's sibling add takes
             C_ADD cycles; a row is open from its first partial to its last partial + C_ADD * ceil(log2 nseg).
  (the constants only shift every row alike: the peak depends on the segment END ORDER, which is the compiler's.)
Output: JSON (per layer: max, the phase holding it, histogram over region x phase of the peak) + one text line a layer.
"""
import argparse, collections, gzip, json, math, os, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
VRD, C_ELEM, C_ADD = 64, 31, 14


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--binding", type=Path, required=True)
    ap.add_argument("--ref", type=Path, default=Path("/home/ubuntu/w17work/ref/ctx1048576_seed20260930"))
    ap.add_argument("--layers", default="0,2,14")
    ap.add_argument("--all-experts", action="store_true", help="every expert of the layer, not the golden six")
    ap.add_argument("--positions", type=int, default=1)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--trace-out", type=Path, help="per layer: the root partial stream (stream order) of the regions "
                    "--trace-regions and of the region holding the layer maximum, every phase (gen_root_stim real)")
    ap.add_argument("--trace-regions", default="0,127")
    a = ap.parse_args()
    os.environ["OT_DSROM_FIELD_BINDING"] = str(a.binding.resolve())
    import dsrom_1m_field as F
    sm = json.loads((F.S81 / "stage_map.json").read_text())
    F.BY_STAGE = "region_bounds_by_stage" in sm
    sbf = F.stage_bounds(sm)
    layers = [int(x) for x in a.layers.split(",")]
    experts = {}
    for L in layers:
        j = a.ref / f"ctx1048576_L{L:02d}.json"
        experts[L] = json.loads(j.read_text())["experts"] if j.exists() and not a.all_experts else None
    ents = {L: [] for L in layers}
    with gzip.open(F.S81 / "matrix_map.jsonl.gz", "rt") as f:
        for ln in f:
            r = json.loads(ln)
            L = r["layer"]
            if L in ents and (r["expert"] is None or experts[L] is None or r["expert"] in experts[L]):
                ents[L].append(r)
    out = dict(schema="opentallas.s81ph.root_open_rows.v1", binding=str(a.binding), positions=a.positions,
               matrix_map_sha256=F.sha(F.S81 / "matrix_map.jsonl.gz"), model=dict(VRD=VRD, C_ELEM=C_ELEM, C_ADD=C_ADD),
               experts={str(L): (experts[L] if experts[L] is not None else "all") for L in layers}, layers={})
    traces = {}
    for L in layers:
        hist_s, hist_d = collections.Counter(), collections.Counter()
        phases, best = [], (0, 0, None, None)
        tr_l, best_reg = collections.defaultdict(list), 0
        for grp, (node, xsrc, mats) in F.layer_groups(L, ents[L], sbf, None).items():
            for g in F.phase_groups(mats):
                name = f"L{L}.{grp}" + ("" if len(g) == len(mats) else "." + "+".join(x["alias"] for x in g))
                pk_s = pk_d = 0
                rows_max = 0
                for reg in range(128):
                    ev, nrow, nopen, leaves, jrow = [], 0, 0, [], 0
                    for m in g:
                        segs = m["segments"]
                        per = collections.defaultdict(list)
                        for s, si, p in m["regions"].get(str(reg), []):
                            per[s].append(si)
                        for s, sis in per.items():
                            assert sorted(sis) == list(range(len(segs))), (name, reg, s, sis)
                            rows = [r for r in (2 * s, 2 * s + 1) if r < m["entry_rows"]]
                            nrow += len(rows)
                            for r in rows:      # root row id: 256 j + 2 reg + (r & 1), j = the root's j-th superrow
                                rid = (256 * jrow + 2 * reg + (r & 1)) & 0xFFFF
                                for pos in range(a.positions):
                                    for si, (e0, el) in enumerate(segs):
                                        leaves.append((-(-(e0 + el) // VRD) + C_ELEM, pos, rid, si, len(segs)))
                            jrow += 1
                            if len(segs) < 2:
                                continue
                            nopen += len(rows)
                            ends = sorted(-(-(e0 + el) // VRD) + C_ELEM for e0, el in segs)
                            t0, t1 = ends[0], ends[-1] + C_ADD * math.ceil(math.log2(len(segs)))
                            for _ in rows:
                                ev += [(t0, 1), (t1, -1)]
                    cur = pk = 0
                    for _, d in sorted(ev, key=lambda x: (x[0], -x[1])):
                        cur += d
                        pk = max(pk, cur)
                    nopen *= a.positions
                    pk *= a.positions
                    evl, tprev = [], -1
                    for t, pos, rid, si, n in sorted(leaves):
                        tprev = max(t, tprev + 1)
                        evl.append([tprev, (pos << 29) | (rid << 13) | (si << 8) | n])
                    if evl:
                        tr_l[reg].append(dict(phase=name, open_static=nopen, events=evl))
                    if (nopen, pk) > best[:2] and (nopen, pk) >= (pk_s, pk_d):
                        best_reg = reg
                    hist_s[nopen] += 1
                    hist_d[pk] += 1
                    pk_s, pk_d, rows_max = max(pk_s, nopen), max(pk_d, pk), max(rows_max, nrow)
                phases.append(dict(phase=name, node=node, K=g[0]["K"], fmts=sorted({m["fmt"] for m in g}),
                                   nseg=sorted({len(m["segments"]) for m in g}),
                                   segments=[m["segments"] for m in g][:2], rows_region_max=rows_max,
                                   open_static_max=pk_s, open_stream_max=pk_d))
                if (pk_s, pk_d) > best[:2]:
                    best = (pk_s, pk_d, name, [m["segments"] for m in g][0])
        keep = list(range(128)) if a.trace_regions == "all" else sorted({int(x) for x in a.trace_regions.split(",")} | {best_reg})
        traces[str(L)] = dict(max_region=best_reg, traces={str(r): tr_l[r] for r in keep})
        out["layers"][str(L)] = dict(max_region=best_reg, open_static_max=best[0], open_stream_max=best[1], phase=best[2], segments=best[3],
                                     hist_static=dict(sorted(hist_s.items())), hist_stream=dict(sorted(hist_d.items())),
                                     phases=phases)
        print(f"L{L}: open (row,pos) per root max static {best[0]} stream {best[1]} at {best[2]} segments {best[3]}; "
              f"hist static {dict(sorted(hist_s.items()))} stream {dict(sorted(hist_d.items()))}")
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(out, indent=1) + "\n")
    if a.trace_out:
        a.trace_out.write_text(json.dumps(dict(schema="opentallas.s81ph.root_trace.v1", binding=str(a.binding),
                                               matrix_map_sha256=out["matrix_map_sha256"], layers=traces)) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
