#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch/claude/codex-s81-rtlgap-2140-1022
python3 - "$R" <<'GEN'
import sys,shutil
from pathlib import Path
p=Path(sys.argv[1]);dst=p/'job15_corrupt13';shutil.copytree(p/'job15',dst,dirs_exist_ok=True)
f=dst/'prog/host_boot.memh';words=f.read_text().splitlines();words[13]=format(int(words[13],16)^(1<<33),'0129x');f.write_text('\n'.join(words)+'\n')
GEN
N=$(wc -l < "$R/job15/prog/host_boot.memh")
"$R/out_producer/obj/sim" +dir="$R/job15_corrupt13" +n="$N" +cyc=1000 +timeout=4000 +mu="$R/job15_corrupt13/mu.txt" > "$R/out_producer/run_corrupt13.log" 2>&1
set +e
python3 "$R/check_producer.py" "$R/job15" "$R/out_producer/run_corrupt13.log" "$R/out_producer/check_corrupt13.json"
rc=$?
set -e
[ "$rc" -eq 1 ] || { echo 'CORRUPT13 NOT CAUGHT'; exit 2; }
echo 'CAP30_PRODUCER corrupt13 CAUGHT'
sha256sum "$R/out_producer/obj/sim" > "$R/out_producer/binary.sha256"
