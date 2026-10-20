#!/bin/bash
set -eu
export PYTHONPATH="$PWD/pylib:$PWD/completecand/tools/ref_tile:$PWD/completecand/tools"
python3 -m pytest -p no:cacheprovider -q -o addopts="" provenancecand/tools/ref_tile/tests/test_native_census.py > provenance_target.log 2>&1
