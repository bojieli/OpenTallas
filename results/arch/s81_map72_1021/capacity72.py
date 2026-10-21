"""Actual selected 72-frame capacity inventory; keep all sixteen logical slices.

Start with the f84 filter (twelve physical frame columns), remove the north
h10 (row 11) in every retained column. Thus each column has five h9 + one h10.
The physical packing is 5678a1aa8; this inventory adapter does not assert STA.
"""
import sys
import capacity_cols as CC

keep84 = CC.keep_frame
CC.keep_frame = lambda name: keep84(name) and not name.endswith('11')

if __name__ == '__main__':
    sys.exit(CC.XC.main())
