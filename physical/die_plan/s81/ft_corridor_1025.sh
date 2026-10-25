#!/bin/bash
# S81-PLAN/FTCHAN 10-25: corridor FT siting for the 9 non-leaf types PROTO G2 classed STRUCTURAL (GRT overflow 2.8k-305k:
# whole ft bundles routed around the svc hcore grid / col ROM blocks in 20-40-um margins, each station's bits stacked at
# one point).  Edits die_plan.json IN PLACE: only these types' ft_slots regs_um / bit_sites_um change (stations, windows,
# pins, cores, outlines unchanged).  Bundles run straight over the cores on M6/M7; station registers sit in the
# inter-core channels / gaps the corridor crosses, one bit per legal site in bit order.
#   col_*: ft0 (E->W 1104 b, window y 980-1220 over the top ROM element): each station takes the gaps above/below the
#   element (a --band y 1100-1224 corridor was tried: G2 362 overflow on col_h10 vs 35 without, so no band);
#   svc_lo_dsdv_svc_rs__t7: the two N->S Z slots jog at different heights inside the sx_hrow row.
set -e
D=$(cd $(dirname $0) && pwd); ROOT=$(cd $D/../../.. && pwd)
T=svc_lo_dsdv_svc_rs_w__t1,svc_hi_dsdv_svc_rs__t3,svc_hi_dsdv_svc_rs__t4,svc_lo_dsdv_svc_rs__t7,svc_hi_dsdv_svc_rs__t5
C=col_h10_r0_p1__t1,col_h9_r0_p1__t1,col_h9_r0_p2__t1,col_h9_r0_p3__t1
python3 $ROOT/tools/die_plan/ft_corridor.py $D/die_plan.json --types $T,$C \
  --jog svc_lo_dsdv_svc_rs__t7/ft2=1200 --jog svc_lo_dsdv_svc_rs__t7/ft1=1265 --ledger $D/ft_corridor_ledger.json

# S81-PLAN3 10-25: svc_hi_dsdv_svc_rs__t1 (was not in the FTCHAN run)
# python3 $ROOT/tools/die_plan/ft_corridor.py $D/die_plan.json --types svc_hi_dsdv_svc_rs__t1 --ledger $D/ft_corridor_ledger_plan3.json
