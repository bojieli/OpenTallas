#!/bin/bash
# $1 = tag (TT|FF|zero), $2 = obj suffix, rest = extra verilator args (defines)
R=/srv/opentallas-scratch2/claude/tok-head-land-2; tag=$1; sfx=$2; shift 2
cd /srv/opentallas-scratch2/claude/wt/tok-head-land-2
exec /home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -Wno-PINMISSING --top-module tb -f $R/die_$tag.f --Mdir $R/obj_$tag$sfx --build-jobs 16 -MAKEFLAGS "OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0" "$@" > $R/build_$tag$sfx.log 2>&1
