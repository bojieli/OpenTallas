#!/bin/bash
# PATH-KV-PC833 10-25: core833 controller gate (run_controller_calendar_core.py) on a generated PC KIT's RTL instead of
# the repo tree: the kit controller parent qkd_ctrl_pc_host_static_nc (qkd_ctrl_pc_nc.sv, no ci write-hold path) and
# every kit copy of the timing chain replace the repo files; the tb drives the nc parent with the exact
# qkd_static_kv_pc_path_nc u_ctrl parameters.  Heavy (Verilator): call it through ot-run.
#   kit_controller_gate.sh KIT_RTL_DIR OUT_DIR      -> OUT/proof (expect PASS) and OUT/mutant (CORE_CLOCK=0: expect PHYSICAL_MIN FAIL)
set -e
WT=$(cd "$(dirname "$0")/../.." && pwd)
K=$(cd "$1" && pwd)
mkdir -p "$2"; O=$(cd "$2" && pwd); G=$O/root
rm -rf $G; mkdir -p $G/tools/qwen_static_kv
cp $WT/tools/qwen_static_kv/controller_calendar_image.py $G/tools/qwen_static_kv/
S=$G/tools/qwen_static_kv/run_controller_calendar_core.py
cp $WT/tools/qwen_static_kv/run_controller_calendar_core.py $S
# file list: the kit controller parent (qkd_ctrl_pc_nc.sv) replaces the repo-only qkd_ctrl_pc_host_static.sv; kit tb
sed -i "s/'qkd_ctrl_pc_host_static','qkd_ctrl_pc_host_static_core'/'qkd_ctrl_pc_nc','qkd_ctrl_pc_host_static_core'/; s#rtl/test/qwen_static_kv/tb_controller_calendar_core.sv#rtl/test/qwen_static_kv/tb_controller_calendar_core_kit.sv#" $S
sed -i "s#'rtl/lib/ot_reset_sync.sv',#'rtl/lib/ot_reset_sync.sv','rtl/lib/ot_kvpc_pin_ff.sv',#" $S   # kit private-port pin flops (ot_kvpc_pin_ar0)
grep -q "ot_kvpc_pin_ff" $S && grep -q "'qkd_ctrl_pc_nc'" $S && grep -q tb_controller_calendar_core_kit $S
for f in $(python3 - "$S" <<'P'
import re,sys
t=open(sys.argv[1]).read()
names=re.search(r"for n in \[([^\]]*)\]",t).group(1)
for n in re.findall(r"'(\w+)'",names): print("rtl/qwen_sys/static_kv_20261014/"+n+".sv")
for p in re.findall(r"'(rtl/[^']+)'",t.split("]]+[",1)[1].split("]\n",1)[0]): print(p)
P
); do
  mkdir -p $G/$(dirname $f); b=$(basename $f)
  if [ -f $K/$b ]; then cp $K/$b $G/$f; echo "KIT  $f"
  elif [ $b = tb_controller_calendar_core_kit.sv ]; then
    sed 's/qkd_ctrl_pc_host_static #(.CORE_CLOCK((TIMING_MUT || DEFAULT_MITER) ? 0 : 1),.PROFILE(0),.ELASTIC(1),.RAW_WD(256),.TQD(64))dut(/qkd_ctrl_pc_host_static_nc #(.CORE_CLOCK((TIMING_MUT || DEFAULT_MITER) ? 0 : 1),.ROW0(64),.CVL(2),.HOFF(3),.WDONE(((TIMING_MUT || DEFAULT_MITER) ? 0 : 1) ? 19 : 17),.LATE(4096),.PROFILE(0),.EVMUT(0),.MUT(0),.ELASTIC(1),.RAW_WD(256),.TQD(64))dut(/; s/\.ci(319.b0),//; s/wire\[293:0\]co;/wire[281:0]co;/; s/\.fo(fault),/.fo(fault),.fo_g(),/' $WT/rtl/test/qwen_static_kv/tb_controller_calendar_core.sv > $G/$f
    # the nc controller has no ci write-hold path: no f_late / f_wmis (failure-diagnostic $display only)
    sed -i "s/dut\.u_sched\.f_late/1'b0/; s/dut\.u_sched\.f_wmis/1'b0/" $G/$f
    grep -q "qkd_ctrl_pc_host_static_nc #(" $G/$f && ! grep -q "\.ci(" $G/$f; echo "TBKIT $f"
  else cp $WT/$f $G/$f; echo "REPO $f"; fi
done
S=$G/tools/qwen_static_kv/run_controller_calendar_core.py
python3 $S $O/proof > $O/proof.log 2>&1 && echo "PROOF PASS" || { echo "PROOF FAIL (see $O/proof.log)"; exit 1; }
python3 $S $O/mutant --timing-mutant 1 > $O/mutant.log 2>&1 && echo "MUTANT caught (PHYSICAL_MIN)" || { echo "MUTANT NOT caught"; exit 1; }
