#!/bin/bash
set -eu
B=$(pwd)
docker run --rm --cpus 1 --memory 4g --memory-swap 4g -v "$B":/work -w /work openroad/orfs:asap7lock bash -lc 'set -eu; source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; for n in normalized_baseline normalized_candidate_hyp normalized_candidate_miter normalized_mutant_hyp; do yosys-abc -c "&r /work/$n.aig; &fraig -C 1000; &sat -a -z -v -C 10000; &ps; &w /work/${n}_swept.aig" > /work/$n.log 2>&1; done'
