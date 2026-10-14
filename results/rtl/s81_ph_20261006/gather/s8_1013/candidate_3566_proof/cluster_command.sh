#!/bin/bash
set -euo pipefail
SSA2=1 LOCAL_BANKS=1 DIE_CLOCKS=1 CONTROL_STRIP=1 SS=8 J=4 bash /srv/opentallas-scratch/codex/s81-gather-leaf-v18/3566a4825/src/rtl/dsrom_sys/s81_ph/test/run_gather_cl.sh /srv/opentallas-scratch/codex/s81-gather-leaf-v18/3566a4825/src /srv/opentallas-scratch/codex/s81-gather-leaf-v18/3566a4825/cluster_ssa2 /srv/opentallas-scratch/codex/s81-gather-leaf-v18/3566a4825/src/rtl/dsrom_sys/s81_ph/test/real_order_trace.json "2 20"
