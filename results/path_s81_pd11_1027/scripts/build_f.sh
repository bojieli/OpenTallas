#!/bin/bash
# PATH-S81-PD11: die clock mesh build (mirror re-site) on the ADOPTED band plan d (die_plan_pd7_composed.json), lattice c (= lat_pd7b + band_root_depth balance)
# usage: build_d.sh <tag> [extra args]
N=/srv/opentallas-scratch2/claude/wt/path-s81-pd10-1027; R=/srv/opentallas-scratch2/claude/path-s81-pd11-1027; D=/srv/opentallas-scratch2/claude/path-s81-pd7-1026/d
T=$1; shift
cd $N || exit 1
echo START $(date) code $(git -C $N rev-parse --short HEAD) dirty $(git -C $N status --short tools | wc -l) plan $(sha256sum $D/src/die_plan_pd7_composed.json | cut -c1-12) > $R/$T.log
timeout 1800 python3 tools/die_plan/die_clock_mesh.py build $D/src/die_plan_pd7_composed.json --out $R/$T --nx 64 --ny 64 --m 2 --ndr 4w \
  --reserve-cell-sites --track-file $D/kit/grt/tracks.tcl --lattice-spec results/path_s81_pd11_1027/lat_pd11${LAT:-f}.json --delta-id D-S81-CLKMESH-PD11 "$@" >> $R/$T.log 2>&1
echo EXIT $? >> $R/$T.log
