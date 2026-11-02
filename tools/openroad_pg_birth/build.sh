#!/bin/bash
# Run INSIDE the exact image, under normal fleet admission. Fetch headers first.
set -euo pipefail
headers=$(realpath "$1")
output=$(realpath -m "$2")
here=$(cd "$(dirname "$0")" && pwd)
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
binary=$(command -v openroad)
expected=21eda99eeae7eccb22ca64ad28949c08a6c01dcece3ccb23e2206d635f8d2846
actual=$(sha256sum "$binary" | cut -d' ' -f1)
[ "$actual" = "$expected" ] || { echo OT_PG_BIRTH_BINARY_ABI_REFUSED >&2; exit 2; }
test -f "$here/headers.json"
mkdir -p "$output"
[ ! -e "$output/nativepgbirth.so" ] || { echo 'refuse overwrite of existing module' >&2; exit 2; }
g++ -std=c++20 -O2 -shared -fPIC -pthread -I"$headers" -I/usr/include/tcl8.6 \
  "$here/native_pg_birth.cpp" -o "$output/nativepgbirth.so"
sha256sum "$binary" "$output/nativepgbirth.so" "$here/native_pg_birth.cpp" "$here/headers.json" > "$output/build.sha256"
echo NATIVE_PG_MODULE_BUILT_NOT_GLOBALLY_ENABLED
