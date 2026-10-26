#!/bin/bash
set -eu
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
openroad -no_init -exit fixture.tcl > fixture.log 2>&1
openroad -no_init -exit readback.tcl > readback.log 2>&1
if openroad -no_init -exit fixture_obs_mutant.tcl > obs_mutant.log 2>&1; then exit 1; fi
grep -q 'original pin/OBS geometry changed' obs_mutant.log
cp pdn_bbox_obs.py pdn_bbox_obs.good.py
cp pdn_bbox_obs_pg_mutant.py pdn_bbox_obs.py
trap 'cp pdn_bbox_obs.good.py pdn_bbox_obs.py' EXIT
if openroad -no_init -exit fixture.tcl > pg_mutant.log 2>&1; then exit 1; fi
grep -q 'pin/outline mismatch' pg_mutant.log
cp pdn_bbox_obs_cover_mutant.py pdn_bbox_obs.py
if openroad -no_init -exit fixture.tcl > cover_mutant.log 2>&1; then exit 1; fi
grep -q 'obstruction coverage shrank' cover_mutant.log
