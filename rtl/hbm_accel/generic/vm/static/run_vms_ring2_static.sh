#!/usr/bin/env bash
# HBM-BIND 2026-10-24: two-stop VM ring (B2 die: hb_vms_NW + hb_vms_NE) gate.
#   run_vms_ring2_static.sh OUT REF_DIR
#   REF_DIR holds the ORIGINAL ot_vms_rstop_static.sv, ot_vms_hub_static.sv, hfd_hgi_vms_static_glue.sv, e.g.
#     for f in ot_vms_rstop_static.sv ot_vms_hub_static.sv hfd_hgi_vms_static_glue.sv; do
#       git show origin/main:rtl/hbm_accel/generic/vm/static/$f > REF_DIR/$f; done
# Steps (each prints one line; the last line is the GATE verdict):
#  1 default bit-exactness: tb_vms_ring2_default_eq (edited rstop/hub/glue at default params vs the renamed originals,
#    random pins, every output every cycle) PASS; mutants MUT 1 (rstop), 2 (hub), 3 (glue RMUT) FAIL.
#  2 the existing four-stop benches unchanged at default: run_static_ring.sh, run_vms_static_ring4_memory.sh,
#    run_vms_static_ring4_packet.sh, run_hub_static.sh.
#  3 tb_vms_ring2_static two-stop ring: bound masters (SYM 0) and symmetric NC 1 hubs (SYM 1), LINK 0 / 3 / 26 relay
#    stages per direction, several seeds: PASS. Mutants FAIL: RMUT 1 mirror payload, RMUT 2 four-stop mirror mask,
#    RMUT 3 commit observed one edge early, HMUT 5 mirror waits four acks, HMUT 6 mirror issued both directions.
# Fixed latencies (edges; inject = the edge the calendar enables the TX stop; LINK = relay flops on the die link;
# identical to the four-stop ONE-hop latencies, the two-stop ring only removes the two-hop / transit cases):
#   PREQ   hub cq k -> TX stop k+2 -> remote rce k+5+LINK -> replay enable k+6+LINK -> hub cq(replay) k+8+LINK -> bank pq k+9+LINK
#   PRSP   remote response enable X -> TX stop k=X+4 -> source cco X+7+LINK -> source response enable X+8+LINK -> cr X+9+LINK
#   mirror egress  eg + TX enable s -> remote xq E=s+3+LINK; commit (xq_done) observed E+CD (CD = 5 + BANK_PIN_IN = 6)
#   WACK   remote TX enable E+CD+1 -> source ack_o E+CD+4+LINK -> outstanding -1 at E+CD+6+LINK (mirror_busy +1 edge)
#   NW -> NE and NE -> NW are the same numbers (one hop each way); four-stop two-hop (via transit) cases were +2+LINK.
set -uo pipefail
out=${1:?out}; ref=${2:?ref dir}; mkdir -p "$out"; out=$(cd "$out" && pwd); ref=$(cd "$ref" && pwd)
d=$(cd "$(dirname "$0")" && pwd); cd "$d"; fail=0
note(){ echo "$1"; }
sed -E 's/\b(ot_vms_slice_static_glue|ot_vms_hub_static|ot_vms_rstop_static|hfd_hgi_vms_static_(SW|NW|SE|NE)_glue)\b/\1_ref/g' \
  "$ref/ot_vms_rstop_static.sv" "$ref/ot_vms_hub_static.sv" "$ref/hfd_hgi_vms_static_glue.sv" > "$out/ring2_ref.sv"
COMMON="ot_vms_rstop_static.sv ot_vms_hub_static.sv ot_vms_rcl_static.sv ot_vms_status_static.sv hfd_hgi_vms_static_glue.sv"
# 1 default equivalence
for m in 0 1 2 3; do
  iverilog -g2012 -s tb_vms_ring2_default_eq -Ptb_vms_ring2_default_eq.MUT=$m -o "$out/eq$m.vvp" $COMMON "$out/ring2_ref.sv" tb_vms_ring2_default_eq.sv > "$out/eq$m.build" 2>&1 || { note "BUILD_FAIL eq$m"; fail=1; continue; }
  vvp "$out/eq$m.vvp" > "$out/eq$m.log" 2>&1; r=$(grep -o 'VMS_RING2_EQ [A-Z]* MUT=[0-9]* checks=[0-9]* errors=[0-9]*' "$out/eq$m.log")
  if [ $m = 0 ]; then note "eq default      $r"; echo "$r" | grep -q ' PASS ' || fail=1
  else note "eq mutant $m     $r"; echo "$r" | grep -Eq ' FAIL .*errors=[1-9]' || fail=1; fi
