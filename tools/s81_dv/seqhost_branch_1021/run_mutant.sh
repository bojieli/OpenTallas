#!/usr/bin/env bash
# Explicit MUT1 declaration for the existing composite seqhost suite; same source/profile, no RTL edit.
set -euo pipefail
O=$(realpath -m "$1"); mkdir -p "$O"
export SEQHOST_SOURCE_ROOT="$PWD"
python3 - "$O/mutant_runner.sh" <<'PYCODE'
import sys,re
from pathlib import Path
s=Path('rtl/dsrom_sys/s81_dv/unit/test/run_seq_host_c_bench.sh').read_text()
assert s.count('\nbad=0\n')==1
s=s.split('\nbad=0\n')[0]+'\n'
s=re.sub(r'^R=.*$', 'R=$SEQHOST_SOURCE_ROOT', s, count=1, flags=re.M)
s=s.replace('-j 16','-j "${J:-4}"')
s+="""
build base +define+MUT=1 || exit 2
"$O/base/tb" +seed=1 > "$O/run_mut1.log" 2>&1
cat "$O/run_mut1.log"
if grep -q 'MISMATCH' "$O/run_mut1.log"; then echo SEQHOST_EXPLICIT_MUT1_CAUGHT; exit 1; fi
echo SEQHOST_EXPLICIT_MUT1_NOT_CAUGHT
exit 0
"""
Path(sys.argv[1]).write_text(s)
PYCODE
bash "$O/mutant_runner.sh" "$O"
