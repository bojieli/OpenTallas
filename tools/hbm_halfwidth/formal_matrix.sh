#!/bin/bash
D=$(cd "$(dirname "$0")" && pwd)
for a in "9 2 24 0 0 2" "9 0 20 0 0 2" "8 1 24 0 0 4" "9 2 30 0 0 4" "10 0 30 0 0 4"; do $D/run_formal.sh $a; done   # expect PROVEN
for a in "9 2 24 1 0 2" "9 2 24 0 5 2" "9 2 24 0 6 2" "9 2 30 1 0 4" "9 2 30 0 5 4" "9 2 30 0 6 4" "9 2 30 0 7 4"; do $D/run_formal.sh $a; done   # expect COUNTEREXAMPLE
