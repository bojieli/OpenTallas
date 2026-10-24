#!/bin/bash
# KV-P3-RTL 10-23: START-only HC transport (qkd_host_ctrl_token_service_packet_collected_mu HCW 39) == the 182-bit
# original with PW/DW zero, in lockstep inside the 8-die MU e2e bench (rtl/test/mu_qwen_1018/tb_mu_peer_e2e.sv: 4 users
# x 3 rounds through the whole die-0 coordinator chain; every one of the 8 transports is an hc39_lockstep pair).
# REF = the transport at REF_COMMIT (before HCW), renamed qkd_ts182_ref_mu.  Verilator 5.050.  Run from the repo root.
# usage: run.sh [OUT]
#   eq        PASS: tb PASS and 0 mismatches on all 8 dies       eq_abort  same with +ABORT (package abort, 3 retained users)
#   mutants (must be CAUGHT = mismatches > 0 or tb FAIL), applied to the HCW 39 DUT only:
#     m1  peers drop the START bit of a received hc (hc<=h[48+:HCW]&~START_EV)
#     m2  root corrupts one command field (pos bit 0) entering the command queue
#     m3  die 0 drops the START bit of its own granted local hc (hc<=active&~START_EV at grant)
#   rsv       PASS: a peer frame with the PW/DW field set: REF takes it, HCW 39 faults (tb_hc39_rsv.sv)
#     m4  (rsv) the class-22 decode without the reserved-field check: must FAIL
#   (a mutant on the abort-with-queued-START load path is NOT caught: this bench never queues a START behind an abort)
set -u
R=$(pwd); O=${1:-hc39_equiv_out}; mkdir -p "$O"; O=$(cd "$O" && pwd)
REF_COMMIT=${REF_COMMIT:-27befae4f}
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$V" --version | grep -q 'Verilator 5.050' || { echo "HC39_EQUIV: not Verilator 5.050"; exit 2; }
L=rtl/test/mu_qwen_1018/lists/tb_mu_peer_e2e.f; D=rtl/test/qwen_host/hc39_equiv
TS=rtl/qwen_sys/mu_qwen_20261018/qkd_host_ctrl_token_service_packet_collected_mu.sv
TB=rtl/test/mu_qwen_1018/tb_mu_peer_e2e.sv
sub(){ python3 - "$1" "$2" "$3" <<'PY'
import sys
p, a, b = sys.argv[1:]; s = open(p).read()
assert s.count(a) == 1, (p, a, s.count(a)); open(p, 'w').write(s.replace(a, b))
PY
}
one(){ # name plusarg mut_from mut_to
  local n=$1 pa=$2 W="$O/src_$1"; rm -rf "$W"; mkdir -p "$W"
  while read -r f; do mkdir -p "$W/$(dirname "$f")"; cp "$R/$f" "$W/$f"; done < "$R/$L"
  git -C "$R" show "$REF_COMMIT:$TS" | sed 's/^module qkd_host_ctrl_token_service_packet_collected_mu #/module qkd_ts182_ref_mu #/' > "$W/ref182.sv"
  grep -q '^module qkd_ts182_ref_mu #' "$W/ref182.sv" && ! grep -q HCW "$W/ref182.sv" || { echo "HC39 $n: bad REF"; return 2; }
  cp "$R/$D/hc39_lockstep.sv" "$W/"
  sub "$W/$TB" 'qkd_host_ctrl_token_service_packet_collected_mu #(.STRAPPED(1),.ENABLE_SERVICE(1),.ENABLE_TOKEN(1),.MU(1))ts(' \
               'hc39_lockstep #(.STRAPPED(1),.ENABLE_SERVICE(1),.ENABLE_TOKEN(1))ts(' || return 2
  # the abort checks read die 0's retained-user register: now one level down, in the DUT
  [ "$(grep -o 'g_ts\[0\]\.ts\.g_mu\.' "$W/$TB" | wc -l)" = 4 ] || { echo "HC39 $n: tb probe count"; return 2; }
  sed -i 's/g_ts\[0\]\.ts\.g_mu\./g_ts[0].ts.u_dut.g_mu./g' "$W/$TB"
  [ -n "$3" ] && { sub "$W/$TS" "$3" "$4" || return 2; }
  (cd "$W" && "$V" --binary --timing -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -Wno-UNOPTFLAT -Wno-WIDTH \
     --top-module tb_mu_peer_e2e -Mdir obj -j 4 -o sim $(cat "$R/$L") ref182.sv hc39_lockstep.sv > "$O/$n.build" 2>&1) \
     || { echo "HC39 $n: BUILD-ERR"; grep %Error "$O/$n.build" | head; return 2; }
  (cd "$W" && ./obj/sim $pa > "$O/$n.log" 2>&1); rm -rf "$W/obj"
  local tbr mis nl; tbr=$(grep -E '^(PASS|FAIL)' "$O/$n.log" | tail -1)
  nl=$(grep -c '^HC39_LOCKSTEP' "$O/$n.log"); mis=$(grep '^HC39_LOCKSTEP' "$O/$n.log" | sed 's/.*mismatches=\([0-9]*\).*/\1/' | paste -sd+ | bc)
  echo "HC39 $n: lockstep_dies=$nl mismatches=${mis:-?} tb: $tbr"
  grep '^HC39_LOCKSTEP' "$O/$n.log" | sed 's/^/   /'
  if [ "$nl" = 8 ] && [ "${mis:-1}" = 0 ] && [[ "$tbr" == PASS* ]]; then return 0; else return 1; fi
}
rc=0
one eq '' '' '' || rc=1
one eq_abort +ABORT '' '' || rc=1
for m in m1 m2 m3; do
  case $m in
   m1) a='hc<=h[48+:HCW];'; b='hc<=h[48+:HCW]&~START_EV;'; pa='';;
   m2) a='cq[cw]<=cd;'; b="cq[cw]<=cd^HCW'(1);"; pa='';;
   m3) a='hc<=active;local_emitted<=1;token_epoch_valid<='; b='hc<=active&~START_EV;local_emitted<=1;token_epoch_valid<='; pa='';;
  esac
  one $m "$pa" "$a" "$b"; r=$?
  if [ $r = 1 ]; then echo "HC39 $m: CAUGHT"; else echo "HC39 $m: NOT CAUGHT (rc=$r)"; rc=1; fi
