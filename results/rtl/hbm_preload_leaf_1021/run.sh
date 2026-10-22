#!/usr/bin/env bash
set -euo pipefail
mkdir -p out
VL=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
"$VL" --version > out/tool_version.txt
for version in old fixed;do
 "$VL" --binary --timing --unroll-count 16384 --unroll-stmts 4000000 -Wno-fatal -j 2 --top-module tb_preload -Mdir out/$version tb_preload.sv $version.sv > out/$version.build.log 2>&1
 sha256sum out/$version/Vtb_preload > out/$version.binary.sha256
 if [ "$version" = old ];then
  if out/old/Vtb_preload +HBM_IMG_DIR=img > out/old.log 2>&1;then echo OLD_UNEXPECTED_PASS;exit 4;fi
  grep PRELOAD_READBACK out/old.log
 else
  out/fixed/Vtb_preload +HBM_IMG_DIR=img > out/fixed.log 2>&1
  grep PRELOAD_FOUR_INSTANCE_READBACK_PASS out/fixed.log
 fi
done
