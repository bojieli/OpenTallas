#!/bin/bash
# Per-stage REAL_MEM AR256 jobs (layer-parallel) for one position. Usage: launch_jobs.sh P [stage ...]
# Each job: one stage (E, L<n>, head) or a chained list "A,B,C", entered from the GPU golden exit of the previous stage.
R=/srv/opentallas-scratch/claude/realmem-fulltoken
P=$1; shift
G=$R/gold/P$P
TOK=$(python3 -c "import json;print(json.load(open('$G/embedding_row.json'))['token'])")
IMG=/srv/opentallas-scratch/claude/layer-parallel-sim/img256
EDIR=/srv/opentallas-scratch/claude/realmem/stages/E
line() {  # stage -> stage line
  case $1 in
    E) echo "E $EDIR $EDIR $EDIR $EDIR 0";;
    head) echo "head $IMG/head-d0 $IMG/head-d1 $IMG/head-d2 $IMG/head-d3 0";;
    L*) n=${1#L}; echo "$1 $IMG/L$n-d0 $IMG/L$n-d1 $IMG/L$n-d2 $IMG/L$n-d3 1";;
  esac
}
prev() { case $1 in E|L0) echo "";; head) echo L35;; L*) echo L$(( ${1#L} - 1 ));; esac; }
for spec in "$@"; do
  name=${spec//,/+}
  J=$R/runs/P$P/$name
  [ -e $J/launched ] && continue
  mkdir -p $J
  : > $J/stages.txt
  for s in ${spec//,/ }; do line $s >> $J/stages.txt; done
  first=${spec%%,*}
  pv=$(prev $first)
  if [ -z "$pv" ]; then cp $G/x_preload.hex $J/entry.hex
  else n=$(printf %02d ${pv#L})
    for d in 1 2 3; do cmp -s $G/L${n}_die0_x.hex $G/L${n}_die${d}_x.hex || { echo "golden exit $pv differs between dies" > $J/error; exit 2; }; done
    { echo @1000; cat $G/L${n}_die0_x.hex; } > $J/entry.hex
  fi
  cat > $J/run.sh <<EOF
#!/bin/bash
cd $R/src-fddd78ca1
echo "\$(date -Is) START P$P $name" >> $R/jobs/MANIFEST
/srv/opentallas-scratch/admit.sh 16 -- /usr/bin/time -f "%M %e %U %S" -o $J/time.txt python3 tools/qwen_rom_rt_token_w12_rm.py --real-mem \
  --workdir $J/w --build-dir $R/build-ar256-h36 --stages $J/stages.txt --oracle $G --pos $P --token $TOK \
  --enable-ar256 --coll-depth 256 --hbm-layers 36 --threads ${THREADS:-2} --x-preload $J/entry.hex --result $J/result.json > $J/driver.log 2>&1
echo \$? > $J/exit
echo "\$(date -Is) END P$P $name exit=\$(cat $J/exit)" >> $R/jobs/MANIFEST
EOF
  chmod +x $J/run.sh
  touch $J/launched
  setsid -f nohup $J/run.sh > /dev/null 2>&1 < /dev/null
  sleep ${STAGGER:-20}
done
