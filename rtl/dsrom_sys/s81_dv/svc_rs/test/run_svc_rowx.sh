#!/usr/bin/env bash
# S81-ROWX (10-26): build + run the dsdv_svc_att held-row export / PK2 ingress bench (tb_dsdv_svc_rowx) and its
# negative controls.  usage: run_svc_rowx.sh <outdir> [variant ...]; variants: base (export / ingress, must PASS),
# miter (ROWX 1 vs ROWX 0 lockstep on legacy traffic, must PASS), mut6 (export rank field rank ^ 1: must FAIL),
# mut7 (PK2 ingress lands the other tile's half: must FAIL), mut8 (S81-ROWX2: RO export valid from the stack-only
# sel_held: must FAIL).  One svc_att module per build (~26 GB Verilator each).  Prints SVCROWX_GATE PASS when
# base passes every seed and every listed mutant fails.  Verilator = the daemon's pinned 5.050; defines = the 877 die's
# OT_SVC_ALLQ (engine = the plan tile_s FPL4/FML6/F12 engine, SVCQ_ENG_FG3 off as on the die).
set -u
R=$(cd "$(dirname "$0")/../../../../.." && pwd); O=$1; shift; VARS=${*:-"base miter mut6 mut7 mut8"}
VL=${VL:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
SRC="rtl/hdc/v41x/ot_hdc_v41x_attn_tile_s.sv rtl/hdc/v41x/ot_hdc_v41x_attn_s.sv rtl/hdc/v41x/ot_hdc_v41x_kreg.sv
 rtl/hdc/v41x/ot_hdc_v41x_attn_tile_lat.sv rtl/hdc/v41x/ot_hdc_v41x_attn_tile.sv rtl/hdc/v41x/ot_hdc_v41x_attn.sv
 rtl/hdc/v41x/ot_hdc_v41x_attn_staging.sv physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v
 rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_f12.sv
 rtl/hdc/v41x/ot_dsrom_su_add6.sv rtl/hdc/ot_hdc_delay.sv rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_att.sv
 rtl/dsrom_sys/s81_dv/svc_rs/test/tb_dsdv_svc_rowx.sv"
mkdir -p "$O"; bad=0
for v in $VARS; do
  X=""; case $v in base) M=0;; miter) M=0; X=-DTB_MITER;; mut*) M=${v#mut};; *) echo "variant? $v"; exit 2;; esac
  B=$O/$v; mkdir -p "$B/obj"
  # a generated but unbuilt obj dir (interrupted C++ build) is finished with make instead of re-running Verilator
  if [ ! -x "$B/obj/Vtb_dsdv_svc_rowx" ] && [ -f "$B/obj/Vtb_dsdv_svc_rowx.mk" ]; then
    make -s -j "${BJ:-16}" -C "$B/obj" -f Vtb_dsdv_svc_rowx.mk OPT_FAST=-O0 OPT_SLOW=-O0 OPT_GLOBAL=-O0 > "$O/make_$v.log" 2>&1 || true
  fi
  if [ ! -x "$B/obj/Vtb_dsdv_svc_rowx" ]; then
    $VL --binary --timing -j "${J:-8}" --build-jobs "${BJ:-16}" -MAKEFLAGS "OPT_FAST=-O0 OPT_SLOW=-O0 OPT_GLOBAL=-O0" -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style -Wno-TIMESCALEMOD -DOT_SVC_ALLQ -DTB_MUT=$M $X \
      --top-module tb_dsdv_svc_rowx -Mdir "$B/obj" $(for f in $SRC; do echo "$R/$f"; done) > "$O/build_$v.log" 2>&1 \
      || { echo "BUILD_FAIL $v"; tail -20 "$O/build_$v.log"; bad=1; continue; }
  fi
  # S81-ROWX2 run list: name|plusargs|expect.  ro0 = the held-list export = the B = 2 NXW fallback (B = 80 at NXW 40);
  # ro1 = rank-order slots (NP 7 x NXW 40, XP 320); fx<L> = the 1M golden token's layer (ex = its max-held owner);
  # st<N> = ex holds the first N ranks (ro0: the budget overflow must be caught = PASS; ro1: no overflow)
  F=$R/results/rtl/s81_rowx2_1026/fix
  FX="2:1:1 8:1:1 14:2:2 20:1:3 24:3:2 28:1:3 32:2:0 36:2:1"
  RUNS=""
  case $v in
    base) for s in 1 2 3; do RUNS="$RUNS ro0_s$s|+seed=$s+ro=0 ro1_s$s|+seed=$s+ro=1"; done
          for x in $FX; do IFS=: read L d st <<< "$x"; LL=$(printf %02d $L); for m in 0 1; do
            RUNS="$RUNS ro${m}_fxL$L|+ro=$m+fix=$F/gid_L$LL.hex+exd=$d+rxd=$(( (d + 1) % 4 ))+st=$st"; done; done
          RUNS="$RUNS ro1_st150|+seed=4+ro=1+stress=150 ro1_st300|+seed=5+ro=1+stress=300 ro0_st100|+seed=4+ro=0+stress=100 ro0_st150|+seed=5+ro=0+stress=150";;
    miter) RUNS="miter_s1|+seed=1";;
    mut6|mut7) RUNS="ro0_s1|+seed=1+ro=0 ro1_s1|+seed=1+ro=1";;
    mut8) RUNS="ro1_s1|+seed=1+ro=1 ro1_fxL28|+ro=1+fix=$F/gid_L28.hex+exd=1+rxd=2+st=3";;
  esac
  for rr in $RUNS; do
    n=${rr%%|*}; pa=${rr#*|}; pa=${pa//+/ +}
    "$B/obj/Vtb_dsdv_svc_rowx" $pa > "$O/run_${v}_$n.log" 2>&1
    l=$(grep -h '^ROWX ' "$O/run_${v}_$n.log" | tail -1); echo "$v $n: $l"
    if [ "$v" = base ] || [ "$v" = miter ]; then case "$l" in *verdict=PASS*) ;; *) bad=1;; esac
    else case "$l" in *verdict=FAIL*) ;; *) echo "MUTANT_NOT_CAUGHT $v $n"; bad=1;; esac; fi
  done
done
[ $bad = 0 ] && echo "SVCROWX_GATE PASS" || echo "SVCROWX_GATE FAIL"; exit $bad
