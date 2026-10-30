#!/bin/bash
set -euo pipefail
Q=/srv/opentallas-scratch2/claude; R=$Q/codex-qc-import-0824; O=$Q/die-qc39/leaf_geom; P=$Q/die-qc38/leaf_apply/provider
docker run --rm --name dqc39-leafgeom-$$ --memory=40g --memory-swap=40g --cpus=4 -v "$Q:$Q" -w "$O" openroad/orfs:asap7lock bash -c "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; trap \"chown -R 1000:1000 $O\" EXIT; openroad -python -exit $R/src/export_geometry119.py --odb $P/provider.odb --out $O > $O/export.log 2>&1"