done
# rsv: peer receive of a frame whose PW/DW field is set (tb_hc39_rsv.sv): REF takes it, HCW 39 faults; mutant m4 drops
# the reserved-field check from the class-22 decode (the DUT then silently truncates) and must FAIL.
rsv(){ local n=$1 W="$O/src_$1"; rm -rf "$W"; mkdir -p "$W/$(dirname "$TS")"
  cp "$R/$TS" "$W/$TS"; [ -n "$2" ] && { sub "$W/$TS" "$2" "$3" || return 2; }
  git -C "$R" show "$REF_COMMIT:$TS" | sed 's/^module qkd_host_ctrl_token_service_packet_collected_mu #/module qkd_ts182_ref_mu #/' > "$W/ref182.sv"
  "$V" --binary --timing -Wno-fatal -Wno-lint -Wno-style --top-module tb_hc39_rsv -Mdir "$W/obj" "$R/$D/tb_hc39_rsv.sv" "$W/ref182.sv" \
    "$W/$TS" "$R/rtl/qwen_sys/host_integrated_20261014/qkd_host_ctrl_token_service_packet_collected.sv" > "$O/$n.build" 2>&1 \
    || { echo "HC39 $n: BUILD-ERR"; return 2; }
  "$W/obj/Vtb_hc39_rsv" > "$O/$n.log" 2>&1; rm -rf "$W/obj"
  echo "HC39 $n: $(grep -E '^(PASS|FAIL)' "$O/$n.log")"; grep -q '^PASS' "$O/$n.log" && return 0 || return 1; }
rsv rsv '' '' || rc=1
rsv m4 "src==0&&hc_rsv_ok&&"$'\n' "src==0&&"$'\n'; r=$?
if [ $r = 1 ]; then echo "HC39 m4: CAUGHT"; else echo "HC39 m4: NOT CAUGHT (rc=$r)"; rc=1; fi
[ $rc = 0 ] && echo 'HC39_EQUIV_SUITE PASS eq eq_abort (8 dies lockstep, 0 mismatches) rsv + 4 mutants caught' || echo 'HC39_EQUIV_SUITE FAIL'
exit $rc
