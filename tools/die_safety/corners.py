#!/usr/bin/env python3
"""Die STA corner set (ROOT14 10-20, COORD 21:29 owner risk reduction (a)): every die build -- diagnostic ones included --
runs TT setup AND FF hold.  A requested corner list is completed, never trimmed: tt and ff are always added, extra
corners (ss = sensitivity) are kept after them.  An unknown corner is refused.

    corners.required(['tt'])          -> ['tt', 'ff']
    corners.py tt ss                   -> prints "tt ff ss"   (shell: corners=$(python3 tools/die_safety/corners.py $corners))
"""
import sys

REQUIRED = ('tt', 'ff')
KNOWN = ('tt', 'ff', 'ss')


class CornerError(ValueError):
    pass


def required(corners=None):
    req = [c.strip().lower() for c in (corners or []) if c and c.strip()]
    bad = sorted(set(req) - set(KNOWN))
    if bad:
        raise CornerError(f'unsupported die STA corner(s) {bad} (known {list(KNOWN)})')
    out = list(REQUIRED)
    for c in req:
        if c not in out:
            out.append(c)
    return out


def added(corners=None):
    """corners that required() added to a request (for the log line)"""
    req = {c.strip().lower() for c in (corners or []) if c and c.strip()}
    return [c for c in REQUIRED if c not in req]


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    words = [w for a in argv for w in a.split()]
    try:
        out = required(words)
    except CornerError as e:
        print(f'DIE_STA_CORNERS FAIL: {e}', file=sys.stderr)
        return 1
    if added(words):
        print(f'DIE_STA_CORNERS: added {added(words)} (TT setup + FF hold run on every die build)', file=sys.stderr)
    print(' '.join(out))
    return 0


if __name__ == '__main__':
    sys.exit(main())
