#!/bin/bash
# closure-loop dshead-elemB-ss-a318fdf47 stage hold_eco attempt 2
set -o pipefail
export RUN=/srv/opentallas-scratch2/scratch/claude/closure-loop/dshead-elemB-ss-a318fdf47
export SRC=/srv/opentallas-scratch2/scratch/claude/closure-loop/dshead-elemB-ss-a318fdf47/src
export CL=/srv/opentallas-scratch2/scratch/claude/closure-loop/dshead-elemB-ss-a318fdf47/cl
export HOST=ot-epyc2
export NAME=dshead_elemB_ss_a318fdf47
export LABEL=dshead_elemB_ss_a318fdf47
export RAW_NAME=dshead-elemB-ss-a318fdf47
export BLOCK=ot_dsrom_head_elem_B
export COMMIT=a318fdf478cdce66e0b03d9d357fec14106713dd
export THREADS=8
export CL_PHASE=hold_eco
export CL_LABEL_SUFFIX=''
export CL_STOP_AFTER=''
[ -f /srv/opentallas-scratch2/scratch/claude/closure-loop/dshead-elemB-ss-a318fdf47/cl/calib.json ] || echo '{"calibrate": "disabled"}' > /srv/opentallas-scratch2/scratch/claude/closure-loop/dshead-elemB-ss-a318fdf47/cl/calib.json
[ -f /srv/opentallas-scratch2/scratch/claude/closure-loop/dshead-elemB-ss-a318fdf47/cl/calib.env ] && { set -a; . /srv/opentallas-scratch2/scratch/claude/closure-loop/dshead-elemB-ss-a318fdf47/cl/calib.env; set +a; }
HM=18 SM=40 FILT=40 PASSES=2 RESAWARE=1 HOLDCELLS=1 ACC_SS=15.0 ACC_FF=15.0 KEEPCLK=0 BUF=30 MACROS=physical/asap7_memory_macros/ot_rom_4096x274_m8 THREADS=8 bash /srv/opentallas-scratch2/scratch/claude/closure-loop/dshead-elemB-ss-a318fdf47/cl/hold_eco.sh /srv/opentallas-scratch2/scratch/claude/closure-loop/dshead-elemB-ss-a318fdf47/routes/dshead_elemB_ss_a318fdf47/work/orfs/results/asap7/opentallas_ot_dsrom_head_elem_asap7_dshead_elemB_ss_a318fdf47/base /srv/opentallas-scratch2/scratch/claude/closure-loop/dshead-elemB-ss-a318fdf47/routes/dshead_elemB_ss_a318fdf47/work/orfs/results/asap7/opentallas_ot_dsrom_head_elem_asap7_dshead_elemB_ss_a318fdf47/base /srv/opentallas-scratch2/scratch/claude/closure-loop/dshead-elemB-ss-a318fdf47/cl/eco-r2 ot_dsrom_head_elem_B physical/dsrom_fh_safe/gen/signoff_elemB.sdc
