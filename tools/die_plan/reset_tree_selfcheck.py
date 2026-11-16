#!/usr/bin/env python3
"""reset_tree_selfcheck.py BIND_RTL_DIR...: offline bind self-check. For every <type>.reset_tree.json emission receipt in a bind rtl dir,
the receipt tree must equal the edges of the emitted RTL (reset_consumers.verify_published). Exit 1 on any mismatch."""
import sys, json, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import reset_consumers as RC
bad = n = 0
for d in map(pathlib.Path, sys.argv[1:]):
    for j in sorted(d.glob('*.reset_tree.json')):
        sv = j.with_name(j.name[:-len('.reset_tree.json')] + '.sv')
        if not sv.is_file():
            continue
        rec = json.loads(j.read_text())
        iss = RC.verify_published(sv.read_text(), rec['tree'])
        n += 1
        if iss:
            bad += 1
            print(f"MISMATCH {d.parent.name}/{sv.name}: {len(iss)}: " + "; ".join(iss[:2]))
print(f"reset_tree_selfcheck: {n} emitted types checked, {bad} mismatching")
sys.exit(1 if bad else 0)
