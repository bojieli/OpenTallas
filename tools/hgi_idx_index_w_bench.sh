#!/bin/bash
# el1013-idxw-v3: bit-exact unit bench of the IDX.INDEX wide-lane frame adapter ot_hgi_idx_index_w (HBM B2).
# DUT: ot_hgi_idx_unit IXW=1 (-> ot_hgi_idx_index_w, 8 lanes) + hfd_idx_sel + 4 hfd_idx_score in tb_hgi_idx_index, every
# VM transfer on a lane model of the wide read / write groups (fatal on a wrong lane; fatal if the frames used the
# packet client).  Vectors and golden: tools/hbm_idx_die_bench.py prepare / compare (4 frames from retained real keys:
# candidates, keep bitmap, partial die, fault path; top-k O / R and candidates D read back from the VM image).
# usage (repo root): hgi_idx_index_w_bench.sh OUT [UNIT_MUT]   UNIT_MUT 0 exact; 2 next head's weight; 3 R from the
# wrong lane (adapter MUT 1 / 2) -- both must end "HGI_IDX_INDEX_W FAIL compare".  IXW=0 in the environment runs the
# packet adapter on the same vectors (reference).
set -uo pipefail
OUT=$(mkdir -p "$1" && cd "$1" && pwd); M=${2:-0}; IXW=${IXW:-1}; R=$(pwd)
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}; [ -x "$V" ] || V=verilator
X=$R/physical/hbm_accel_die_views/index/rtl
SRC="$X/hfd_idx_lib.sv $X/hfd_idx_score.sv $X/hfd_idx_sel.sv
 $R/rtl/hbm_accel/index/ot_hbm_accel_index_query.sv $R/rtl/hbm_accel/index/ot_hbm_accel_index_candidate.sv
 $R/rtl/hdc/v41x/ot_hdc_v41x_idx_lat.sv $R/rtl/hdc/v41x/ot_hdc_v41x_idx_arith_lat.sv $R/rtl/hdc/v41x/ot_hdc_v41x_idx_arith.sv
 $R/rtl/hdc/v41x/ot_hdc_v41x_sel.sv $R/rtl/hdc/v41x/ot_hdc_v41x_sel_lib.sv $R/rtl/hdc/v41x/ot_hdc_v41x_sel_slice.sv
 $R/rtl/hdc/v41x/ot_hdc_v41x_sel_cand.sv $R/rtl/hdc/v41/ot_hdc_actquant.sv $R/rtl/hdc/ot_hdc_delay.sv $R/rtl/hdc/ot_hdc_fastfp.sv
 $R/rtl/hdc/ot_hdc_fpu.sv $R/rtl/hdc/ot_hdc_fp32_mul_pipe.sv $R/rtl/proto/ot_fp32_add_rne_pipe.sv $R/rtl/hdc/ot_hdc_prefix.sv
 $R/rtl/hdc/ot_hdc_fp32_add_lat.sv $R/rtl/hbm_accel/service/ot_hbm_accel_cdc_fifo.sv
 $R/rtl/hbm_accel/generic_20261009/ot_hgi_idx_topk.sv $R/rtl/hbm_accel/generic_20261009/ot_hgi_idx_topk_registered.sv
 $R/rtl/hbm_accel/generic/idx/ot_hgi_idx_owned.sv $R/rtl/hbm_accel/generic/idx/ot_hgi_idx_merge.sv
 $R/rtl/hbm_accel/generic/idx/ot_hgi_idx_index.sv $R/rtl/hbm_accel/generic/idx/ot_hgi_idx_index_w.sv
 $R/rtl/hbm_accel/generic/idx/ot_hgi_idx_unit.sv $R/rtl/hbm_accel/generic/idx/tb_hgi_idx_index.sv ${HGI_IDXW_EXTRA_SRC:-}"
python3 tools/hbm_idx_die_bench.py prepare --work "$OUT/vec" > "$OUT/prepare.log" 2>&1 || { echo "HGI_IDX_INDEX_W ERROR prepare"; tail -5 "$OUT/prepare.log"; exit 2; }
( cd "$OUT" && "$V" --binary --timing ${HGI_IDXW_VOPT:--O2} -j ${NC:-8} -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-BLKANDNBLK -Wno-MULTIDRIVEN \
    -Wno-MODMISSING -I$R/rtl/hbm_accel/generic -I$R/rtl/hbm_accel/generic/idx --top-module tb_hgi_idx_index -GMUT=$M -GIXW=$IXW -Mdir obj $SRC > build.log 2>&1 ) \
  || { echo "HGI_IDX_INDEX_W ERROR build"; grep -m5 -E "%Error" "$OUT/build.log"; exit 2; }
( cd "$OUT" && ./obj/Vtb_hgi_idx_index +DIR=$OUT/vec +ODIR=. +SEED=7 +GAP=3 > sim.log 2>&1 ); src=$?
grep -E "HGIIDX_(FRAME|WIDE|END)" "$OUT/sim.log"
grep -q "^HGIIDX_END" "$OUT/sim.log" || { echo "HGI_IDX_INDEX_W ERROR sim rc=$src (no HGIIDX_END)"; tail -3 "$OUT/sim.log"; exit 2; }
python3 tools/hbm_idx_die_bench.py compare --work "$OUT/vec" --run "$OUT" > "$OUT/compare.log" 2>&1; crc=$?
python3 - "$OUT/verdict.json" "$M" "$IXW" <<'P'
import json, sys
v = json.load(open(sys.argv[1])); f = v["frames"]
n = lambda k: sum(x.get(k, 0) for x in f)
if v["verdict"] == "PASS" and all(x["ok"] for x in f):
    print(f"HGI_IDX_INDEX_W PASS ({len(f)} frames, {n('scores_checked')} scores, {n('topk_checked')} topk lanes, "
          f"{n('cand_checked')} candidates exact; unit MUT {sys.argv[2]} IXW {sys.argv[3]}; cycles {[x.get('cycles') for x in f]})")
    sys.exit(0)
print(f"HGI_IDX_INDEX_W FAIL compare (unit MUT {sys.argv[2]} IXW {sys.argv[3]}): "
      + "; ".join(f"{x['name']}: {x['why']}" for x in f if not x["ok"])[:600])
sys.exit(1)
P
