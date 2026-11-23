#!/usr/bin/env python3
"""R8 baseline check: compare the named R8 failures of a die bind against a sealed exception set (r8.py check logs).

    python3 tools/die_plan/r8_baseline_check.py BASELINE_R8CHECK.log ACTUAL_R8CHECK.log

Exit 1 when ACTUAL has an R8 ERROR that BASELINE does not carry.  Normalization (KV-D29, COORD ruling 11-23):
  * bus group lines compare up to ": unequal added delay" (the delay figures are reprinted per bind);
  * type conflicts ("instances need different landing pads at N sites (e.g. SITE: pads [..])") compare on type, site
    count N and example SITE; the printed example pad values follow accepted lane depths and are not compared, so a
    change of N or of the example site still fails;
  * the KV afk/kreq order inversions on slg_{EN,ES,WN,WS}_4 are accepted once per face.
"""
import collections
import re
import sys
from pathlib import Path

ALLOWED_INVERSION = re.compile(
    r"ERROR R8 order inversion slg_(EN|ES|WN|WS)_4 \(pc_\1_0\): afk led kreq as built \(\d+ < \d+\) but lands after it \(\d+ > 7\)"
)
TYPE_PADS = re.compile(
    r"^(ERROR R8 type \S+: instances need different landing pads at \d+ sites) \(e\.g\. (.*): pads \[[\d, ]+\]\)(.*)$"
)


def read(path):
    text = Path(path).read_text()
    if not re.search(r"^R8 (?:PASS|FAIL) \{", text, re.MULTILINE):
        raise ValueError(f"missing R8 verdict in {path}")
    return [line for line in text.splitlines() if line.startswith("ERROR ")]


def normalize(line):
    m = TYPE_PADS.match(line)
    if m:
        return f"{m[1]} (e.g. {m[2]}){m[3]}"
    if line.startswith("ERROR R8 bus group "):
        return line.split(": unequal added delay", 1)[0]
    return line


def compare(baseline_lines, actual_lines):
    baseline = collections.Counter(map(normalize, baseline_lines))
    actual = collections.Counter()
    accepted = set()
    for line in actual_lines:
        match = ALLOWED_INVERSION.fullmatch(line)
        if match and match[1] not in accepted:
            accepted.add(match[1])
        else:
            actual[normalize(line)] += 1
    return actual - baseline, baseline - actual, sorted(accepted)


def main(argv):
    new, missing, accepted = compare(read(argv[1]), read(argv[2]))
    print(f"R8_BASELINE {'FAIL' if new else 'PASS'} new={sum(new.values())} resolved={sum(missing.values())} "
          f"accepted_inversions={accepted}", flush=True)
    for line, count in new.items():
        print(f"R8_BASELINE_NEW {count} {line}")
    return int(bool(new))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
