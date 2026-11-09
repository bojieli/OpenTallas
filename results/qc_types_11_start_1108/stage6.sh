#!/bin/bash
# QC-TYPES-11: private hardlink copy of the wave src + rsync to the compose source tree bytes (rsync replaces via temp+rename: never writes a shared inode).
set -eu
CT=/srv/opentallas-scratch2/claude/qct10/ctlm/src_ctlmfq; W=/srv/opentallas-scratch2/claude/qct11/wave
SRC=/srv/opentallas-scratch3/claude/codex-qc-compose-1113/src_fixed; Q=/srv/opentallas-scratch3/claude/qct11/start
R=$(readlink -f $CT); test -d $R; mkdir -p $W; test ! -e $W/src
cp -al $R $W/src; find $W/src -type d -exec chmod u+w {} +
rsync -rcL --delete --no-inplace --exclude=.git $SRC/ $W/src/
echo RSYNC_DONE; find $W/src -type f -links 1 | wc -l
rsync -rcLn --delete --itemize-changes --exclude=.git $SRC/ $W/src/ | wc -l
mkdir -p $W/plan; cp $Q/plan/plan_qc53v4nS.json $W/plan/; cp -rL /srv/opentallas-scratch3/claude/codex-qc-compose-1113/plan/cores $W/plan/cores
sha256sum $W/plan/plan_qc53v4nS.json | cut -c1-12
