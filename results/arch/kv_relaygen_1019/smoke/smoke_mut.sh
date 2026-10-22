cd "$(dirname "$0")"
docker run --rm -v "$PWD":/w -w /w openroad/orfs:latest bash -c 'python3 mut.py; yosys -s eq_mut.ys > eq_mut.log 2>&1; echo EQ_MUT_RC=$?; grep -E "SUCCESS|FAIL" eq_mut.log | tail -2'
