#!/bin/bash
# geo_dump.sh KIT ODB_REL OUT IX IY
K=$(cd "$1" && pwd)
docker run --rm --name qcsl2-geo-$(basename $K)-$$ --memory=8g --memory-swap=8g --cpus=1 -v $K:/work -v $(dirname $(readlink -f $0)):/s:ro openroad/orfs:asap7lock bash -c \
 "P_ODB=/work/$2 P_OUT=/work/$3 P_IX=$4 P_IY=$5 P_IS=8.64 /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /s/geo_dump.tcl" > $K/$3.log 2>&1
docker run --rm -v $K:/work openroad/orfs:asap7lock chown -R $(id -u):$(id -g) /work/$3 /work/$3.log >/dev/null 2>&1
grep -c SINK $K/$3; grep -E "^(CORE|PIN|MACRO|ISLCOUNT)" $K/$3
