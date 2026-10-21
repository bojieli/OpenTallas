#!/bin/bash
set -euo pipefail
O=$(mkdir -p ../out_seq_exact;cd ../out_seq_exact;pwd)
# Exact selected profile from10cbb2c45 committed seqhost/benches.sh, plus CSA.
export VL_EXTRA='-DOT_N32_ADDR_CSA -DOT_S81_SH_APIPE9 -DOT_S81_SH_APIPE10 -DOT_S81_SH_SRAM -DOT_S81_SH_RSZ -DOT_S81_SH_S10B -DOT_S81_SH_S10C -DOT_S81_SH_S10D -DOT_S81_SH_S10E -DOT_S81_SH_ACKP -DTB_HSH=8 -DTB_HSC=9'
bash rtl/dsrom_sys/s81_dv/unit/test/run_seq_host_bench.sh "$O/seqhost" '1 2' base > "$O/run.log" 2>&1
cat "$O/run.log"
