#!/bin/bash
cd /srv/opentallas-scratch2/claude/qwen-fullwidth-r2
R=/srv/opentallas-scratch2/claude/qwen-fullwidth-r2/source-59da397a9/tools/qwen_rom_combined_p0_20261005/run_full.py
/srv/opentallas-scratch/admit.sh 64 -- python3 $R --output /srv/opentallas-scratch2/claude/qwen-fullwidth-r2/full-r2 --source /srv/opentallas-scratch2/claude/qwen-fullwidth-r2/source-59da397a9 --stage build --workers 16 > build_driver.log 2>&1; echo $? > build.rc
[ $(cat build.rc) = 0 ] || { echo BUILD_FAIL > TERMINAL; exit 1; }
( /srv/opentallas-scratch/admit.sh 16 -- python3 $R --output /srv/opentallas-scratch2/claude/qwen-fullwidth-r2/full-r2 --source /srv/opentallas-scratch2/claude/qwen-fullwidth-r2/source-59da397a9 --stage layer-runtime > layer_driver.log 2>&1; echo $? > layer.rc ) &
/srv/opentallas-scratch/admit.sh 16 -- python3 $R --output /srv/opentallas-scratch2/claude/qwen-fullwidth-r2/full-r2 --source /srv/opentallas-scratch2/claude/qwen-fullwidth-r2/source-59da397a9 --stage runtime > runtime_driver.log 2>&1; echo $? > runtime.rc
python3 /srv/opentallas-scratch2/claude/qwen-fullwidth-r2/source-59da397a9/tools/qwen_rom_combined_p0_20261005/check_fullwidth.py --output /srv/opentallas-scratch2/claude/qwen-fullwidth-r2/full-r2 > check.log 2>&1; echo $? > check.rc
wait; echo DONE > TERMINAL
