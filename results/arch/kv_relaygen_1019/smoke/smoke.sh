cd "$(dirname "$0")"; mkdir -p gold split
docker run --rm -v "$PWD":/w -w /w openroad/orfs:latest bash -c '
SPLIT=0 OUTD=gold TOPN=gold yosys -q -c run.tcl > gold.log 2>&1 || { echo GOLD_FAIL; tail -5 gold.log; }
SPLIT=1 OUTD=split TOPN=gate yosys -q -c run.tcl > split.log 2>&1 || { echo SPLIT_FAIL; tail -20 split.log; }
grep -hE "OT_RST|OT_KEEP" split.log; python3 count.py split/post.json
yosys -s eq.ys > eq.log 2>&1; echo EQ_RC=$?; grep -E "SUCCESS|FAIL" eq.log | tail -2'
