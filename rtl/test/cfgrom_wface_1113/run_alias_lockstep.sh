#!/bin/bash
set -euo pipefail
ulimit -c 0
cd "$(dirname "$0")"
export PATH="$HOME/.local/opentallas-tools/verilator-5.050/bin:$HOME/.local/opentallas-tools/bin:$PATH"
python3 - <<'PY'
import random
from pathlib import Path
rng=random.Random(1113)
words=[rng.getrandbits(72) for _ in range(4096)]
rows=[0]*512
for a,w in enumerate(words):
    for b in range(72):
        if (w>>b)&1:rows[a//8]|=1<<(b*8+a%8)
Path('logical_words.hex').write_text(''.join(f'{x:018x}\n' for x in words))
Path('cfg_fixture.viamap.hex').write_text(''.join(f'{x:0144x}\n' for x in rows))
PY
verilator --binary --timing -j 4 -Wno-fatal --top-module tb_cfgrom_alias --Mdir obj tb_cfgrom_alias.sv old.v alias.v > build.log 2>&1
./obj/Vtb_cfgrom_alias +OT_ROM_DIR=. +MUT=0 > nominal.log 2>&1
grep CFGROM_ALIAS nominal.log
for mutation in 1 2; do
  if ./obj/Vtb_cfgrom_alias +OT_ROM_DIR=. +MUT="$mutation" > "mutant_$mutation.log" 2>&1; then
    echo "UNCUGHT_MUTANT $mutation";exit 1
  fi
  grep -q 'alias mismatch' "mutant_$mutation.log"
  grep CFGROM_ALIAS "mutant_$mutation.log"
done
echo CFGROM_ALIAS_ALL_PASS
