#!/usr/bin/env python3
"""Bounded calibration intake: replay using only selected current sources."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
proof = json.loads((HERE / 'source-selected-proof-r1.json').read_text())
for group in ['current_replay_sources', 'reviewed_artifacts']:
    for row in proof[group]:
        data = (ROOT / row['path']).read_bytes()
        assert hashlib.sha256(data).hexdigest() == row['sha256'], row['path']
# Historical predecessor blobs are provenance only, never copied or executed.
with tempfile.TemporaryDirectory(prefix='qwen-source-selected-replay-') as temp:
    sandbox = Path(temp)
    for row in proof['current_replay_sources'] + proof['reviewed_artifacts']:
        target = sandbox / row['path']
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / row['path'], target)
    subprocess.run([sys.executable, '-B', '-m', 'pytest', '-q',
                    '-p', 'no:cacheprovider', 'tests/test_qwen_rom_me_latency_semantics.py'],
                   cwd=sandbox, check=True)
print('SOURCE_SELECTED_41_AND_ARTIFACT_4_HASHES_PASS; MINIMAL_TREE_COLD_REPLAY_PASS')
