#!/usr/bin/env bash
# hgi-adapters: ot_hgi_sm_record bench.  usage: run_sm.sh <outdir> [MUT_ROWS|MUT_EARLY]
exec bash "$(dirname "$0")/run_small.sh" sm "$@"
