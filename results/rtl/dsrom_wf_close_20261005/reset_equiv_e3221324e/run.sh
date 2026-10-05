#!/usr/bin/env bash
set -euo pipefail
source ~/.opentallas-env
W=/srv/opentallas-scratch/codex/dsrom-wf-ctrl/wt-equiv-e3221324e
O=/srv/opentallas-scratch/codex/dsrom-wf-ctrl/reset_equiv_e3221324e
run_case() {
  name=$1; shift
  /srv/opentallas-scratch/admit.sh 12 -- bash "$W/tools/dsrom_wfc_reset_reference_recipe.sh" "$O/$name" "$@"
  echo "$name PASS" >> "$O/summary.txt"
}
for cfg in "1 16 12 20 60 3" "2 40 37 5 10 1" "3 40 40 3 200 2" "4 64 50 40 30 4" "5 16 16 2 6 2" "6 33 33 8 0 5" "7 70 66 4 3 2" "8 100 100 1 2 1"; do
  read -r seed maxu users clat pdly plen <<< "$cfg"
  run_case "src_seed${seed}_maxu${maxu}" -GLOCKSTEP=0 -GSEED="$seed" -GMAXU="$maxu" -GUSERS="$users" -GCLAT="$clat" -GPDLY="$pdly" -GPLEN="$plen"
done
for seed in 1 2 3; do
  run_case "stg_seed${seed}" -GSOURCE=0 -GSEED="$seed" -GMAXU=$((seed*20)) -GUSERS=$((seed*15)) -GRXWORDS=$((seed*3)) -GXWORDS=$((seed*2+1))
done
run_case s1_u866 -GSOURCE=1 -GLOCKSTEP=0 -GMAXU=866 -GUSERS=866 -GSEED=11 -GCLAT=6 -GPDLY=40
run_case s0_u866 -GSOURCE=0 -GMAXU=866 -GUSERS=866 -GSEED=13 -GNJOBS=20000 -GXWORDS=46 -GRXWORDS=41
run_case lat12k -GSOURCE=1 -GLOCKSTEP=0 -GMAXU=866 -GUSERS=32 -GSEED=21 -GCLAT=12000 -GPDLY=600 -GPLEN=2 -GGEN=10 -GMAXCYC=100000000
echo '14 retained cases PASS'
