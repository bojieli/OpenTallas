#!/bin/bash
# KV-CTL10: every PASS case and mutant of run_kv_ctl_c32.sh, 4 in parallel; out/rc.txt one line a case
set -u
cd "$(dirname "$(readlink -f "$0")")/../../.." || exit 2
mkdir -p out
printf '%s\n' dcfg m_dc6 m_dc7 tile_a tile_b first_a m_tl kb_a kb_b kb_first | xargs -P 5 -I{} bash -c 'bash rtl/test/kv_ctl10_1020/run_kv_ctl_c32.sh . out {} > out/{}.stdout 2>&1; echo "RC $? {} $(tail -1 out/{}.stdout)"' > out/rc.txt
cat out/rc.txt; echo DONE
