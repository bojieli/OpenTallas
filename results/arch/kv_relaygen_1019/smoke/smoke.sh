set -e
cd "$(dirname "$0")"
docker run --rm -v "$PWD":/w -w /w openroad/orfs:latest bash -c 'yosys -q -c run.tcl > yosys.log 2>&1; rc=$?; grep -E "OT_RST_SPLIT|OT_KEEP|ERROR" yosys.log; python3 count.py; exit $rc'
