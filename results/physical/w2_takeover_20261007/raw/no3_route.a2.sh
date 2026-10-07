#!/bin/bash
# closure-loop w2-rb-safe-no3-872c56bd4 stage route attempt 2
set -o pipefail
export RUN=/srv/opentallas-scratch/claude/closure-loop/w2-rb-safe-no3-872c56bd4
export SRC=/srv/opentallas-scratch/claude/closure-loop/w2-rb-safe-no3-872c56bd4/src
export CL=/srv/opentallas-scratch/claude/closure-loop/w2-rb-safe-no3-872c56bd4/cl
export HOST=ot-epyc1tb
export NAME=w2_rb_safe_no3_872c56bd4
export LABEL=w2_rb_safe_no3_872c56bd4
export RAW_NAME=w2-rb-safe-no3-872c56bd4
export BLOCK=ot_hbm_native_frame_station_rb_NO3_SAFE
export COMMIT=872c56bd4dc37be1a0034d3c1ceee91c2858d531
export THREADS=16
export CL_PHASE=route
export CL_LABEL_SUFFIX=''
export CL_STOP_AFTER=''
export HM=0.035
[ -f /srv/opentallas-scratch/claude/closure-loop/w2-rb-safe-no3-872c56bd4/cl/calib.json ] || echo '{"calibrate": "disabled"}' > /srv/opentallas-scratch/claude/closure-loop/w2-rb-safe-no3-872c56bd4/cl/calib.json
[ -f /srv/opentallas-scratch/claude/closure-loop/w2-rb-safe-no3-872c56bd4/cl/calib.env ] && { set -a; . /srv/opentallas-scratch/claude/closure-loop/w2-rb-safe-no3-872c56bd4/cl/calib.env; set +a; }
python3 physical/hbm_w2_rb_station_20261006/run_owned.py --run /srv/opentallas-scratch/claude/closure-loop/w2-rb-safe-no3-872c56bd4/routes/w2_rb_safe_no3_872c56bd4 --no 3 --safe --core-width 520 --core-height 160 --place-density 0.40 --period-ps 730 --hold-margin-ns 0.035 --threads 16 --tag tk_W2_safe
