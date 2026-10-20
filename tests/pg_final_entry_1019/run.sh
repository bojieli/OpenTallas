#!/bin/bash
# Run from a directory holding physical/common_flow, tests/pg_final_entry_1019 and inputs/checkpoint.odb
# (the strict CTS checkpoint of tests/pg_final_order_1019, 510 PG terms, 192 unbound).
set -euo pipefail
ROOT=$PWD
IMG=openroad/orfs:asap7lock
OR=/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad
mkdir -p output
sha256sum inputs/checkpoint.odb physical/common_flow/native_pg* tests/pg_final_entry_1019/*.tcl >output/source.sha256
docker image inspect "$IMG" --format '{{.Id}} {{json .RepoDigests}}' >output/image.txt
run() {
 local case=$1 odb=$2
 mkdir -p output/$case
 docker run --rm -v "$ROOT:/src" -w /src -e TEST_CASE="$case" -e TEST_ODB="/src/$odb" -e TEST_OUT="/src/output/$case" \
   -e TEST_BOOTSTRAP=/src/physical/common_flow/native_pg_final_entry.tcl "$IMG" "$OR" -no_init -exit \
   /src/tests/pg_final_entry_1019/compose.tcl >output/$case/run.log 2>&1 || true
 grep -q "^TEST_PASS $case$" output/$case/run.log && echo "CASE_PASS $case" || { echo "CASE_FAIL $case"; tail -5 output/$case/run.log; FAIL=1; }
}
FAIL=0
run birth inputs/checkpoint.odb
run protected inputs/checkpoint.odb
run dirty inputs/checkpoint.odb
run default inputs/checkpoint.odb
docker run --rm -v "$ROOT:/src" -e TEST_ODB=/src/inputs/checkpoint.odb -e TEST_FIXTURE=/src/output/allbound_fixture.odb "$IMG" "$OR" -no_init -exit /src/tests/pg_final_entry_1019/fixture.tcl >output/fixture.log 2>&1
run allbound output/allbound_fixture.odb
run wrongrole output/allbound_fixture.odb
sha256sum -c output/source.sha256 >output/source_after.txt
[ $FAIL = 0 ] && echo PG_FINAL_ENTRY_SUITE_PASS || { echo PG_FINAL_ENTRY_SUITE_FAIL; exit 1; }
