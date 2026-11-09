#!/bin/bash
# QC-TYPES-11: private hardlink copy of this host's src_ctlmfq, rsynced (temp+rename, never in place) to epyc6 wave src; plan + bind copied.
set -eu
CT=/srv/opentallas-scratch2/claude/qct10/ctlm/src_ctlmfq; W=/srv/opentallas-scratch2/claude/qct11/wave; E=epyc6
SSH="ssh -o ControlPath=none -o ConnectTimeout=15"
test ! -e $W/src
R=$(readlink -f $CT); test -d $R; mkdir -p $W
if [ "$(stat -c %d $R)" != "$(stat -c %d $(dirname $W))" ]; then RD=$(dirname $R)/qct11_wave_src; test ! -e $RD; cp -al $R $RD; ln -s $RD $W/src; else cp -al $R $W/src; fi
find -L $W/src -type d -exec chmod u+w {} +
rsync -rlc --delete --no-inplace --exclude=.git -e "$SSH" $E:$W/src/ $W/src/
rsync -rlc -e "$SSH" $E:$W/plan $E:$W/bind_v4nS $W/
sha256sum $W/plan/plan_qc53v4nS.json | cut -c1-12
find -L $W/src -type d -exec chmod a-w {} +
echo STAGED $(hostname) $(df -BG --output=avail /srv/opentallas-scratch2 | tail -1)
