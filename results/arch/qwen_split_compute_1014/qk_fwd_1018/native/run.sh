#!/bin/bash
# QK-FWD 10-18: native_pin_audit (main 0dq rule + --case) of the closed 1-bit landings; plain / case k0..k2 / relative
cd "$(dirname "$0")"; D=$PWD; A="python3 $D/hier_contract/native_pin_audit.py --root $D"
V(){ local d=v/$1/physical/ref_tile/${1%%-*}/views; echo $d/$(ls $d | head -1); }
LE=qfwd_landh_1_ew_65x30-f2-9ddc1acf2; LN=qfwd_landh0_1_ns_65x30-f2-9ddc1acf2; SN=qfwd_rlyh_1_sn_65x30-f1-93960f2c9; SW=qfwd_rlyh0_1_sw_65x30-f2-9ddc1acf2
mkdir -p out
for j in $LE $LN $SN $SW; do $A --view $(V $j) > out/$j.plain.json; echo "$j plain rc=$?"; done
for j in $LE $LN; do $A --view $(V $j) --case k0,k1,k2 > out/$j.case.json; echo "$j case rc=$?"; done
$A --view $(V $LE) --case k0,k1,k2 --relative-to $D/$(V $SN) > out/$LE.case_rel_sn.json; echo "$LE case+rel(rlyh_1_SN) rc=$?"
$A --view $(V $LN) --case k0,k1,k2 --relative-to $D/$(V $SW) > out/$LN.case_rel_sw.json; echo "$LN case+rel(rlyh0_1_SW src-root neighbour) rc=$?"
