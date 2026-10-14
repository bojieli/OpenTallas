#!/bin/bash
set +e
bash gate.sh early_commit 0 8 tb_qfd_vm_writer_lease_provenance_native 15
rc=$?
set -e
test "$rc" != 0
grep -Eq 'actual native row storage commit crossed active lease|actual posted writer/commit crossed lease|lease payload/provenance mismatch' out/early_commit/run.log
