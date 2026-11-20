#!/usr/bin/env bash
# FABLE-FIX-HEAD-SERDES-R2 2026-11-20: unit bench of ot_s81_rate_match in the HEAD forms (OT_S81_RM_STAGED, RPC 32) with
# and without the registered read-side reset leaves (RLEAF), on tb_s81_rate_match, both slip directions.  The RTL and the
# bench are COPIED to OUTDIR; the source is never edited.  usage: run_rm_rleaf_bench.sh MODE OUTDIR
#   rleaf0 / rleaf1   -> RM_RLEAF_BENCH PASS dirs=2   (RLEAF 0 / 1, RPC 32, staged)
#   mut_stale         -> FAIL (RLEAF 1 + RMSTAGED_MUT_STALE: selector copy 5 stale)
#   mut_group         -> FAIL (RLEAF 1, slice group 5 held in reset: its leaf never releases)
set -u
mode=${1:?rleaf0|rleaf1|mut_stale|mut_group}; out=${2:?fresh output directory}; mkdir -p "$out"
R=$(cd "$(dirname "$0")/../.." && pwd); L=$R/rtl/dsrom_sys/s81_link
cp "$L/ot_pdie_serdes.sv" "$out/rtl.sv"; cp "$L/tb_s81_rate_match.sv" "$out/tb.sv"
rl=1; defs="-DOT_S81_RM_STAGED"
case $mode in rleaf0) rl=0;; rleaf1) ;; mut_stale) defs="$defs -DRMSTAGED_MUT_STALE";;
  mut_group) python3 -I - "$out/rtl.sv" <<'PY' || { echo "RM_RLEAF_BENCH MUTANT_NOT_APPLIED"; exit 2; }
import sys
p=sys.argv[1]; t=open(p).read(); a="wire rrn_g = rrn_s[LO / 64];"; assert t.count(a)==1
open(p,"w").write(t.replace(a,"wire rrn_g = (LO / 64 == 5) ? 1'b0 : rrn_s[LO / 64];"))
PY
  ;; *) echo "RM_RLEAF_BENCH BAD_MODE $mode"; exit 2;; esac
python3 -I - "$out/tb.sv" "$rl" <<'PY' || { echo "RM_RLEAF_BENCH TB_EDIT_FAIL"; exit 2; }
import sys
p,rl=sys.argv[1:]; t=open(p).read(); a="ot_s81_rate_match u_rm ("; assert t.count(a)==1
open(p,"w").write(t.replace(a,"ot_s81_rate_match #(.RLEAF(%s), .RPC(32)) u_rm (" % rl))
PY
nf=0
for f in 1 0; do
  iverilog -g2012 $defs -s tb_s81_rate_match -P tb_s81_rate_match.FAST=$f -o "$out/sim$f.vvp" "$out/tb.sv" "$out/rtl.sv" \
    > "$out/build$f.log" 2>&1 || { echo "RM_RLEAF_BENCH BUILD_FAIL FAST=$f"; tail -5 "$out/build$f.log"; exit 2; }
  vvp -n "$out/sim$f.vvp" > "$out/run$f.log" 2>&1
  grep '^ERR' "$out/run$f.log" | head -3
  line=$(grep '^TB_S81_RATE_MATCH' "$out/run$f.log" | tail -1); echo "$line"
  case "$line" in *" PASS") ;; *) nf=$((nf + 1));; esac
done
if [ $nf = 0 ]; then echo "RM_RLEAF_BENCH PASS mode=$mode dirs=2"; else echo "RM_RLEAF_BENCH FAIL mode=$mode dirs_failed=$nf"; exit 1; fi
