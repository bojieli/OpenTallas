#!/bin/bash
# run_die_cfg_cap.sh OUT (RTL-BUILD-KV/FAULT 2026-10-18, lanes/RTL-BUILD-KV.md P8): the fused attention-programme
# capability bit loaded by the boot dispatcher (DIECAP=1, pre-boot target 10) into qkd_kv_die_cfg CAP=1 (word 32+NRST),
# tb_kv_die_cfg_boot.sv CAP=1 -- the producer of attention_programme / attn_root fused_program_capability.
#   must PASS (CAP 1): SCN 0 CAPV 1 (0 before the seal, 1 after, kept across the functional re-reset, full boot ->
#              setup_ready), SCN 0 CAPV 0 (stays 0, image still sealed), SCN 1 (no image -> no setup_ready), SCN 2 (late
#              target 10 refused), SCN 3 (ECTL padding refused), SCN 4 (capability padding refused, capability 0)
#   must FAIL: MUT 4 (bit from data[1]) and MUT 5 (not seal-gated) in SCN 0 CAPV 1; MUT 2 (padding unchecked) in SCN 4
#   regression: CAP 0 SCN 0..3 PASS (the KVJ-F die cfg unchanged)
set -u
O=$(readlink -f "$1"); mkdir -p "$O"
S=rtl/qwen_sys/static_kv_20261014
rc=0
run(){ # tag scn mut cap capv expect
  iverilog -g2012 -o "$O/$1" -P tb_kv_die_cfg_boot.SCN=$2 -P tb_kv_die_cfg_boot.MUT=$3 -P tb_kv_die_cfg_boot.CAP=$4 \
    -P tb_kv_die_cfg_boot.CAPV=$5 $S/qkd_kv_die_cfg.sv $S/qkd_static_kv_boot_dispatch.sv rtl/qwen_sys/split_20261014/qkd_rst_region.sv \
    rtl/test/qwen_static_kv/tb_kv_die_cfg_boot.sv > "$O/$1.build.log" 2>&1 || { echo "BUILD FAIL $1"; rc=1; return; }
  l=$(vvp -n "$O/$1" 2>&1 | tee "$O/$1.log" | grep -E '^(PASS|FAIL) kv_die_cfg_boot' | tail -1)
  echo "$1 (must $6): ${l:-no result line}"
  case "$l" in $6*) ;; *) rc=1;; esac
  rm -f "$O/$1"
}
run cap_scn0_v1 0 0 1 1 PASS; run cap_scn0_v0 0 0 1 0 PASS
for s in 1 2 3 4; do run cap_scn$s $s 0 1 1 PASS; done
run cap_mut4 0 4 1 1 FAIL; run cap_mut5 0 5 1 1 FAIL; run cap_mut2 4 2 1 1 FAIL
for s in 0 1 2 3; do run nocap_scn$s $s 0 0 1 PASS; done
[ $rc = 0 ] && echo "PASS die_cfg_cap: 6 CAP scenarios, 3 mutants caught, CAP 0 regression unchanged" || echo "FAIL die_cfg_cap"
exit $rc
