#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
sha256sum -c MODEL_INPUT_SHA256SUMS
python3 kit/model.py >model.log 2>&1
sha256sum out/* >MODEL_OUTPUT_SHA256SUMS
