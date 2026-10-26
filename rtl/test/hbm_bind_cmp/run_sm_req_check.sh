#!/usr/bin/env bash
# HBM-BIND-CMP bench: ot_hbm_sm_req_check MUT 0 PASS (3 lane shapes) and MUT 1/2/3 FAIL; plus a lint of the
# ot_hbm_svc_sm_group_rel_id_rc wrapper against the real service-group RTL.  Usage: run_sm_req_check.sh OUT (from repo root)
set -uo pipefail
OUT=$(realpath -m "${1:?out}"); mkdir -p "$OUT"; R=$(git rev-parse --show-toplevel); cd "$R"
D=rtl/hbm_accel/loader/service_native; T=rtl/test/hbm_bind_cmp; fail=0
run(){ local tag=$1; shift; verilator --binary --timing -Wno-fatal -Wno-lint -Wno-style --top-module tb_sm_req_check "$@" \
   $D/ot_hbm_sm_req_check.sv $T/tb_sm_req_check.sv --Mdir "$OUT/obj_$tag" -o tb > "$OUT/build_$tag.log" 2>&1 \
   && "$OUT/obj_$tag/tb" > "$OUT/run_$tag.log" 2>&1; grep -h TB_SM_REQ_CHECK "$OUT/run_$tag.log" 2>/dev/null || echo "TB $tag NO RESULT"; }
for s in "0 0" "3 4" "11 17"; do set -- $s
  r=$(run m0_$1_$2 -GLS=$1 -GLR=$2 -GMUT=0); echo "$r"; echo "$r" | grep -q "PASS$" || fail=1; done
for m in 1 2 3; do r=$(run m$m -GLS=3 -GLR=4 -GMUT=$m); echo "$r"; echo "$r" | grep -q " FAIL errs=" || fail=1; done
# wrapper lint: real group RTL closure from the service_native dir + hdc/sm static children it instantiates
Y=$(find rtl/hbm_accel rtl/hdc -name '*.sv' -printf '%h\n' | sort -u | sed 's/^/-y /')
verilator --lint-only -Wno-fatal -Wno-lint -Wno-style -Wno-MULTITOP --top-module ot_hbm_svc_sm_group_rel_id_rc -GRQD=9 \
   -GLBANKS=4 -GNID=6 -GIDW=9 -GPAW=11 -GPREL=1 -GDD=256 -GID_COHORT=1 -GXSLOT=1 -GOPEN_IL=1 $Y \
   $D/ot_hbm_sm_req_check.sv > "$OUT/lint_rc.log" 2>&1 && echo "LINT ot_hbm_svc_sm_group_rel_id_rc PASS" \
   || { echo "LINT ot_hbm_svc_sm_group_rel_id_rc FAIL (see lint_rc.log)"; fail=1; }
[ $fail = 0 ] && echo "SM_REQ_CHECK_GATE PASS" || echo "SM_REQ_CHECK_GATE FAIL"; exit $fail
