#!/bin/bash
# ELEM-QK: dump a kit's ODB (default 3_place) for geometry review.  dump_kit.sh KITDIR [STAGE]
K=$(cd "$1" && pwd); S=${2:-3_place}; T=$(cd "$(dirname "$0")" && pwd)
cp "$T/kvg3_dump.py" "$K/kvg3_dump.py"
O=$(ls $K/run/results/asap7/*/base/$S.odb | head -1); O=/work/${O#$K/}
docker run --rm -v "$K":/work -e ODB=$O -e OUT=/work/dump_$S.json openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -python -exit /work/kvg3_dump.py >/work/dump_$S.log 2>&1; chown $(id -u):$(id -g) /work/dump_$S.*"
ls -la $K/dump_$S.json
