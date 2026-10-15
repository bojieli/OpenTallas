#!/usr/bin/env python3
"""Exercise terminal reach, occupancy and real pair predicates before relay BFS."""
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from qwen_rom_fulldie_b3r2 import _relay_terminal_possible

# A source-side site cannot help when every terminal is beyond the reach limit.
assert not _relay_terminal_possible(np.array([[0., 0.], [100., 0.]]), (1000., 0.), 500., lambda _: True)
# Reach alone is insufficient when the destination-side site is occupied.
assert not _relay_terminal_possible(np.array([[490., 0.]]), (1000., 0.), 510., lambda _: False)
# The exact real-view predicate must also admit the final hop.
assert not _relay_terminal_possible(np.array([[490., 0.]]), (1000., 0.), 510., lambda _: True,
                                    lambda a, b: abs(a[0] - b[0]) <= 500.)
assert _relay_terminal_possible(np.array([[490., 0.], [510., 0.]]), (1000., 0.), 510., lambda _: True,
                                lambda a, b: abs(a[0] - b[0]) <= 500.)
# Center versus origin matters: a site at origin 0 with center 20 reaches x=510.
assert _relay_terminal_possible(np.array([[20., 0.]]), (510., 0.), 500., lambda _: True)
print('PASS: relay terminal guard preserves reach, occupancy and exact pair conditions')
