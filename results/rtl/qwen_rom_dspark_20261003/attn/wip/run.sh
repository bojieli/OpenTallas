#!/bin/bash
# run.sh BIN VECDIR_GLOB... : every position pass of VP each
B=$1; shift; VP=$(basename $B | sed 's/.*vp//')
for d in "$@"; do p=$(python3 -c "import json;print(json.load(open('$d/meta.json'))['p'])")
  for ((f=0; f+VP<=p; f+=VP)); do echo "$(basename $d) first=$f $($B/Vtb $d $f ${LAT:-16} ${BPC:-750} ${MAXC:-400000} 2>/dev/null | tail -1 | python3 -c "import sys,json;r=json.loads(sys.stdin.read());print('exact',r['exact'],'mism',r['per_position_mismatches'],'fault',r['fault'],'cyc',r['cycles_total'],'mask',r['mask_ctx'])")"; done; done
