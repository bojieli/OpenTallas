#!/bin/bash
set -euo pipefail
D=$(pwd)/native_source
mkdir -p "$D/clock"
cp /srv/opentallas-scratch2/claude/die-kv-21-1028/kit_c/clock/make_tracks.tcl "$D/clock/"
docker run --rm --name codex-kv-native-source-$$ --cpus=4 --memory=32g --memory-swap=32g -v "$D:/work" -w /work -e HUID=$(id -u) -e HGID=$(id -g) openroad/orfs:latest bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; CORNER=TT LIBDIR=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM openroad -no_init -threads 4 -exit /work/source_only.tcl > /work/source_only.log 2>&1; rc=$?; chown -R $HUID:$HGID /work; exit $rc'
