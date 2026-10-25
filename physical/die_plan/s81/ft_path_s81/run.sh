#!/bin/bash
# PATH-S81/FT 10-25: structural FT corridor re-plan of svc_hi_dsdv_svc_rs__t6 (svc_15) and ot_s81sl_leaf__t55 (s_6S_L4)
# from PLAN3 WIP e64fb49ff1.  Run from the repo root on the e64 plan (idempotent per type: all re-placed slots recomputed).
set -euo pipefail
P=physical/die_plan/s81/die_plan.json; D=physical/die_plan/s81/ft_path_s81
python3 tools/die_plan/ft_corridor.py $P --types ot_s81sl_leaf__t55 --routes $D/t55_routes.json --out /tmp/plan_t55.json --ledger $D/t55_ledger.json
python3 $D/mk_hi_t6.py /tmp/plan_t55.json /tmp/plan_t55_hi_in.json $D/hi_t6_routes.json
python3 tools/die_plan/ft_corridor.py /tmp/plan_t55_hi_in.json --types svc_hi_dsdv_svc_rs__t6 --split-bits svc_hi_dsdv_svc_rs__t6/ft1=123 --split-bits svc_hi_dsdv_svc_rs__t6/ft2=123 --routes $D/hi_t6_routes.json --out $P --ledger $D/hi_t6_ledger.json
