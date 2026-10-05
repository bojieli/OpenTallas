#!/bin/bash
# Detached step-2 chain on ot-epyc1tb: build every bench in parallel, then run every case/pass in parallel.
S=/srv/opentallas-scratch/claude/qwen-rom-dspark-attn
cd $S
B=$S/src/rtl/test/nearhbm/build_nearhbm_tb_vp.sh
mkdir -p bld res logs
st() { echo "$(date -u +%FT%TZ) $*" >> $S/STATUS.md; }
st "chain start (source 7e55cac85)"
build() {  # name HD R FP VP VMASK
  local n=$1; shift
  ( JOBS=16 /usr/bin/time -v $B $S/bld/$n "$@" > logs/build_$n.log 2>&1; echo $? > logs/build_$n.rc ) 
}
build h16r_vp2 16 1 real 2 1 &
build h128r1_vp1 128 1 dpi 1 1 &
build h128r1_vp2 128 1 dpi 2 1 &
build h128r1_vp4 128 1 dpi 4 1 &
build h128r8_vp1 128 8 dpi 1 1 &
build h128r8_vp2 128 8 dpi 2 1 &
build h128r6_vp2 128 6 dpi 2 1 &
wait
st "builds done: $(for f in logs/build_*.rc; do echo -n "$(basename $f .rc)=$(cat $f) "; done)"
# case list: BIN VEC FIRST
: > jobs.txt
for d in v16/*/; do d=${d%/}; p=$(python3 -c "import json;print(json.load(open('$d/meta.json'))['p'])"); for ((f=0;f+2<=p;f+=2)); do echo "h16r_vp2 $d $f" >> jobs.txt; done; done
for d in v128/*/; do d=${d%/}; p=$(python3 -c "import json;print(json.load(open('$d/meta.json'))['p'])")
  for ((f=0;f<p;f++)); do echo "h128r1_vp1 $d $f" >> jobs.txt; done
  for ((f=0;f+2<=p;f+=2)); do echo "h128r1_vp2 $d $f" >> jobs.txt; done
  echo "h128r1_vp4 $d 0" >> jobs.txt
  case $d in *8189_4_normal|*8189_4_peaky)
    for ((f=0;f<p;f++)); do echo "h128r8_vp1 $d $f" >> jobs.txt; done
    for ((f=0;f+2<=p;f+=2)); do echo "h128r8_vp2 $d $f" >> jobs.txt; echo "h128r6_vp2 $d $f" >> jobs.txt; done;;
  esac
done
st "jobs queued: $(wc -l < jobs.txt)"
runone() { b=$1; d=$2; f=$3; n=${b}__$(basename $d)__$f
  [ -x bld/$b/Vtb ] || { echo "nobuild" > res/$n.json; return; }
  bld/$b/Vtb $d $f 16 750 2000000 > res/$n.json 2> res/$n.err; echo $? > res/$n.rc; }
export -f runone
cat jobs.txt | xargs -P 96 -L 1 bash -c 'runone $0 $1 $2'
st "runs done: $(ls res/*.rc | wc -l) rc files, nonzero: $(grep -L '^0$' res/*.rc | wc -l)"
echo 0 > chain.rc
