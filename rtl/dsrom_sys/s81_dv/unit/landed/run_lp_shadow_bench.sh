#!/usr/bin/env bash
# PL-SEQ (10-18): landed dsdv_seq_host bench on the S81U-SEQ GOLDEN stimulus (tb_dsdv_seq_host_lp = tb_dsdv_seq_host + the
# landed shadow dsdv_seq_host_wf_lp, lockstep at the record's port offsets).  Run on the FLEET (ot-run), never on localhost.
#   LP_MUT 0: seeds 1-4 SEQHOST PASS (flat goldens + shadow 0 mismatches);  LP_MUT 1 / 2 / 4: SEQHOST FAIL (shadow mismatches).
# Also: the tb's offset constants are checked against the record.  Prints LPSEQ_GATE PASS/FAIL.
# Usage: run_lp_shadow_bench.sh OUTDIR [seeds]
set -u
R=$(cd "$(dirname "$0")/../../../../.." && pwd)
O=${1:-$(mktemp -d)}; SEEDS=${2:-"1 2 3 4"}; mkdir -p "$O"
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
U=$R/rtl/dsrom_sys/s81_dv/unit; L=$U/landed
F="$R/rtl/lib/ot_async_fifo.sv $R/rtl/lib/ot_reset_sync.sv $R/rtl/lib/ot_rst_relay.sv $R/rtl/link/ot_link_afifo.sv
   $R/rtl/dsrom_sys/s81_ctrl/ot_s81_secded.sv $R/rtl/hdc/ingest/ot_hdc_ingest_fp8q.sv $R/rtl/hdc/ingest/ot_hdc_kv_ingest.sv
   $R/rtl/hdc/ingest/ot_rom_host_ingest.sv $R/physical/rom_host_ingest/rtl/dsfd_host.sv
   $R/rtl/dsrom_sys/s81_ingest/ot_s81_ingest_visibility_fence.sv $R/rtl/dsrom_sys/s81_ingest/dsfd_host_native.sv
   $R/rtl/dsrom_sys/s81_ingest/dsfd_host_sd.sv $R/rtl/dsrom_sys/s81_ingest/dsfd_host_c.sv
   $R/rtl/dsrom_sys/s81_static_control/ot_s81_fixed_issue.sv $U/ot_dsdv_fixed_issue.sv $U/ot_dsdv_vstop.sv $U/dsdv_sh_sd.sv $U/dsdv_seq_host.sv
   $R/physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
   $R/rtl/common/landed_parent/ot_pl_land.sv $L/dsdv_seq_host_wf_lp.sv"
bad=0
python3 - "$R" "$L/tb_dsdv_seq_host_lp.sv" <<'PY' || bad=1
import json, re, sys
r = json.load(open(sys.argv[1] + "/results/arch/landed_parent_1018/dsdv_seq_host/dsdv_seq_host_wf_lp_record.json"))
c, tb = r["compiler"], open(sys.argv[2]).read()
g = lambda k: int(re.search(rf"\b{k} = (\d+)", tb).group(1))
ii, oo = c["input_port_offset_edges"], c["output_port_offset_edges"]
ok = (g("RB") == r["reset"]["depth"] and g("OI_VN") == ii["vi_n"] and all(v == g("OI") for k, v in ii.items() if k != "vi_n")
      and g("OO_VN") == oo["vo_n"] and all(v == g("OO") for k, v in oo.items() if k != "vo_n"))
print("RECORD_OFFSETS", "MATCH" if ok else "DIFFER", ii, oo, "RB", r["reset"]["depth"])
sys.exit(0 if ok else 1)
PY
build() { l=$1; shift
  verilator --binary --timing -j 16 -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style -Wno-UNOPTFLAT +define+DSFD_HOST_C_STATIC \
    --top-module tb_dsdv_seq_host_lp "$@" --Mdir "$O/$l" -o tb $F $L/tb_dsdv_seq_host_lp.sv > "$O/build_$l.log" 2>&1 \
    || { echo "BUILD_FAIL $l (see $O/build_$l.log)"; return 2; }
}
build base || exit 2
for s in $SEEDS; do
  "$O/base/tb" +seed=$s > "$O/run_s$s.log" 2>&1
  grep -E '^SEQHOST (seed|LP_SHADOW)' "$O/run_s$s.log"; grep -q '^SEQHOST PASS' "$O/run_s$s.log" || { echo "seed $s FAIL"; bad=1; }
done
for m in 1 2 4; do
  build lpmut$m +define+LP_MUT=$m || { bad=1; continue; }
  "$O/lpmut$m/tb" +seed=1 > "$O/run_lpmut$m.log" 2>&1
  if grep -q '^SEQHOST PASS' "$O/run_lpmut$m.log"; then echo "LP mutant $m NOT detected"; bad=1
  else echo "LP mutant $m detected: $(grep -m1 '^SEQHOST LP_SHADOW' "$O/run_lpmut$m.log")"; fi
done
[ $bad = 0 ] && echo "LPSEQ_GATE PASS" || echo "LPSEQ_GATE FAIL"
exit $bad
