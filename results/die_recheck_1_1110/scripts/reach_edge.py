"""DIE-RECHECK-1: kit.log reach failure -> the feed edge whose tap is at the failing leg's end (prints a->b or nothing)."""
import json, re, sys
m = re.findall(r'leg to node \S+ \(\(([-\d.]+), ([-\d.]+)\) -> \(([-\d.]+), ([-\d.]+)\)', open(sys.argv[1]).read())
if not m:
    sys.exit(0)
pts = [(float(m[-1][0]), float(m[-1][1])), (float(m[-1][2]), float(m[-1][3]))]
tap = json.load(open(sys.argv[2]))['tap']
d, k = min((min(abs(v[0] - x) + abs(v[1] - y) for x, y in pts), k) for k, v in tap.items())
print(k if d < 20 else '')
