#!/bin/bash
set -euo pipefail
T=qkd_hr_core_prompt_mu4p6_n32
SHA=$(sha256sum original.v | cut -d' ' -f1)
python3 host_prompt_native32.py --netlist original.v --parser textbook_lint.py --sha256 "$SHA" --top "$T" --out "$T.sv" >generate.log 2>&1
docker run --rm -u "$(id -u):$(id -g)" -v "$PWD:/work" openroad/orfs:asap7lock bash /work/host_prompt_resynth.sh "$T" >resynth_docker.log 2>&1
python3 host_prompt_census.py "$T" >census.log 2>&1
python3 host_prompt_reset_profile.py "$T" >reset_profile.log 2>&1
echo N37_NATIVE_DONE
