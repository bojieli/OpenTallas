#!/bin/bash
# run_die_cfg_boot.sh OUT (KVJ-F 2026-10-17, stub audit K-12 / coordinator 0da (d)): ECTL cfg + regional reset release
# delays through the boot dispatcher (DIECFG=1 pre-boot target 10) into qkd_kv_die_cfg; tb_kv_die_cfg_boot.sv.
#   must PASS: SCN 0 (load, aligned re-release of 43 real qkd_rst_region roots, die cfg kept, full 1..9/0 -> setup_ready),
#              SCN 1 (no die cfg image -> never setup_ready), SCN 2 (late target 10 refused), SCN 3 (bad padding refused)
#   must FAIL: die cfg MUT 1 (B/C swapped) and 3 (region one off) in SCN 0, MUT 2 (padding unchecked) in SCN 3
#   regression (DIECFG=0 = the KVJ-A dispatcher): KVJ-A lockstep vs 73d265953 (MUT_B 0 PASS / 4 FAIL), dispatcher + 160
#   real boot CDCs (MUT 0 PASS / 4 FAIL), unit receipt (run_boot_dispatch.py)
set -u
O=$(readlink -f "$1"); mkdir -p "$O"; W=$(pwd)
S=rtl/qwen_sys/static_kv_20261014
rc=0
run(){ # tag scn mut expect
  iverilog -g2012 -o "$O/$1" -P tb_kv_die_cfg_boot.SCN=$2 -P tb_kv_die_cfg_boot.MUT=$3 $S/qkd_kv_die_cfg.sv \
    $S/qkd_static_kv_boot_dispatch.sv rtl/qwen_sys/split_20261014/qkd_rst_region.sv rtl/test/qwen_static_kv/tb_kv_die_cfg_boot.sv \
    > "$O/$1.build.log" 2>&1 || { echo "BUILD FAIL $1"; rc=1; return; }
  l=$(vvp -n "$O/$1" 2>&1 | tee "$O/$1.log" | grep -E '^(PASS|FAIL) kv_die_cfg_boot' | tail -1)
  echo "$1 (must $4): ${l:-no result line}"
  case "$l" in $4*) ;; *) rc=1;; esac
}
for s in 0 1 2 3; do run scn$s $s 0 PASS; done
run mut1 0 1 FAIL; run mut3 0 3 FAIL; run mut2 3 2 FAIL
E=results/rtl/qwen_kv_boot_dispatch_cdc_join_1017
( cd "$O" && for m in 0 4; do
   iverilog -g2012 -s tb_static_boot_dispatch_lockstep -Ptb_static_boot_dispatch_lockstep.MUT_B=$m -o l$m.sim $W/$E/base_dispatch.sv \
     $W/$S/qkd_static_kv_boot_dispatch.sv $W/rtl/test/qwen_static_kv/tb_static_boot_dispatch_lockstep.sv && vvp -n l$m.sim > lockstep_m$m.log 2>&1
   iverilog -g2012 -s tb_static_boot_dispatch_cdc -Ptb_static_boot_dispatch_cdc.MUT=$m -o c$m.sim $W/rtl/lib/ot_reset_sync.sv \
     $W/rtl/lib/ot_async_fifo.sv $W/$S/qkd_static_kv_boot_cdc.sv $W/$S/qkd_static_kv_boot_dispatch.sv \
     $W/rtl/test/qwen_static_kv/tb_static_boot_dispatch_cdc.sv && vvp -n c$m.sim > cdc_m$m.log 2>&1
  done; rm -f *.sim )
for f in lockstep_m0 lockstep_m4 cdc_m0 cdc_m4; do echo "regression $f: $(grep -E 'PASS|FAIL|FATAL|fatal' "$O/$f.log" | head -1)"; done
grep -q '^PASS dispatcher lockstep' "$O/lockstep_m0.log" && grep -q 'observed negative MUT4' "$O/lockstep_m4.log" && grep -q '^PASS' "$O/cdc_m0.log" && ! grep -q '^PASS' "$O/cdc_m4.log" || rc=1
python3 tools/qwen_static_kv/run_boot_dispatch.py --out "$O/unit" > "$O/unit.log" 2>&1 && echo "regression unit receipt: PASS" || { echo "regression unit receipt: FAIL"; rc=1; }
[ $rc = 0 ] && echo "PASS die_cfg_boot: 4 scenarios, 3 mutants caught, KVJ-A dispatcher regressions unchanged at DIECFG=0" || echo "FAIL die_cfg_boot"
exit $rc
