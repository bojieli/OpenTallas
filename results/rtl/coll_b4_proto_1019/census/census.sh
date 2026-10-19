#!/bin/bash
set -eu
D=/srv/opentallas-scratch/claude/coll-b4-census-1019
mkdir -p "$D/out"
cp "$D/census.ys" "$D/out/census.ys"
docker run --rm --cpus=4 --memory=20g -v "$D/src:/src:ro" -v "$D/out:/out" -v "$D/map_inside.sh:/map_inside.sh:ro" -w /src openroad/orfs:asap7lock bash /map_inside.sh
