#!/bin/bash
# MU-ADOPT-HROOT 10-19: host-root endpoint / epoch allocator / KV layer programme for 4 users.  Verilator 5.050 (the
# closure daemon's version).  usage: run_mu_hroot.sh ROOT OUT CASE
#   MU 1 PASS : tb_mu_hroot_e2e | tb_mu_hroot_collide (negative control, must report the collision fault) |
#               tb_mu_lprg_lockstep (MU 0 == original; MU 1 user 0 gap 0 == original) | tb_mu_lprg_lockstep_s2 |
#               lint_guard_mu (the MU 1 qkd_hr_core_guard with its member sources)
#   MU 0 ident: ex_endpoint (existing bench, original) | ex_endpoint_mu0 (same bench, endpoint -> _mu #(MU 0)) |
#               ex_lifecycle (existing bench) | ex_lifecycle_mu0 (lifecycle binds the allocator _mu #(MU 0))
#   mutants (must FAIL): ep1 ep2 al1 al2 kp1 kp2 kp3
# Every file a case reads is in lists/<tb>.f.
set -u
ROOT=$(cd "${1:?root}" && pwd); OUT=${2:?out}; CASE=${3:?case}
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
L=$(dirname "$(readlink -f "$0")")/lists
mkdir -p "$OUT"; OUT=$(cd "$OUT" && pwd)
M=rtl/qwen_sys/mu_qwen_20261018
EP=$M/qkd_host_native_token_endpoint_cancel_mu.sv; AL=$M/ot_qwen_tp8_token_epoch_allocator_mu.sv
KP=$M/qkd_static_kv_layer_programme_mu.sv
TB=$CASE; MF=""; FROM=""; TO=""; PA=""; TOP=""
case "$CASE" in
 tb_mu_hroot_collide) TB=tb_mu_hroot_e2e; PA=+COLLIDE;;
 tb_mu_lprg_lockstep_s2) TB=tb_mu_lprg_lockstep; PA=+SEED=1234;;
 ex_endpoint) TB=tb_qkd_host_native_token_endpoint_cancel;;
 ex_endpoint_mu0) TB=tb_qkd_host_native_token_endpoint_cancel; MF=rtl/test/qwen_host/tb_qkd_host_native_token_endpoint_cancel.sv
   FROM='qkd_host_native_token_endpoint_cancel #(.ENABLE_NATIVE(1),.MUT(MUT))d'; TO='qkd_host_native_token_endpoint_cancel_mu #(.ENABLE_NATIVE(1),.MUT(MUT),.MU(0))d';;
 ex_lifecycle) TB=tb_qkd_host_lifecycle_collected;;
 ex_lifecycle_mu0) TB=tb_qkd_host_lifecycle_collected; MF=rtl/qwen_sys/host_integrated_20261014/qkd_host_lifecycle_collected.sv
   FROM='ot_qwen_tp8_token_epoch_allocator #(.INITIAL_EPOCH(INITIAL_EPOCH)) allocator'; TO='ot_qwen_tp8_token_epoch_allocator_mu #(.INITIAL_EPOCH(INITIAL_EPOCH),.MU(0)) allocator';;
 # endpoint keeps the single-user position check (pos[17:13] == 0): users 1..3 are protocol faults
 ep1) TB=tb_mu_hroot_e2e; MF=$EP; FROM='hc_q[15:13]==0'; TO='hc_q[17:13]==0';;
 # endpoint retire waits for the global drains although other users are in flight
 ep2) TB=tb_mu_hroot_e2e; MF=$EP; FROM='(MUT==1||drains||!alone)'; TO='(MUT==1||drains)';;
 # allocator epoch without the user in its low bits
 al1) TB=tb_mu_hroot_e2e; MF=$AL; FROM='g_epoch <= {seq[ureq], ureq};'; TO='g_epoch <= {seq[ureq], 2'"'"'b00};';;
 # allocator single-busy (one allocation for all users, as the original)
 al2) TB=tb_mu_hroot_e2e; MF=$AL; FROM='!ubusy[ureq] && !grant_pending'; TO='!(|ubusy) && !grant_pending';;
 # KV programme: user not taken from the epoch (every start lands in context 0)
 kp1) TB=tb_mu_hroot_e2e; MF=$KP; FROM="wire[1:0]us=epoch_q[1:0];"; TO="wire[1:0]us=2'd0;";;
 # KV programme: metadata follow the previous owner, not the firing context
 kp2) TB=tb_mu_hroot_e2e; MF=$KP; FROM='epoch<=(start_q&&start_ok&&fire_u==us)?epoch_q:c_epoch[fire_u];'; TO='epoch<=(start_q&&start_ok&&fire_u==us)?epoch_q:c_epoch[owner];';;
 # KV programme: collision detection removed (collide case must then FAIL)
 kp3) TB=tb_mu_hroot_e2e; PA=+COLLIDE; MF=$KP; FROM='wire collide=(e_any&(e_any-4'"'"'d1))!=0;'; TO="wire collide=1'b0;";;
esac
[ -f "$L/$TB.f" ] || { echo "MU_HROOT $CASE: no list $TB"; exit 2; }
W="$OUT/src_$CASE"; rm -rf "$W"; mkdir -p "$W"
while read -r f; do mkdir -p "$W/$(dirname "$f")"; cp "$ROOT/$f" "$W/$f"; done < "$L/$TB.f"
if [ -n "$MF" ]; then
  python3 - "$W/$MF" "$FROM" "$TO" <<'PY' || { echo "MU_HROOT $CASE: mutation did not apply"; exit 2; }
import sys
p, a, b = sys.argv[1], sys.argv[2], sys.argv[3]
s = open(p).read()
assert s.count(a) == 1, (a, s.count(a))
open(p, "w").write(s.replace(a, b))
PY
fi
cd "$W"
if [ "$TB" = lint_guard_mu ]; then
  "$V" --lint-only -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -Wno-UNOPTFLAT -Wno-WIDTH --top-module qkd_hr_core_guard \
    $(cat "$L/$TB.f") > "$OUT/$CASE.log" 2>&1; rc=$?
  if [ $rc = 0 ] && ! grep -qE '%Error|PINMISSING|PINNOTFOUND|PINCONNECTEMPTY' "$OUT/$CASE.log" \
     && grep -q 'qkd_host_native_token_endpoint_cancel_mu' "$L/$TB.f"; then
    echo "PASS LINT_GUARD_MU qkd_hr_core_guard (u_rank__u_native = qkd_host_native_token_endpoint_cancel_mu, MU 1)" >> "$OUT/$CASE.log"
  else echo "FAIL LINT_GUARD_MU rc=$rc" >> "$OUT/$CASE.log"; fi
  echo "MU_HROOT $CASE: $(tail -1 "$OUT/$CASE.log")"; grep -q '^PASS' "$OUT/$CASE.log"; exit
fi
"$V" --binary --timing -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -Wno-UNOPTFLAT -Wno-WIDTH \
  --top-module "$TB" -Mdir obj -j ${VJ:-4} -o sim $(cat "$L/$TB.f") > "$OUT/$CASE.build" 2>&1 \
  || { echo "MU_HROOT $CASE: BUILD-ERR"; tail -20 "$OUT/$CASE.build"; exit 1; }
./obj/sim $PA > "$OUT/$CASE.log" 2>&1; rc=$?
r=$(grep -E '^(PASS|FAIL)|^%Error|Fatal|fatal' "$OUT/$CASE.log" | tail -1)
echo "MU_HROOT $CASE rc=$rc: $r"
rm -rf "$W/obj"
[ $rc = 0 ] && grep -q '^PASS' "$OUT/$CASE.log"
