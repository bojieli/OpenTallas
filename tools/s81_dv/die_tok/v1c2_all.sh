#!/bin/bash
# TOK-DS-2 V1c2: fresh hierarchical build with ot_s81c_attn_hcore as its own hier block (the 16 svc_rs/pvso partitions each
# hold 64 hcores and blew 64 GB per frontend), V1c bench (KS + PROG), then run_v1c (base/mut/noks/rom + check_seqhost)
set -u
R=/srv/opentallas-scratch2/claude/tok-ds-2
J=${J:-12} $R/build_v1c2.sh || exit $?
B=$R/bin_v1c/Vtb_s81_die W=$R/chk O=$R/run_v1c $R/run_v1c.sh
