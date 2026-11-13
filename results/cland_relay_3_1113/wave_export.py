"""CLAND-RELAY-2 private proof: head_wave_kit_rtl export from the proof tree with the published-cohort token
compare RECORDED (diff written to OUT/token_diff.txt) instead of enforced, because the reader-START relay changes the
wrapper on purpose.  Everything else (alias_patch, private raw patch, kit_rtl.f/json) is the wave's own code."""
import difflib, sys
from pathlib import Path
src = Path(sys.argv[1]); sys.path.insert(0, str(src / 'tools/s81_head'))
import head_wave_kit_rtl as h
orig = h.tokens
log = []
def tokens(text):
    log.append(orig(text))
    return 0
h.tokens = tokens
import argparse
a = argparse.Namespace(plan=Path(sys.argv[2]), out=Path(sys.argv[3]), type=sys.argv[4])
h.export(a)
if len(log) == 2:
    d = list(difflib.unified_diff([str(x) for x in log[1]], [str(x) for x in log[0]], 'published', 'proof', lineterm='', n=2))
    (a.out / 'token_diff.txt').write_text('\n'.join(d) + '\n')
    print('TOKEN_DIFF lines', len(d))
