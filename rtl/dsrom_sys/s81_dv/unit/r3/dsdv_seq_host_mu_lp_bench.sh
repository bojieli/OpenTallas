#!/usr/bin/env bash
# STW-S81c-COLLA3 10-22: dsdv_seq_host_mu_lp lockstep (base must PASS; MU_LP_MUT 1/2 and the r3_lp landing mutant LPMUT 1 must FAIL)
#   bash rtl/dsrom_sys/s81_dv/unit/r3/dsdv_seq_host_mu_lp_bench.sh OUTDIR   (cwd = repo root; VERILATOR, VL_JOBS)
set -u; OUT=${1:-mu_lp_bench}; mkdir -p "$OUT"; rc=0; R=rtl/dsrom_sys/s81_dv/unit
# file list = the r3_lp landed-band bench's (tools/s81_dv/seq_three_roots_1021/run_landing_lb.sh: run_seq_host_c_bench.sh
# sources + the r3_lp bench SRCS, lp -> lb + bands) + relay + hslot + this parent + its tb; same OT_S81_SH_* defines
python3 - "$OUT/files.txt" <<'PY'
from pathlib import Path
import re,sys
s=Path('rtl/dsrom_sys/s81_dv/unit/test/run_seq_host_c_bench.sh').read_text()
f=re.search(r'F="(.*?)"\ngrep',s,re.S).group(1).replace('$U','rtl/dsrom_sys/s81_dv/unit').replace('$R/','').split()
f=[x for x in f if x not in ['rtl/dsrom_sys/s81_dv/unit/dsdv_seq_host_c.sv','rtl/dsrom_sys/s81_dv/unit/test/dsdv_seq_host_bw.sv']]
s=Path('rtl/dsrom_sys/s81_dv/unit/r3/dsdv_seq_host_c_r3_lp_bench.sh').read_text()
f+=re.search(r'SRCS="(.*?)"\n',s,re.S).group(1).split()
u='rtl/dsrom_sys/s81_dv/unit/r3/'
f=[x for x in f if x != u+'dsdv_seq_host_c_r3_lp.sv']+[u+'dsdv_seq_host_c_r3_lb.sv',u+'dsdv_seq_host_c_r3_lb_bands.sv','rtl/lib/ot_rst_relay.sv',
   'rtl/dsrom_sys/s81_ph/ot_s81ph_mem1r1w.sv','physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v','rtl/dsrom_sys/s81_dv/unit/dsdv_mu_hslot.sv',u+'dsdv_seq_host_mu_lp.sv',u+'tb_dsdv_seq_host_mu_lp.sv']
Path(sys.argv[1]).write_text('\n'.join(dict.fromkeys(f))+'\n')
PY
mapfile -t F < "$OUT/files.txt"; sha256sum "${F[@]}" > "$OUT/sources.sha256"
DEFS="-DOT_S81_SH_APIPE9 -DOT_S81_SH_APIPE10 -DOT_S81_SH_SRAM -DOT_S81_SH_RSZ -DOT_S81_SH_S10B -DOT_S81_SH_S10C -DOT_S81_SH_S10D -DOT_S81_SH_S10E"
for c in "0 0" "1 0" "2 0" "0 1"; do set -- $c; t=m$1_l$2
  ${VERILATOR:-verilator} --binary --timing -j ${VL_JOBS:-4} -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH -Wno-MULTIDRIVEN -Wno-UNOPTFLAT -Wno-PINMISSING -Wno-IMPLICIT -Wno-SELRANGE -Wno-TIMESCALEMOD -O1 \
    $DEFS --top-module tb_dsdv_seq_host_mu_lp -GMU_LP_MUT=$1 -GLPMUT=$2 "${F[@]}" -Mdir "$OUT/obj_$t" > "$OUT/build_$t.log" 2>&1 \
    && "$OUT/obj_$t/Vtb_dsdv_seq_host_mu_lp" > "$OUT/run_$t.log" 2>&1
  r=$(grep -o 'MU_LP_LOCKSTEP [A-Z]*' "$OUT/run_$t.log" 2>/dev/null | head -1); echo "$t: ${r:-NO_RESULT} $(grep -o 'ku_valid=[0-9]*' $OUT/run_$t.log 2>/dev/null)"
  if [ "$t" = m0_l0 ]; then [ "$r" = "MU_LP_LOCKSTEP PASS" ] || rc=1; else [ "$r" = "MU_LP_LOCKSTEP FAIL" ] || rc=1; fi
done; echo "MU_LP_BENCH_EXIT $rc"; exit $rc
