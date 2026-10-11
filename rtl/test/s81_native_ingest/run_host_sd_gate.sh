#!/bin/bash
# s81-svceng-1011 host side gate: tb_dsfd_host_sd (Verilator 5 --binary --timing).  Bases (must PASS): NS 1 (KVS 1, ENG -1),
# NS 2 (KVS 01, ENG 1 = layer1e), NS 4 (KVS 1111, ENG -1), 2 seeds each.  Negatives (must FAIL): MUT 1 wrong KV decode (NS 4),
# MUT 2 dropped credit return, MUT 3 Engram -> stack 0 (NS 2), TBMUT 1 invalid marker class.
# Usage (repo root): run_host_sd_gate.sh <out> [one <name> <args...>]   exit 0 iff PASS (one: the run's rc, 1 = FAIL)
set -u
O=$1; mkdir -p $O
F="rtl/lib/ot_rst_relay.sv rtl/dsrom_sys/s81_ingest/dsfd_host_sd.sv rtl/test/s81_native_ingest/tb_dsfd_host_sd.sv"
run() { n=$1; shift
  verilator --binary --timing -Wno-fatal -Wno-lint -Wno-style --top-module tb_dsfd_host_sd -Mdir $O/obj_$n "$@" $F > $O/$n.build 2>&1 || { echo BUILD_FAIL > $O/$n.log; return 2; }
  $O/obj_$n/Vtb_dsfd_host_sd > $O/$n.log 2>&1; grep -q '^PASS' $O/$n.log && return 0 || return 1; }
if [ "${2:-}" = one ]; then shift 2; run "$@"; rc=$?; echo "HOST_SD_ONE $1 rc=$rc"; exit $rc; fi
for c in "ns1a -GNS=1 -GKVS=1 -GENG=-1 -GSEED=1" "ns1b -GNS=1 -GKVS=1 -GENG=-1 -GSEED=2" \
         "ns2a -GNS=2 -GKVS=1 -GENG=1 -GSEED=3" "ns2b -GNS=2 -GKVS=1 -GENG=1 -GSEED=4" \
         "ns4a -GNS=4 -GKVS=15 -GENG=-1 -GSEED=5" "ns4b -GNS=4 -GKVS=15 -GENG=-1 -GSEED=6" \
         "mut1 -GNS=4 -GKVS=15 -GENG=-1 -GMUT=1" "mut2 -GNS=2 -GKVS=1 -GENG=1 -GMUT=2" "mut3 -GNS=2 -GKVS=1 -GENG=1 -GMUT=3" \
         "badcls -GNS=2 -GKVS=1 -GENG=1 -GTBMUT=1"; do
  set -- $c; ( run "$@"; echo $? > $O/$1.rc ) &
done; wait
v=PASS; line=""
for n in ns1a ns1b ns2a ns2b ns4a ns4b; do r=$(cat $O/$n.rc); line="$line $n=$r"; [ $r -eq 0 ] || v=FAIL; done
for n in mut1 mut2 mut3 badcls; do r=$(cat $O/$n.rc); line="$line $n=$r"; [ $r -eq 1 ] || v=FAIL; done
echo "HOST_SD_GATE $v$line" | tee $O/verdict.log
[ $v = PASS ]
