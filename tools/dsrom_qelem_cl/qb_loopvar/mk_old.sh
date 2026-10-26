#!/bin/bash
# mk_old.sh REPO OLD_SHA OUTDIR: the q-element source list (rtl_list.txt) at OLD_SHA with every module DECLARED in that list
# renamed <name>_old (declarations + instantiations), so old and new elements can sit side by side in one bench / LEC
# design.  Modules not declared in the list (ROM macros, ICG cells) keep their names (shared fixtures / black boxes).
set -eu
R=$1; OLD=$2; O=$3; D=$(cd "$(dirname "$0")" && pwd)
rm -rf "$O"; mkdir -p "$O"
L=$(cat "$D/rtl_list.txt")
git -C "$R" archive "$OLD" $L | tar -x -C "$O"
MODS=$(cd "$O" && cat $L | grep -oE '^\s*module\s+[A-Za-z_][A-Za-z0-9_]*' | awk '{print $2}' | sort -u)
EXPR=""; for m in $MODS; do EXPR="$EXPR -e s/\\b$m\\b/${m}_old/g"; done
for f in $L; do sed -i -E $EXPR "$O/$f"; done
echo "$MODS" > "$O/renamed_modules.txt"
echo "mk_old: $(echo $MODS | wc -w) modules renamed from $OLD into $O"
