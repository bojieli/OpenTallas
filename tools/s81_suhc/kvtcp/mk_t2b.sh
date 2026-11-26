#!/bin/bash
# S81-KVTC-PINS: T2B place + GRT-it0 probe kit = probe_v11 (S81-KVLEAF-T2, 17.86M total GRT congestion) with ONLY the
# kvtc view replaced by a position-major kvtcp view and the bars re-seated for its height (reseat.py; arr v11 / v12).
# usage: mk_t2b.sh LABEL ARR LEF LIB
set -euo pipefail
T=/srv/opentallas-scratch2/claude/S81-KVTC-PINS/t2b; L=$1; A=$2; LEF=$3; LIB=$4
P=$T/$L; test ! -e $P
mkdir -p $P
rsync -a $T/base_v11/ $P/ --exclude macro_place.tcl --exclude flow.log --exclude grt_it0.log --exclude grt_it0_congestion.rpt
cp $LEF $P/macros/dsfd_su_t_kvtc.lef; cp $LIB $P/macros/dsfd_su_t_kvtc_tt.lib
python3 -I $T/reseat.py $T/base_v11 $LEF $A $P
sed -i "s/^export DESIGN_NICKNAME = .*/export DESIGN_NICKNAME = kvleaf_t2b_kvtcp_$L/" $P/config.mk
sed -i "s#kvleaf_t2b_probe_v11#kvleaf_t2b_kvtcp_$L#" $P/grt_it0.tcl
grep -q "kvleaf_t2b_kvtcp_$L" $P/grt_it0.tcl
echo "S81-KVTC-PINS probe: probe_v11 + kvtcp view $(sha256sum $LEF | cut -c1-12) bars $A; place + GRT-it0 only; not a release" > $P/PROBE_ONLY.txt
sha256sum $P/macros/* $P/macro_place.tcl > $P/inputs.sha256
echo "KIT $P"
