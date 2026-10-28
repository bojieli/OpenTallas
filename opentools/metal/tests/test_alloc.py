"""opentools.metal allocator tests.  QC case = INFRA-FIRST-QC-R34 (claude/qc-infra-r34-1027@3752a99e90): M8 PG
stripe every 4.32 um (VSS/VDD alternating, 0.48 wide), 16w clock NDR (w 0.64, s 0.5, PG-flank shields), +-2.5 um pin
windows on island slot rows every 8.64 um.  R34 measured 266 no_clock_track (209 on M8)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from metal import alloc as A  # noqa: E402

N16 = dict(width_um=0.64, space_um=0.5, shield="pg_flank")
QC_PG = dict(pitch_um=8.64, stripes=[dict(net="VSS", offset_um=0.0, width_um=0.48), dict(net="VDD", offset_um=4.32, width_um=0.48)])
ROWS = dict(pitch_um=8.64, half_um=2.5)
FIX = json.loads((ROOT / "tests" / "data" / "qc_r34_m8_blockers.json").read_text())


def qc_layer(row_y, pg_y):
    pg = dict(QC_PG, stripes=[dict(s, offset_um=(pg_y + s["offset_um"]) % 8.64) for s in QC_PG["stripes"]])
    return dict(pg=pg, pin_windows=[dict(layer="M8", rows=dict(ROWS, offset_um=row_y % 8.64))])


def test_reproduces_qc_r34_m8_conflicts():
    """every one of the 209 R34 M8 no_clock_track rows: an off-window 16w wire (escape / foreign trunk) has NO legal
    position within one PG pitch (8.64 um) of its ideal track, with nothing else placed -> the conflict is structural."""
    n = 0
    for r in FIX["rows"]:
        L = qc_layer(r["ideal_y"], r["pg_y"][0])
        w = dict(name=r["name"], ndr=N16, y_pref=r["ideal_y"], x0=0.0, x1=10.0, row=None, max_jog_um=8.64)
        res = A.allocate(L, [w])
        assert res["stats"]["conflicts"] == 1, (r["name"], res)
        assert any(b.startswith("window") for b in res["conflicts"][0]["blockers"])
        n += 1
    assert n == 209


def test_phase_scan_qc_now_zero_and_gap_centred_rows_free_one():
    scan = dict((p, off) for p, off, _ in A.phase_scan(QC_PG, N16, ROWS))
    # R34 rows sit 0.13 / -0.41 um from a PG stripe (fixture): 0 off-window slots per 8.64-um row period
    for phi in (0.12, 8.24, 4.44, 3.92):
        assert scan[phi] == 0, phi
    # rows centred in a PG gap (phi = 2.16 or 6.48): 1 off-window slot per row period
    assert scan[2.16] == 1 and scan[6.48] == 1
    free = sorted(p for p, off in scan.items() if off > 0)
    assert free and min(free) >= 1.16 - 1e-6        # band [1.16, 3.16] u [5.48, 7.48]


def test_own_trunks_fill_gaps_then_escape_conflicts_then_fixes():
    """one top repeater on row y=1321.4 (R34 example ckt_17675): in- and out-net 16w trunks overlap at the cell, plus an
    off-window escape. Today: both gaps of the row are taken by the own trunks and every other gap is in a window
    -> conflict. Fix A (rows at PG gap centre, phase 2.16) + B (flow-oriented repeater: in/out share one track)
    -> all placed."""
    y = 1321.4
    W = [dict(name="in", ndr=N16, y_pref=1320.84, x0=2700.0, x1=2780.3, row=round((y - y % 8.64) / 8.64)),
         dict(name="out", ndr=N16, y_pref=y, x0=2778.5, x1=2990.0, row=round((y - y % 8.64) / 8.64)),
         dict(name="esc", ndr=N16, y_pref=1323.0, x0=2727.0, x1=2993.0, row=None)]
    L = qc_layer(y, 1321.92)
    r0 = A.allocate(L, W)
    assert [c["name"] for c in r0["conflicts"]] == ["esc"]
    # fix A only: rows on gap centres -> the escape gets the off-window gap
    pg_y = y - 2.16
    LA = qc_layer(y, pg_y)
    WA = [dict(w, row=round((y - (y % 8.64)) / 8.64)) if w["row"] is not None else w for w in W]
    rA = A.allocate(LA, WA)
    # the row's own two trunks still need two gaps; the row owns only its centre gap, the off-window gap is shared
    rAB = A.allocate(LA, [dict(WA[0], name="in+out", x1=2990.0), WA[2]])
    assert rAB["stats"]["conflicts"] == 0, rAB
    assert rA["stats"]["placed"] >= 2


def test_drawn_shields_pack_several_per_gap():
    L = dict(pg=dict(pitch_um=10.0, stripes=[dict(offset_um=0.0, width_um=0.5)]), pin_windows=[])
    n8 = dict(width_um=0.32, space_um=0.08, shield="drawn", shield_width_um=0.32)
    W = [dict(name=f"w{i}", ndr=n8, y_pref=5.0, x0=0, x1=100, row=None, max_jog_um=5.0) for i in range(9)]
    r = A.allocate(L, W)
    # gap 9.5 um, footprint 1.12 + 0.08 space -> 7 fit
    assert r["stats"]["placed"] == 7 and r["stats"]["conflicts"] == 2
