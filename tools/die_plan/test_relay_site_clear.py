"""relay_site_clear: sites inside a macro move to its free boundary point with the smaller worst hop (TYPE-SAFE-5 11-10)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from relay_site_clear import L1, clear_sites, inside  # noqa: E402

DIE = (0.0, 0.0, 1442.88, 1226.88)
MACRO = (305.0, 35.0, 535.0, 208.0)          # leaf__t35 p3: the bottom-centre macro under the leafup_o0 line


def test_t35_leafup_second_site_leaves_macro():
    # bit 0 of p3: ist_0 site, ist_1 site (inside the macro), u_bout capture
    ist0, ist1, bout = (642.4, 284.3), (446.5, 145.2), (250.0, 6.0)
    assert inside(ist1, MACRO, 6.0)
    path, moved = clear_sites([ist0, ist1], [(749.7, 406.2)], [bout], [MACRO], DIE)
    assert moved == 1
    assert path[0] == ist0                       # a site outside every macro is untouched
    s = path[1]
    assert not inside(s, MACRO, 6.0)
    # p3 placed it on the macro top edge at x ~ 446: 270 / 400 um hops.  The cleared site balances both sides.
    assert max(L1(ist0, s), L1(s, bout)) < 380
    assert abs(L1(ist0, s) - L1(s, bout)) <= 4


def test_site_outside_macros_unchanged():
    path = [(700.0, 600.0), (900.0, 700.0)]
    assert clear_sites(path, [(600.0, 600.0)], [(1000.0, 700.0)], [MACRO], DIE) == (path, 0)


def test_cleared_site_avoids_neighbour_macro():
    other = (299.0, 214.0 - 20.0, 460.0, 260.0)  # a second macro covering most of the first macro's top edge
    path, moved = clear_sites([(642.4, 284.3), (446.5, 145.2)], [(749.7, 406.2)], [(250.0, 6.0)],
                              [MACRO, other], DIE)
    assert moved == 1
    assert not any(inside(path[1], r, 6.0) for r in (MACRO, other))


def test_last_site_uses_capture_fan():
    # one site inside, capture fan of two points: the worst of the two counts
    path, _ = clear_sites([(420.0, 100.0)], [(700.0, 100.0)], [(250.0, 6.0), (250.0, 200.0)], [MACRO], DIE)
    s = path[0]
    assert not inside(s, MACRO, 6.0)
    assert max(L1(s, (700.0, 100.0)), L1(s, (250.0, 6.0)), L1(s, (250.0, 200.0))) < 400
