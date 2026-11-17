#!/bin/bash
set -euo pipefail
KIND=${1:?head|lane|station_repeat|sender|late_payload}
WORK=${2:?fresh scratch directory}
HERE=$(cd -- "$(dirname -- "$0")" && pwd)
REPO=$(cd "$HERE/../../../.." && pwd)
case "$KIND" in head|lane|station_repeat|sender|late_payload);;*)exit 2;;esac
mkdir "$WORK"
if [ "$KIND" = head ] || [ "$KIND" = lane ];then
 tar -xzf "$REPO/results/rtl/qc_round96_1116/source_capsule.tar.gz" -C "$WORK"
 if [ "$KIND" = head ];then cp "$WORK/head_round96.sv" "$WORK/head.sv";fi
else
 cp "$REPO/results/rtl/qc_stn55_1116/source_capsule.tar.gz" "$WORK/"
fi
cp "$HERE/$KIND/"* "$WORK/"
cd "$WORK"
bash run.sh
