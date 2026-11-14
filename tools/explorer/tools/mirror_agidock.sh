#!/bin/bash
# Standard step (COORD 2026-11-14): every signed DB pulled to rtx-pro signed-export-1114 is mirrored to AGIdock
# /archive/opentallas-signed-1114/<die>/<element>/ in the same step, sha256 verified per file. Additive: never overwrites.
# usage: mirror_agidock.sh <die> <element>
die="$1"; el="$2"; SRC=/home/ubuntu/signed-export-1114/$die/$el; DST=/archive/opentallas-signed-1114/$die/$el
A="ubuntu@155.103.253.53"; O="-i $HOME/.ssh/agidock_ot -o BatchMode=yes -o ConnectTimeout=15 -o ControlPath=none"
[ -d "$SRC" ] || { echo "$die/$el NO_SOURCE"; exit 2; }
timeout 60 ssh -n $O $A "mkdir -p $DST" || { echo "$die/$el SSH_FAIL"; exit 3; }
rc=0
for f in "$SRC"/*; do
  b=$(basename "$f"); [ -f "$f" ] || continue
  want=$(sha256sum "$f" | cut -d' ' -f1)
  have=$(timeout 600 ssh -n $O $A "[ -f $DST/$b ] && sha256sum $DST/$b | cut -d' ' -f1")
  if [ "$have" = "$want" ]; then echo "$die/$el/$b already there, sha256 ok"; continue; fi
  [ -n "$have" ] && { echo "$die/$el/$b EXISTS WITH OTHER CONTENT, not overwritten"; rc=4; continue; }
  timeout 3000 scp -q $O "$f" $A:$DST/.$b.part && got=$(timeout 600 ssh -n $O $A "sha256sum $DST/.$b.part | cut -d' ' -f1")
  if [ "$got" = "$want" ]; then timeout 60 ssh -n $O $A "mv $DST/.$b.part $DST/$b && chmod a-w $DST/$b"; echo "$die/$el/$b copied, sha256 ok $want"; else echo "$die/$el/$b SHA_MISMATCH"; rc=5; fi
done
exit $rc
