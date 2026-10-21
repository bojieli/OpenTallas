#!/bin/bash
# S81-RTLGAP/RG-ENG (10-21): fleet runner of tb_dsdv_eng_rr (Engram row-read path + join, dsdv_eng_rr.sv).
#   run_eng_rr.sh <git ref> <work dir>   (on a fleet host with the git mirror; Verilator 5.050 = the closure daemon's)
# Builds base + 4 mutants (XQ_MUT 1/2, TAP_MUT 1/2), runs each, python bit-exact check (hdc_golden_v41), writes
# <work>/check.json {pass, mutants[{name, failed, log}]} and keeps every run log.
set -u
REF=${1:?ref}; W=$(realpath -m ${2:?work}); mkdir -p $W/src
G=${OT_GIT_DIR:-/srv/opentallas-scratch/claude/git-mirror/OpenTallas.git}
VL=${VL:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
git --git-dir=$G cat-file -e "$REF^{commit}" 2>/dev/null || git --git-dir=$G fetch -q origin ${BR:-claude/s81-eng640-1021}
F=(rtl/dsrom_sys/s81_dv/ot_s81dv_fp_n32.sv rtl/dsrom_sys/s81_dv/ot_s81dv_finish_sram.sv
   rtl/hdc/v41/ot_hdc_engram_tables_shipped_pkg.sv rtl/hdc/v41/ot_hdc_engram_hash_shipped.sv
   rtl/dsrom_sys/engram/static_lookup_1015/ot_s81_engram_rowbank_static_leaf.sv
   rtl/dsrom_sys/engram/static_lookup_1015/ot_s81_engram_hash_static.sv
   rtl/dsrom_sys/engram/static_lookup_1015/ot_s81_engram_lookup_static.sv
   rtl/dsrom_sys/engram/static_lookup_1015/dsfd_engram_lkp_static14.sv
   rtl/dsrom_sys/engram/static_lookup_1015/ot_s81_engram_lookup_ra512.sv rtl/dsrom_sys/engram/static_lookup_1015/dsfd_engram_lkp_ra512.sv
   rtl/dsrom_sys/engram/static_lookup_1015/ot_s81_engram_hash_n32.sv
   rtl/dsrom_sys/engram/static_lookup_1015/ot_s81_engram_lookup_ra640.sv rtl/dsrom_sys/engram/static_lookup_1015/dsfd_engram_lkp_ra640.sv
   physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
   rtl/dsrom_sys/s81_ph/ctrl/dsfd_ctrl_rg3.sv rtl/dsrom_sys/s81_ph/ctrl/ot_s81ph_ctrl_pcr.sv rtl/lib/ot_rst_relay.sv rtl/lib/ot_rst_relay_bounded32.sv rtl/dsrom_sys/s81_dv/eng/ot_s81eng_reset3n32.sv
   rtl/dsrom_sys/s81_glue/dsfd_rly_masters_dv276.sv rtl/dsrom_sys/s81_glue/ot_s81_rly.sv
   rtl/dsrom_sys/s81_ph/ctrl/ot_s81ph_afifo_g_sram.sv rtl/dsrom_sys/s81_ph/ctrl/ot_s81ph_afifo_g.sv rtl/dsrom_sys/s81_ph/ot_s81ph_afifo.sv
   physical/asap7_memory_macros/ot_sram_1r1w2c_16x340_p192/ot_sram_1r1w2c_16x340_p192.v
   physical/asap7_memory_macros/ot_sram_1r1w2c_16x546_m1/ot_sram_1r1w2c_16x546_m1.v
   physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v
   physical/asap7_memory_macros/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v
   physical/asap7_memory_macros/ot_rom_4096x72_m8/ot_rom_4096x72_m8.v
   rtl/hdc/ot_hdc_delay.sv rtl/dsrom_sys/engram/ot_dsrom_engram_token_map.sv rtl/hdc/v41/ot_hdc_engram_gather.sv
   rtl/dsrom_sys/s81_dv/slice/ot_s81sl_aq12x.sv rtl/hdc/ot_hdc_fastfp_lat_f12.sv rtl/hdc/ot_hdc_prefix.sv
   rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_fp32_f12.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fastfp.sv
   rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/proto/ot_fp32_add_rne_pipe.sv
   rtl/dsrom_sys/s81_dv/eng/ot_s81eng_rr_n32.sv rtl/dsrom_sys/s81_dv/eng/ot_s81eng_aq_n32.sv rtl/dsrom_sys/s81_dv/eng/dsdv_eng_rr.sv rtl/dsrom_sys/s81_dv/eng/test/tb_dsdv_eng_rr.sv)
git --git-dir=$G archive "$REF" "${F[@]}" tools/hdc_golden.py tools/hdc_golden_v41.py tools/s81_dv/eng_rr | tar -xf - -C $W/src
cd $W/src; git --git-dir=$G rev-parse "$REF" > $W/ref.txt; sha256sum "${F[@]}" > $W/sources.sha256
$VL --version > $W/verilator.version
python3 tools/s81_dv/eng_rr/prep_rom.py $W/rom
build() {  # name, -G params
  local n=$1; shift
  /usr/bin/time -v -o $W/$n.build.time $VL --binary --timing -j ${J:-16} -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH \
    -Wno-MULTIDRIVEN -Wno-UNOPTFLAT -Wno-PINMISSING -Wno-IMPLICIT -Wno-SELRANGE -CFLAGS -O1 ${TAP_N32R2:+ +define+OT_S81ENG_TAP_N32R2} ${RR_N32:+ +define+OT_S81ENG_RR_N32} ${RR_MUL_N32:+ +define+OT_S81ENG_RR_MUL_N32} +define+OT_ENGRAM_CRCMAT \
    --top-module tb_dsdv_eng_rr "$@" "${F[@]}" --Mdir $W/obj_$n -o sim > $W/$n.build.log 2>&1
  echo "$n build rc $?" >> $W/status
}
run() {   # name
  local n=$1; shift
  if [ -x $W/obj_$n/sim ]; then
    /usr/bin/time -v -o $W/$n.run.time $W/obj_$n/sim +OT_ROM_DIR=$W/rom "$@" > $W/$n.log 2>&1
    python3 tools/s81_dv/eng_rr/check_eng_rr.py $W/$n.log $W/src >> $W/$n.log 2>&1
  else echo "NO BUILD" > $W/$n.log; fi
  echo "$n: $(grep -h 'TB_ENG_RR PASS\|TB_ENG_RR FAIL' $W/$n.log | tail -1) $(grep -h 'ENG_RR_PY PASS\|ENG_RR_PY FAIL' $W/$n.log | tail -1)" >> $W/status
}
if [ "${BASE_ONLY:-0}" = 1 ]; then build base; run base; cat $W/status; grep -m20 '%Error' $W/base.build.log; tail -30 $W/base.log; exit 0; fi
build base &
build xq1 -GXQ_MUT=1 &
build xq2 -GXQ_MUT=2 &
build tap1 -GTAP_MUT=1 &
build tap2 -GTAP_MUT=2 &
build rpar +define+OT_ENGRAM_MUT_RA512_PAR &
build onesc +define+OT_ENGRAM_MUT_ONESCALE &
wait
run base; run xq1; run xq2; run tap1; run tap2; run rpar; run onesc
n=base; for a in "+SEED=2 +LAT=160" "+SEED=3 +LAT=60"; do /usr/bin/time -v -o $W/var.run.time $W/obj_base/sim +OT_ROM_DIR=$W/rom $a > $W/var_${a//[ +=]/_}.log 2>&1; python3 tools/s81_dv/eng_rr/check_eng_rr.py $W/var_${a//[ +=]/_}.log $W/src >> $W/var_${a//[ +=]/_}.log 2>&1; echo "base $a: $(grep -h 'TB_ENG_RR PASS\|TB_ENG_RR FAIL' $W/var_${a//[ +=]/_}.log) $(grep -h 'ENG_RR_PY PASS\|ENG_RR_PY FAIL' $W/var_${a//[ +=]/_}.log)" >> $W/status; done
python3 - $W <<'PY'
import json, sys, re
from pathlib import Path
w = Path(sys.argv[1])
def verdict(n):
    t = (w / f'{n}.log').read_text()
    return ('TB_ENG_RR PASS' in t) and ('ENG_RR_PY PASS' in t)
muts = [dict(name=n, failed=not verdict(n), log=f'{n}.log') for n in ('xq1', 'xq2', 'tap1', 'tap2', 'rpar', 'onesc')]
j = dict(bench='tb_dsdv_eng_rr', ref=(w / 'ref.txt').read_text().strip(), pass_=verdict('base'), mutants=muts)
j['pass'] = j.pop('pass_')
(w / 'check.json').write_text(json.dumps(j, indent=1) + '\n')
print('ENG_RR_CHECK', 'PASS' if j['pass'] and all(m['failed'] for m in muts) else 'FAIL', json.dumps(j))
PY
cat $W/status
