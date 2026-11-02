"""Stage an owned coupon only. This script launches no EDA process."""
from pathlib import Path
import hashlib
import json
import shutil

d = Path('/srv/opentallas-scratch2/claude/codex-serdes-loaded-1131')
b = Path('/srv/opentallas-scratch2/claude/codex-serdes-lec/replay1')
r = Path('/srv/opentallas-scratch2/claude/codex-head-pins-1131/src/tools/die_plan')
assert not (d / 'out').exists()
(d / '.keep').touch()
(d / 'out').mkdir()
cache = ['gold.aig', 'gold.map', 'gold.keep', 'gate.aig', 'gate.map', 'gold.aliases.json']
for name in cache:
    shutil.copyfile(b / 'kit/lec' / name, d / 'out' / name)
packet = json.loads((d / 'candidate.json').read_text())
for name, expected in packet['source_sha256'].items():
    assert hashlib.sha256((b / 'kit/rtl' / name).read_bytes()).hexdigest() == expected
identity = {'cache_source': str(b / 'kit/lec'), 'checker': str(r / 'lec.py'),
            'checker_sha256': hashlib.sha256((r / 'lec.py').read_bytes()).hexdigest(),
            'source_hashes': packet['source_sha256'], 'cache_files': cache,
            'full_compare': 'OFF', 'mem_gb': 16, 'threads': 4,
            'status': 'STAGED_NOT_LAUNCHED'}
(d / 'input_identity.json').write_text(json.dumps(identity, indent=1) + '\n')
(d / 'run_guard.sh').write_text('''#!/bin/bash
set -euo pipefail
D=/srv/opentallas-scratch2/claude/codex-serdes-loaded-1131
B=/srv/opentallas-scratch2/claude/codex-serdes-lec/replay1
R=/srv/opentallas-scratch2/claude/codex-head-pins-1131/src/tools/die_plan
docker run --rm --name codex-serdes-loaded-1131 --memory=16g --memory-swap=16g --cpus=4 -e HEAD_FULL_COMPARE=0 -v "$B/kit":/work:ro -v "$B":/baseline:ro -v "$D":/candidate -v "$D/out":/out -v "$R":/m:ro openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 -u /candidate/native_guard_canary.py' > "$D/guard.log" 2>&1
''')
(d / 'run_guard.sh').chmod(0o755)
print(json.dumps(identity))
