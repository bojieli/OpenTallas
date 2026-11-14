#!/bin/bash
# usage: apply.sh <src tree>   LIMIT-BIND-1 patch (base origin/main 83fc576b530; 7 tools/die_plan files). Breaks hardlinks first.
set -e; H=$(cd "$(dirname "$0")" && pwd); T=${1:?src tree}
cd "$T"
for f in $(grep "^+++ b/" $H/limit_bind_1.patch | sed "s#+++ b/##"); do [ -f "$f" ] && { cp "$f" "$f.__n" && mv -f "$f.__n" "$f"; }; done
patch -p1 --forward -s < $H/limit_bind_1.patch && echo "LIMIT-BIND-1 applied to $T"
sha256sum $(grep "^+++ b/" $H/limit_bind_1.patch | sed "s#+++ b/##")
