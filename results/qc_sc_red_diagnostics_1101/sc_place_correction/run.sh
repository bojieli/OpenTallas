#!/bin/bash
set -euo pipefail
python3 prepare_points.py
g++ -O2 -std=c++17 match.cpp -o match
./match
python3 summarize.py
