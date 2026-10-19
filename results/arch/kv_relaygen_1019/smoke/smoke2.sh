set -e
cd "$(dirname "$0")"; mkdir -p gold
docker run --rm -v "$PWD":/w -w /w openroad/orfs:latest bash -c 'yosys -q -c gold.tcl > gold.log 2>&1 && yosys -s eq.ys > eq.log 2>&1; rc=$?; grep -E "SUCCESS|FAIL|Induction step proven|ERROR|failed" eq.log | head; echo EQ_RC=$rc; exit $rc'
