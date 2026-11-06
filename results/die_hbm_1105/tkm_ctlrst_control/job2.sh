#!/bin/bash
set -eu
cd /srv/opentallas-scratch2/claude/codex-hbm-tkm-proof
export OBJCACHE= CCACHE_DISABLE=1
/home/ubuntu/.local/opentallas-tools/bin/verilator --binary -O1 -CFLAGS -O1 --output-split 20000 -j 4 -Wno-fatal -Wno-lint -Wno-style --x-assign 0 --x-initial 0 -GRSTP=1500 --top-module tb_tkm_root_ctlrst --Mdir obj2 tb.sv old.sv new_mut.sv sram.v > build2.log 2>&1
set +e
./obj2/Vtb_tkm_root_ctlrst > mutant2.log 2>&1
rc=$?
set -e
echo MUTANT_RC=$rc >> mutant2.log
if [ "$rc" = 0 ]; then echo MUTANT_MISSED; exit 1; fi
grep SUMMARY mutant2.log
grep -q "mismatches=0 " mutant2.log && exit 1
printf "MUTANT_CAUGHT\n"
