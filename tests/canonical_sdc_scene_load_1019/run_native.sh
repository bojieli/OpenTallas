#!/bin/bash
set -euo pipefail
IMG=openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29
sha256sum 1_synth.odb candidate.tcl old.tcl
for kind in reference reference_ff old candidate coupon_reference coupon_reference_ff coupon_old coupon_candidate; do
 helper=candidate.tcl
 if [[ "$kind" = *old ]]; then helper=old.tcl; fi
 mkdir -p out_verified/"$kind"
 docker run --rm -v "$PWD:/src" -w /src -e CASE="$kind" -e HELPER="$helper" "$IMG" /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /src/test/probe.tcl >out_verified/"$kind"/native.log 2>&1
done
