"""Real occupancy counterexample: a short-reach hub landing needs the shared street first."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import dsrom_s81_fulldie as G


def place(p, name, size, reach):
    at = p.near(150, 120, *size, [(80, 100, 240, 140)], prev=(150, 120), reach=reach, span=100, rows=20)
    if at is not None:
        p.add(G.Inst(name, name, *at, *size))
    return at


def test_shared_street_old_order_blocks_pin_new_order_places_both():
    old = G.Placer({'insts': []})
    assert place(old, 'link', (20, 20), 100) is not None
    assert place(old, 'hub', (60, 20), 20) is None
    new = G.Placer({'insts': []})
    assert place(new, 'hub', (60, 20), 20) is not None
    assert place(new, 'link', (20, 20), 100) is not None
    a, b = new.m['insts']
    assert not (a.x < b.x+b.w and b.x < a.x+a.w and a.y < b.y+b.h and b.y < a.y+a.h)
    assert G._mh((a.x+a.w/2,a.y+a.h/2),(150,120)) <= 20


def test_unsatisfiable_street_refuses_without_forcing_overlap():
    blocker = G.Inst('full_street', 'obstacle', 80, 100, 160, 40)
    p = G.Placer({'insts': [blocker]})
    assert place(p, 'hub', (60, 20), 20) is None
    assert place(p, 'link', (20, 20), 100) is None
    assert len(p.m['insts']) == 1
