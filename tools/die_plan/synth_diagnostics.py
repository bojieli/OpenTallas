#!/usr/bin/env python3
"""Install full Yosys stage diagnostics in a disposable ORFS container only."""
from pathlib import Path
import argparse

MARKER = '# OT_SYNTH_DIAGNOSTICS v1'
ANCHOR = '$YOSYS_EXE $YOSYS_FLAGS -c $1'
TRAP = r'''# OT_SYNTH_DIAGNOSTICS v1
# Native -l records detailed frontend messages hidden by console -v.
trap 'ot_synth_status=$?; if [ "$ot_synth_status" -ne 0 ] && [ -f "$2.full.log" ]; then echo "OT_SYNTH_DIAGNOSTICS exit=$ot_synth_status full_log=$2.full.log" >&2; tail -n 160 "$2.full.log" >&2; fi; exit "$ot_synth_status"' EXIT
'''


def patch(text):
    replacement='$YOSYS_EXE $YOSYS_FLAGS -l "$(realpath "$2").full.log" -c $1'
    if MARKER in text:
        if text.count(MARKER)!=1 or text.count(replacement)!=1 or text.count(TRAP)!=1:
            raise ValueError('incomplete existing synth diagnostic patch')
        return text
    if text.count(ANCHOR)!=1 or text.count('touch $2\n')!=1:
        raise ValueError('unsupported ORFS synth.sh anchors; not installed')
    return text.replace('touch $2\n','touch $2\n'+TRAP).replace(ANCHOR,replacement)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('flow',type=Path)
    args=parser.parse_args()
    script=args.flow/'scripts/synth.sh'
    old=script.read_text();new=patch(old)
    if old!=new:script.write_text(new)
    print('OT_SYNTH_DIAGNOSTICS installed',script)


if __name__=='__main__':main()
