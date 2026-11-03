#!/usr/bin/env bash
set -euo pipefail
# No native SYNTH/proof invocation is currently authorized by this packet.
# Remove this deliberate refusal only in a fresh root-reviewed successor.
printf '%s\n' 'PREP_ONLY: pinned fragment readset and execution scope require review' >&2
exit 70
