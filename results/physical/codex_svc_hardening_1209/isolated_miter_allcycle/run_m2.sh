#!/bin/bash
# tightened SML miter: o_mx all cycles after first valid; hold-removed mutant must be caught
M=/srv/opentallas-scratch2/claude/codex-svc-hardening-1209/sml_isolated2; cd $M
V=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator; [ -x $V ] || V=/home/ubuntu/.local/opentallas-tools/bin/verilator; [ -x $V ] || V=verilator
grep -q codex_svc_sml_isolated rtl/codex_svc_sml_native.sv || { echo "wrapper does not use isolated"; exit 9; }
SRCS=$(grep '^export VERILOG_FILES = ' config.mk | sed 's/^export VERILOG_FILES = //; s#/work/#'$M'/#g')
$V --binary --timing -O2 -Wno-fatal -Wno-WIDTH --top-module tb -Mdir obj -j 8 $SRCS tb.sv > build.log 2>&1 || { echo BUILD_FAIL; tail -5 build.log; exit 8; }
timeout 300 ./obj/Vtb > base.log 2>&1; echo "base rc $?"; grep -E 'SML_' base.log
MSRCS=$(echo $SRCS | sed "s#$M/rtl/codex_svc_sml_isolated.sv#$M/isolated_mutant.sv#")
$V --binary --timing -O2 -Wno-fatal -Wno-WIDTH --top-module tb -Mdir obj_mut -j 8 $MSRCS tb.sv > build_mut.log 2>&1 || { echo BUILD_MUT_FAIL; exit 7; }
timeout 300 ./obj_mut/Vtb > mut.log 2>&1; echo "mutant rc $?"; grep -E 'SML_' mut.log
