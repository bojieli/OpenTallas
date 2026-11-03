#!/usr/bin/env bash
# DIE-HBM-61/SPLIT rp3lp3h_s lock-step (S half alone): see ../rp3lp3h_n/run.sh (mode s).  run.sh KITRTL_N KITRTL_S SRAM_MODEL OUT
exec bash "$(cd "$(dirname "$0")" && pwd)/../rp3lp3h_n/run.sh" s "$@"
