#!/bin/bash
# die-evidence-2 r25gp-power: run r25gp_block_power_cg.tcl on one routed / post-CTS block database (host-side wrapper).
# usage: r25gp_power_run.sh <BASE> <tag> <odb> <sdc> <spef|-> [mem_gb]
#   BASE holds r25gp_block_power_cg.tcl and libs/ (physical/asap7_memory_macros + physical/hbm_accel_macros);
#   writes BASE/out/<tag>.kv, BASE/out/<tag>.log and BASE/out/<tag>.src (db / sdc / spef paths + sha256).
set -u
B=$1 T=$2 ODB=$3 SDC=$4 SPEF=$5 MEM=${6:-16}
mkdir -p $B/out
[ "$SPEF" = "-" ] && SPEF=""
{ echo "odb $ODB $(sha256sum $ODB | cut -c1-64)"; echo "sdc $SDC $(sha256sum $SDC | cut -c1-64)"
  [ -n "$SPEF" ] && echo "spef $SPEF $(sha256sum $SPEF | cut -c1-64)"; echo "host $(hostname)"; } > $B/out/$T.src
/srv/opentallas-scratch/admit.sh $MEM -- docker run --rm --name r25gp_pw_$T --memory=$((MEM*2))g -v /srv:/srv \
  -e PW_ODB=$ODB -e PW_SDC=$SDC -e PW_SPEF="$SPEF" -e PW_MACRO_LIBS=$B/libs -e PW_OUT=$B/out/$T.kv \
  openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -threads 4 -no_init -exit $B/r25gp_block_power_cg.tcl > $B/out/$T.log 2>&1; echo \$? > $B/out/$T.rc; chmod -R a+rwX $B/out"
