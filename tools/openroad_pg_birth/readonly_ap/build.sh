#!/bin/bash
set -euo pipefail
cd /work
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
expected=21eda99eeae7eccb22ca64ad28949c08a6c01dcece3ccb23e2206d635f8d2846
binary=$(command -v openroad)
actual=$(sha256sum "$binary" | cut -d' ' -f1)
[ "$actual" = "$expected" ] || exit 2
[ ! -e /work/apreader.so ] || exit 2
g++ -std=c++20 -O2 -shared -fPIC -I/work/include -I/usr/include/tcl8.6 /work/ap_reader.cpp -o /work/apreader.so
sha256sum "$binary" /work/ap_reader.cpp /work/apreader.so > /work/build.sha256
