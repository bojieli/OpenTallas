#!/bin/bash
# collect MUQWREG legs back to LOCAL dir ($1, default ~/scratch/refill-0730/MUQWREG/collected) and print table leg | expect | got
set -u
D=/srv/opentallas-scratch/claude/refill-0730/MUQWREG; C=${1:-/home/ubuntu/scratch/refill-0730/MUQWREG/collected}
L=/home/ubuntu/scratch/refill-0730/MUQWREG/legs; mkdir -p $C/out $C/runs $C/client
SSH='ssh -o ControlPath=none -o ConnectTimeout=15'
for h in ot-agidock128 ot-pve1; do mkdir -p $C/host/$h/out $C/host/$h/runs
  rsync -a -m -e "$SSH" --include='*/' --include='*.out' --include='*.txt' --include='*.log' --include='*.json' --exclude='obj*/' --exclude='*build.log' --exclude='*' $h:$D/out/ $C/host/$h/out/ 2>/dev/null
  rsync -a -m -e "$SSH" --include='*/' --include='*.out' --include='*.log' --include='*.txt' --exclude='*' $h:$D/src/results/rtl/mu_qwen_1018/ $C/host/$h/runs/ 2>/dev/null
done
# merge: per relative path keep the copy that is complete (has '# exit' / 'overall rc' / 'BENCHES'), else the larger
python3 - "$C" <<'PY'
import sys, os, shutil
C = sys.argv[1]; best = {}
for h in os.listdir(f"{C}/host"):
    for top in ("out", "runs"):
        b = f"{C}/host/{h}/{top}"
        for dp, _, fs in os.walk(b):
            for f in fs:
                p = os.path.join(dp, f); rel = os.path.join(top, os.path.relpath(p, b)); t = open(p, errors="replace").read()
                score = (("# exit" in t) or ("overall rc" in t) or ("BENCHES" in t) or ("summary" in f), len(t))
                if rel not in best or score > best[rel][0]: best[rel] = (score, p)
for rel, (_, p) in best.items():
    d = os.path.join(C, rel); os.makedirs(os.path.dirname(d), exist_ok=True); shutil.copy2(p, d)
PY
cp $L/*.log $C/client/
find $C -type d -empty -delete
row() { printf "| %s | %s | %s |\n" "$1" "$2" "$3"; }
echo "| leg | expect | got |"; echo "|---|---|---|"
for f in $L/*.log; do n=$(basename $f .log)
  rc=$(grep -o "RAN on [^ ]*.*exit [0-9]*" $f | tail -1); [ -z "$rc" ] && rc="$(grep -o 'NOT [A-Z]*' $f | tail -1)"; [ -z "$rc" ] && rc=RUNNING
  o=$C/out/$n.out
  case $n in
   host) row host "MU1 PASS, cm/hm/rm FAIL, 12 ex identical" "$rc; $(grep -c '' $C/out/host/runs/summary.txt 2>/dev/null) cases; $(grep -ciE 'differs' $o 2>/dev/null) DIFFERS";;
   *) last=$(grep -E "PASS|FAIL|BAD|OK " $o 2>/dev/null | tail -1 | cut -c1-140); row $n "-" "$rc; ${last:-no out}";;
  esac
done