done
# 2 existing four-stop benches at default parameters
bash run_static_ring.sh "$out/static_ring" > "$out/static_ring.log" 2>&1 && grep -q 'VMS_STATIC_RING PASS' "$out/static_ring.log" \
  && grep -q 'MUTANT observed FAIL' "$out/static_ring.log" && note "four-stop run_static_ring.sh PASS ($(grep -o 'PASS [0-9]* checks' "$out/static_ring.log"))" || { note "four-stop run_static_ring.sh FAIL"; fail=1; }
bash run_vms_static_ring4_memory.sh "$out/ring4m" > "$out/ring4m.log" 2>&1 && note "four-stop run_vms_static_ring4_memory.sh $(tail -1 "$out/ring4m.log")" || { note "four-stop ring4 memory FAIL"; fail=1; }
bash run_vms_static_ring4_packet.sh "$out/ring4p" > "$out/ring4p.log" 2>&1 && note "four-stop run_vms_static_ring4_packet.sh $(tail -1 "$out/ring4p.log")" || { note "four-stop ring4 packet FAIL"; fail=1; }
bash run_hub_static.sh "$out/hub" > "$out/hub.log" 2>&1 && note "four-stop run_hub_static.sh PASS ($(grep -c KILLED "$out/hub/receipt.json") mutants killed)" || { note "four-stop run_hub_static.sh FAIL (see $out/hub.log)"; fail=1; }
# 3 two-stop ring
R2="$COMMON hfd_hgi_vms_ring2_glue.sv tb_vms_ring2_static.sv"
run2(){ local tag=$1; shift; local P=(); for a in "$@"; do P+=(-Ptb_vms_ring2_static.$a); done
  iverilog -g2012 -s tb_vms_ring2_static "${P[@]}" -o "$out/r2_$tag.vvp" $R2 > "$out/r2_$tag.build" 2>&1 || { echo "BUILD_FAIL"; return; }
  vvp "$out/r2_$tag.vvp" > "$out/r2_$tag.log" 2>&1; grep -o 'VMS_RING2 \(PASS\|FAIL\).*' "$out/r2_$tag.log" | tail -1; rm -f "$out/r2_$tag.vvp"; }
for cfg in "s0l0 SYM=0 LINK=0 SEED=1" "s0l0b SYM=0 LINK=0 SEED=11 NTX=600" "s0l3 SYM=0 LINK=3 SEED=2" "s0l26 SYM=0 LINK=26 SEED=3" \
           "s1l0 SYM=1 LINK=0 SEED=4" "s1l3 SYM=1 LINK=3 SEED=5" "s1l26 SYM=1 LINK=26 SEED=7"; do
  set -- $cfg; tag=$1; shift; r=$(run2 $tag "$@"); note "ring2 $tag $r"; echo "$r" | grep -q '^VMS_RING2 PASS' || fail=1
done
for cfg in "m_r1 RMUT=1" "m_r2 RMUT=2" "m_r3 RMUT=3" "m_h5 HMUT=5" "m_h6 HMUT=6" "m_r2s RMUT=2 SYM=1" "m_r3l RMUT=3 LINK=3"; do
  set -- $cfg; tag=$1; shift; r=$(run2 $tag "$@"); note "ring2 mutant $tag $r"; echo "$r" | grep -Eq '^VMS_RING2 FAIL .*errors=[1-9]' || fail=1
done
[ $fail = 0 ] && echo "VMS_RING2_GATE PASS" || { echo "VMS_RING2_GATE FAIL"; exit 1; }
