#!/bin/bash
set -eu
source ~/.opentallas-env
cd /srv/opentallas/repos/OpenTallas-git
git -c gc.auto=0 fetch origin codex/russell-dsrom-reindex-parallel-20261005
for V in u40 u45 split2; do
 WT=/srv/opentallas/repos/russell-reindex-parallel-$V-20261005
 git -c gc.auto=0 worktree add --detach "$WT" e73b07389
 git -C "$WT" sparse-checkout set --no-cone tools rtl/hdc/v41x rtl/test rtl/experimental/dsrom_reindex_kc7_20261005 rtl/experimental/dsrom_reindex_kc7_split_20261005 results/rtl/dsrom_1m_measured_20261004 results/rtl/dsrom_reindex_kc7_20261005 results/uarch/dsrom_reindex_parallel_20261005 results/arch
 D=/srv/opentallas-scratch/codex/russell-reindex-parallel-20261005/$V
 if test -e "$D"; then echo 'REFUSE existing variant output'; exit 1; fi
 mkdir -p "$D"
 setsid bash /srv/opentallas-scratch/codex/russell-reindex-parallel-job.sh "$V" > "$D/launch.log" 2>&1 < /dev/null &
 echo "$V launch_PID=$!"
 echo "$!" > "$D/launcher.pid"
done
