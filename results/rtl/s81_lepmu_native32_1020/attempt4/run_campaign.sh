#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
cd src
python3 campaign.py "$1"
