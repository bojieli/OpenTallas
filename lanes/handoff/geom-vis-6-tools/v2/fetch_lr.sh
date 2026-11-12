#!/bin/bash
# fetch_lr.sh S key host:/path/to/.../run
S=$1; key=$2; src=$3; host=${src%%:*}; p=${src#*:}
D=$S/v2/vis/$key; rm -rf $D; mkdir -p $D
timeout 120 ssh -n -o ControlPath=none -o ConnectTimeout=15 $host "cd '$p' && ls -d layout_review/*/*.png layout_review/*/smells.one layout_review/summary.txt 2>/dev/null | tar cf - -T - 2>/dev/null; cd ../../../geom 2>/dev/null && ls auto_geom.png auto_geom.json 2>/dev/null | tar cf - -T - 2>/dev/null" > $D/x.tar
cd $D && tar xif x.tar 2>/dev/null; rm -f x.tar
echo "$src" > $D/SRC; find $D -type f | sed "s#$D/##" | sort | tr '\n' ' '; echo
