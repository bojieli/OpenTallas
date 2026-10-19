#!/bin/bash
# HBM-NEXT-VEH 10-19 step 3: the SM4 P = 4 leaf (hnx_rp4lp4_lf) driven by ONE layer's SM records (DS L3, MTP verify N = 6
# and 4-user N = 4; results/arch/hbm_next_1019/veh/layer_units/layer_records.json). Fleet only, Verilator 5.050.
# Per record shape the leaf sees NCHUNK = csum chunks (K / 256 block-dot) x ceil(rows per SM / 8) interleaved row groups:
#   expert 2304 x 53 FP4 -> 9 x 1 = 9;  expert / shared 5120 x 24 -> 20 x 1 = 20;  shared 1280 x 512 -> 5 x 4 = 20;
#   shared 8192 x 53 -> 32 x 1 = 32.   Chunk spacing K = 4 (minimum, static-schedule rule) and 16 (SM4 production-like).
# Each point runs P = 1 and P = 4 (THR = 1): the P4 / P1 publish-span ratio of a SHORT record is the layer-level cost of
# the +1 front / +1 publish / +8p lane skew that the 64-chunk SM4 bench amortised (1.003x / 1.012x).
# Negative control: MUT 1 (lane alias) at the minimum spacing K = 4 (random stimulus) must FAIL (LANE MISMATCH) -> fail witness.
#   tools/hbm_next/vehicle/run_sm4_layer.sh OUT      (from a bundle root)
set -u
OUT=$(realpath -m "${1:?OUT}"); mkdir -p "$OUT"
B=rtl/hbm_next/sm/tb/run_leaf_bench.sh
pids=()
for n in 9 20 32; do
  for k in 4 16; do
    for p in 1 4; do
      d=$OUT/n${n}_k${k}; mkdir -p "$d"
      ( VL_JOBS=4 bash $B "$d" $p 0 1 -GNCHUNK=$n -GKMIN=$k -GKMAX=$k > "$d/p$p.out" 2>&1; echo "RC=$?" >> "$d/p$p.out" ) &
      pids+=($!)
    done
  done
done
d=$OUT/mut1_k4; mkdir -p "$d"
( VL_JOBS=4 bash $B "$d" 4 1 0 -GNCHUNK=9 -GKMIN=4 -GKMAX=4 > "$d/p4_m1.out" 2>&1; echo "RC=$?" >> "$d/p4_m1.out" ) &
pids+=($!)
wait "${pids[@]}"
python3 - "$OUT" <<'PY'
import glob, json, re, sys
o = sys.argv[1]; rows = []
for d in sorted(glob.glob(o + "/n*_k*")):
    sp = {}
    for p in (1, 4):
        for f in glob.glob(f"{d}/run_p{p}_m0_t1.log"):
            t = open(f).read()
            m = re.search(r"THROUGHPUT P=(\d+) chunks=(\d+) K=(\d+) .*publish_span=(\d+)", t)
            if m and "PASS HNX-RP4LP4" in t:
                sp[p] = int(m.group(4))
    n, k = re.search(r"n(\d+)_k(\d+)", d).groups()
    rows.append(dict(nchunk=int(n), k=int(k), p1_span=sp.get(1), p4_span=sp.get(4),
                     ratio=round(sp[4] / sp[1], 4) if 1 in sp and 4 in sp else None,
                     delta=(sp[4] - sp[1]) if 1 in sp and 4 in sp else None))
mut = open(glob.glob(o + "/mut1_k4/p4_m1.out")[0]).read()
res = dict(schema="opentallas.hbm_next_1019.veh.sm4_layer.v1", sim="Verilator 5.050", points=rows,
           all_pass=all(r["ratio"] is not None for r in rows), mut1_caught="MUTANT CAUGHT" in mut)
json.dump(res, open(o + "/sm4_layer.json", "w"), indent=1)
print(json.dumps(res))
PY
