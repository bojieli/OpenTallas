#!/usr/bin/env python3
"""landing_phase_sign classification: LEAD / LAG / NEAR at the margin, corner disagreement -> NEAR."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import landing_phase_sign as L


def c(d, up=0.0, dn=0.0, m=100.0):
    return L.classify_corner(dict(t_local_ps=d, t_fwd_ps=0.0, p_up_ps=up, p_dn_ps=dn), m)['cls']


def test_classes():
    assert c(-150) == 'LEAD'
    assert c(-150, up=60) == 'NEAR'         # derated hi -90 > -100
    assert c(150) == 'LAG'
    assert c(150, dn=60) == 'NEAR'
    assert c(0) == 'NEAR'
    assert c(-100) == 'LEAD' and c(100) == 'LAG'


if __name__ == '__main__':
    test_classes()
    print('ok')
