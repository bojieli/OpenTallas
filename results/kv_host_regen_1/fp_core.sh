#!/bin/bash
# KV-HOST-REGEN-1 10-27: main hr_face_ports.sh (unchanged) for one core; its three proofs (same .ys files) run in parallel.
# usage: fp_core.sh MODULE DOCKER_MEM_GB
set -u
MOD=$1; MEM=$2
R=/srv/opentallas-scratch2/claude/kv-host-regen-1
M=/srv/opentallas-scratch2/claude/wt/kv-host-regen-1
O=$R/fp/$MOD; rm -rf $O; mkdir -p $O
cat > $O/inner.sh <<IN
set -u
Y=/OpenROAD-flow-scripts/tools/install/yosys/bin/yosys
cd $M
YOSYS=$R/bin/yosys_defer bash physical/die_plan/qwen_kvsys/cores/harden/hr_face_ports.sh $R/rtl/$MOD/${MOD}_core.json $O > $O/stage1.log 2>&1
if ! grep -q 'post rc=99' $O/eq_rc.txt || ! grep -q 'emitted_v rc=99' $O/eq_rc.txt; then echo STAGE1_FAIL; tail -5 $O/stage1.log; chown -R 1000:1000 $O; exit 2; fi
rm -f $O/eq_rc.txt
for V in post mut v; do ( date +%s > $O/t0_\$V; \$Y -q -l $O/eq_\$V.log $O/eq_\$V.ys >/dev/null 2>&1; echo \$? > $O/rc_\$V; date +%s > $O/t1_\$V ) & done
wait
{ echo post rc=\$(cat $O/rc_post); echo mut rc=\$(cat $O/rc_mut); echo emitted_v rc=\$(cat $O/rc_v); } > $O/eq_rc.txt
chown -R 1000:1000 $O
IN
docker run --rm -m ${MEM}g --name khr1-fp-$MOD -v /srv/opentallas-scratch2/claude:/srv/opentallas-scratch2/claude openroad/orfs:asap7lock bash $O/inner.sh
cat $O/eq_rc.txt 2>/dev/null
python3 - "$O/eq_rc.txt" <<'PY'
import pathlib, sys
actual = pathlib.Path(sys.argv[1]).read_text().split()
if actual != ["post", "rc=0", "mut", "rc=1", "emitted_v", "rc=0"]:
    raise SystemExit("HR face proof FAIL or incomplete: " + " ".join(actual))
print("HR face proof PASS")
PY
