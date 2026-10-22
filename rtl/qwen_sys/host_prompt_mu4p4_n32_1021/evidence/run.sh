#!/bin/bash
set -euo pipefail
cd /srv/opentallas-scratch/claude/qe3-prompt35-p4n32
T=qkd_hr_core_prompt_mu4p4_n32
python3 host_prompt_native32.py --netlist original.v --parser textbook_lint.py --sha256 ede6faacb7c0535ff93e6097d7bfffda1a4bcf6d3fbbcdf9bb020ddf5b7d8d81 --top $T --out $T.sv > generate.log 2>&1
cp original.v original.v.keep
docker run --rm -u $(id -u):$(id -g) -v $PWD:/work openroad/orfs:asap7lock bash /work/host_prompt_resynth.sh $T > resynth_docker.log 2>&1
python3 host_prompt_census.py $T > census.log 2>&1
python3 host_prompt_reset_profile.py $T > reset_profile.log 2>&1 || true
echo P4N32_DONE
