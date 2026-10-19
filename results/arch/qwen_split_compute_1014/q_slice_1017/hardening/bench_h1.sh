#!/bin/bash
# S-QSLICE 10-18 hardening benches (run from the repository root on the fleet; Verilator 5.x on PATH):
#   lint     the two opt-in hard configurations elaborate (slice2 SU_LT/HD_W130 = 1, qfd_dv_su_lane, qfd_dv_heads_w130)
#   heads    tb_qfd_dv_heads with HD_W130 = 1 (32 closed-view-config leaves; constant slice-minus-fabric offset)
#            + mutants 8 (column head TDM, HEAD_MUT 3) and 9 (x word bit flip): must FAIL
#   slice2   dv_bench2 a..g i j with SU_LT = 1 + HD_W130 = 1 (8 hard lane tiles, w130 heads)
#            + mutants OT_LOFF_MUT (lane offset twice, su8 tile path), OT_TLS_MUT (lane ring read one word late),
#              OT_LOREG_MUT (answers keep RD relay stages under the tile's OREG) and OT_IREG_MUT (va bypasses its pin flop)
set -u
W=${W:-$PWD/../qslice2_bench_h1}; rm -rf $W; mkdir -p $W
V=${VERILATOR:-verilator}
B=rtl/test/qwen_dv/dv_bench2.py
FS=$(python3 -c "import sys; sys.path.insert(0,'rtl/test/qwen_dv'); import dv_bench2 as B; print(' '.join(s for s in B.SRCS2 + B.XSRCS if 'tb_' not in s))")
LINT="$V --lint-only -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-WIDTH"
( $LINT --top-module qfd_dv_slice2 -GSU_LT=1 -GHD_W130=1 $FS && echo "LINT slice2 SU_LT=1 HD_W130=1: ok" ) > $W/lint_h.out 2>&1 &
( $LINT --top-module qfd_dv_slice2 $FS && echo "LINT slice2 default: ok" ) > $W/lint_0.out 2>&1 &
( $LINT --top-module qfd_dv_su_lane $FS && echo "LINT qfd_dv_su_lane: ok" ) > $W/lint_lane.out 2>&1 &
( $LINT --top-module qfd_dv_heads_w130 $FS && echo "LINT qfd_dv_heads_w130: ok" ) > $W/lint_heads.out 2>&1 &
JOBS=12 rtl/test/qwen_dv/run_heads.sh $W/heads_pos -GHD_W130=1 > $W/heads_pos.out 2>&1 &
JOBS=12 rtl/test/qwen_dv/run_heads.sh $W/heads_m8 -GHD_W130=1 -GMUT=8 > $W/heads_m8.out 2>&1 &
JOBS=12 rtl/test/qwen_dv/run_heads.sh $W/heads_m9 -GHD_W130=1 -GMUT=9 > $W/heads_m9.out 2>&1 &
python3 $B a b c d e f g i j --work $W/s_pos --vflags "-GSU_LT=1 -GHD_W130=1" > $W/slice_pos.out 2>&1 &
python3 $B a b c d e f g --work $W/s_loff --vflags "-GSU_LT=1 -GHD_W130=1 +define+OT_LOFF_MUT" > $W/slice_loff_mut.out 2>&1 &
python3 $B a b c d e f g --work $W/s_tls --vflags "-GSU_LT=1 -GHD_W130=1 +define+OT_TLS_MUT" > $W/slice_tls_mut.out 2>&1 &
python3 $B a b c d e f g --work $W/s_loreg --vflags "-GSU_LT=1 -GHD_W130=1 +define+OT_LOREG_MUT" > $W/slice_loreg_mut.out 2>&1 &
python3 $B a b c d e f g --work $W/s_ireg --vflags "-GSU_LT=1 -GHD_W130=1 +define+OT_IREG_MUT" > $W/slice_ireg_mut.out 2>&1 &
wait
for f in lint_h lint_0 lint_lane lint_heads heads_pos heads_m8 heads_m9 slice_pos slice_loff_mut slice_tls_mut slice_loreg_mut slice_ireg_mut; do
  echo "== $f"; grep -v "^%Warning" $W/$f.out | head -30; done
