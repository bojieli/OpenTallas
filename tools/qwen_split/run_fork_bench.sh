#!/bin/bash
set -eu
MODE=$1;MUT=$2;R=$3
mkdir -p "$R"
if [ "$MODE" = selector ];then TB=-DOT_TEST_SELECTOR_FORK;DUT=rtl/qwen_split/qfd_static_selector_fork26.sv;D=-DOT_QFD_SELECTOR_FORK_MUT;else TB=;DUT=rtl/qwen_split/qfd_static_command_fork42.sv;D=-DOT_QFD_COMMAND_FORK_MUT;fi
[ "$MUT" = 1 ]||D=
iverilog -g2012 $TB $D -s tb -o "$R/bench" "$DUT" rtl/test/qwen_command_fork/tb.sv
vvp "$R/bench"
