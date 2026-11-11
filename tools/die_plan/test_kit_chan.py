"""KIT-CHAN-1 (DIE-QC-97 11-11): plan internal_stations[].leg_order "channel" (istation_channel.py), one test per piece:
the shared geometry, the kit TCL site proc (vs the Python mirror), the kit chain emission + fail-closed checks, the plan
macro gate, taps station sinks and the schema.  Byte-identity of the existing orders: test_kit_chan_identity.py."""
import json
import random
import re
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import istation_channel as IC          # noqa: E402
import kit_istations as KI             # noqa: E402
import test_kit_istations_core_pin as F  # noqa: E402
from test_kit_chan_identity import GOLDEN, _run_plan  # noqa: E402


def _close(a, b, tol=1e-6):
    return all(abs(x - y) < tol for p, q in zip(a, b) for x, y in zip(p, q)) and len(a) == len(b)


# ---------------------------------------------------------------------------------------------------- geometry
def test_geometry_columns_paths_and_equal_hops():
    assert IC.column(8.0, 120.0, 0, 4) == pytest.approx(22.0) and IC.column(8.0, 120.0, 3, 4) == pytest.approx(106.0)
    # W face in bus: pin (0, 100) -> (col, 100) -> (col, 700) -> leaf (190, 700)
    col = IC.column(8.0, 120.0, 1, 4)
    p = IC.path(0.0, 100.0, 190.0, 700.0, "W", "in", col)
    assert p == [(0.0, 100.0), (col, 100.0), (col, 700.0), (190.0, 700.0)]
    assert IC.path(0.0, 100.0, 190.0, 700.0, "W", "out", col) == p[::-1]
    # N face: the transpose (row through the channel)
    assert IC.path(50.0, 1339.2, 300.0, 600.0, "N", "in", 1200.0) == [(50.0, 1339.2), (50.0, 1200.0), (300.0, 1200.0),
                                                                       (300.0, 600.0)]
    for d in ("in", "out"):
        s = IC.sites(0.0, 100.0, 190.0, 700.0, "W", d, 8.0, 120.0, 1, 4, 3)
        start = p[0] if d == "in" else p[-1]
        end = p[-1] if d == "in" else p[0]
        hops = [abs(a[0] - c[0]) + abs(a[1] - c[1]) for a, c in zip([start] + s + [end], s + [end])]
        L = IC.length(p)
        assert len(s) == 3 and all(h == pytest.approx(L / 4) for h in hops)
    assert IC.worst_hop(0.0, 100.0, 190.0, 700.0, "W", "in", 8.0, 120.0, 1, 4, 3) == pytest.approx(IC.length(p) / 4)


def test_entry_channel_fails_closed():
    assert IC.entry_channel(dict(leg_order="channel", channel_um=[8, 120])) == (8.0, 120.0)
    for bad in (None, [8], [120, 8], ["a", 1]):
        with pytest.raises(SystemExit, match="channel_um"):
            IC.entry_channel(dict(conn="bus:x", core="A", leg_order="channel", channel_um=bad))


# ---------------------------------------------------------------------------------------------------- kit TCL
def _tcl(body):
    p = subprocess.run(["tclsh"], input=KI.TCL_CHAN_SITE + "\n" + body, text=True, capture_output=True)
    assert p.returncode == 0, p.stderr
    return p.stdout


def test_tcl_site_matches_python_mirror():
    rnd = random.Random(1111)
    lines, want = [], []
    for _ in range(120):
        face, d = rnd.choice("NSEW"), rnd.choice(("in", "out"))
        W = rnd.randint(1, 600)
        b = rnd.randint(0, W)
        if face in "EW":
            px, py = (0.0 if face == "W" else 622.08), rnd.uniform(0, 1339)
            lo = rnd.uniform(5, 300)
        else:
            px, py = rnd.uniform(0, 622), (0.0 if face == "S" else 1339.2)
            lo = rnd.uniform(5, 600)
        hi = lo + rnd.uniform(0, 200)
        lx, ly = rnd.uniform(0, 622), rnd.uniform(0, 1339)
        n = rnd.randint(1, 6)
        if IC.worst_hop(px, py, lx, ly, face, d, lo, hi, b, W + 1, n) > 403.0:
            continue
        s = IC.sites(px, py, lx, ly, face, d, lo, hi, b, W + 1, n)
        for k in range(n):
            lines.append(f'puts [is_chan_site {px} {py} {lx} {ly} {face} {k + 1} {n + 1} {d} {lo} {hi} {b} {W}]')
            want.append(s[k])
    got = [tuple(map(float, ln.split())) for ln in _tcl("\n".join(lines)).splitlines()]
    assert len(got) == len(want) > 100 and _close(got, want, 1e-6)


def test_tcl_site_fails_closed_over_403():
    out = _tcl('if {[catch {is_chan_site 0 0 600 1300 W 1 2 in 8 120 0 3} m]} { puts "E $m" } else { puts OK }')
    assert out.startswith("E internal station channel needs a plan depth change")


def test_tcl_chan_bits_is_is_bits_with_the_channel_site():
    a = KI.TCL_HEAD.index("proc is_bits ")
    isb = KI.TCL_HEAD[a:KI.TCL_HEAD.index("\n}\n", a) + 3].splitlines()
    c = KI.TCL_CHAN.index("proc is_chan_bits ")
    icb = KI.TCL_CHAN[c:].splitlines()
    diff = [(x, y) for x, y in zip(isb, icb) if x != y]
    assert len(isb) == len(icb) and len(diff) == 2
    assert "is_chan_bits" in diff[0][1] and "lo hi" in diff[0][1]
    assert "is_chan_site" in diff[1][1] and "$lo $hi $b $W" in diff[1][1]
    assert "is_chan_site" not in KI.TCL_HEAD and "is_chan_bits" not in KI.TCL_HEAD


# ---------------------------------------------------------------------------------------------------- kit emission
def _chan_plan(which=(0,), um=(5.0, 30.0)):
    p = F.plan()
    for i, e in enumerate(p["partition_types"]["t"]["internal_stations"]):
        if i in which:
            e["leg_order"] = "channel"
            if um is not None:
                e["channel_um"] = list(um)
    return p


def test_kit_emits_chan_bits_only_for_channel_chains(tmp_path):
    kd = tmp_path / "k"
    kd.mkdir()
    got = _run_plan(kd, _chan_plan(), F.BOUND)
    tcl = (kd / "kit" / "istations.tcl").read_text()
    assert tcl.count("proc is_chan_bits ") == 1 and tcl.count("proc is_chan_site ") == 1
    assert tcl.index("proc is_chan_bits ") < min(tcl.index("\nis_bits "), tcl.index("\nis_chan_bits "))
    rows = re.findall(r"^is_chan_bits (\S+) .*$", tcl, re.M)
    assert rows == ["u_ist_x__A_0_0", "u_ist_x__A_0_1"]
    assert all(ln.endswith(" ist:x:A 5.0000 30.0000 0") for ln in re.findall(r"^is_chan_bits .*$", tcl, re.M))
    assert len(re.findall(r"^is_bits u_ist_", tcl, re.M)) == 10
    # the leg order is placement only: RTL and report are byte-equal to the normal-first kit
    assert got["rtl"] == GOLDEN["kit"]["normal"]["rtl"] and got["rep"] == GOLDEN["kit"]["normal"]["rep"]


def test_kit_channel_start_core_keeps_starts(tmp_path):
    p, pins = F.lplan()
    e = p["partition_types"]["t"]["internal_stations"][0]
    e.update(leg_order="channel", channel_um=[64.0, 78.0])
    _run_plan(tmp_path, p, F.LBOUND, pins)
    rows = re.findall(r"^is_chan_bits .*$", (tmp_path / "kit" / "istations.tcl").read_text(), re.M)
    assert len(rows) == 2 and all(r.endswith(" 64.0000 78.0000 0 {0 80.0000 12.0000 1 80.0000 13.0000 2 80.0000 "
                                             "14.0000 3 80.0000 15.0000}") for r in rows)


@pytest.mark.parametrize("mut,msg", [("no_um", "channel_um"), ("non_core", "leg_order channel on non-core")])
def test_kit_channel_must_fail(tmp_path, mut, msg):
    p = _chan_plan(um=None) if mut == "no_um" else F.plan()
    if mut == "non_core":
        p["partition_types"]["t"]["internal_stations"].append(
            dict(conn="bus:x", bit_route="per_bit", leaf_um=[5.0, 5.0], regs_um=[[1.0, 1.0]], leg_order="channel",
                 channel_um=[1.0, 2.0], from_um=[0.0, 0.0], to_um=[5.0, 5.0]))
    pf = tmp_path / "plan.json"
    pf.write_text(json.dumps(p))
    kd = tmp_path / "kit"
    kd.mkdir()
    bf = kd / "t_part_bound.sv"
    bf.write_text(F.BOUND)
    (kd / "kit_rtl.json").write_text(json.dumps(dict(bound_module="t_part_bound", files=[str(bf)])))
    r = subprocess.run([sys.executable, str(HERE / "kit_istations.py"), str(pf), "t", str(kd), "--apply"],
                       capture_output=True, text=True)
    assert r.returncode != 0 and msg in (r.stderr + r.stdout), r.stderr[-300:]
    assert bf.read_text() == F.BOUND


# ---------------------------------------------------------------------------------------------------- plan gate
def test_chain_macro_hits_channel():
    # W face pins at x = 0, y 10..13 -> leaf (100, 200); macro M covers x -1..5, y 40..140 (the along_first column)
    t = dict(hard_cores=[dict(inst="M", module="m", origin_um=[-1.0, 40.0], outline_um=[6.0, 100.0])])
    b = dict(name="z", face="W")
    starts = {k: (0.0, 10.0 + k) for k in range(4)}
    assert {h[1] for h in KI.chain_macro_hits(t, dict(leaf_um=[100.0, 200.0], leg_order="along_first"), b, starts)} == {"M"}
    e = dict(leaf_um=[100.0, 200.0], leg_order="channel", channel_um=[20.0, 60.0])
    assert KI.chain_macro_hits(t, e, b, starts) == []
    # a channel over the macro is caught on its vertical leg
    e2 = dict(e, channel_um=[1.0, 3.0])
    assert sorted(KI.chain_macro_hits(t, e2, b, starts)) == [(k, "M") for k in range(4)]
    # nbits sets the columns: with nbits = 4 bit 0 sits at 25 um, with nbits = 40 at 20.5 um
    t3 = dict(hard_cores=[dict(inst="N", module="n", origin_um=[24.0, 40.0], outline_um=[2.0, 100.0])])
    assert KI.chain_macro_hits(t3, e, b, {0: (0.0, 10.0)}, nbits=4) == [(0, "N")]
    assert KI.chain_macro_hits(t3, e, b, {0: (0.0, 10.0)}, nbits=40) == []


# ---------------------------------------------------------------------------------------------------- taps
def test_taps_channel_sites_match_kit_geometry():
    import taps
    t = F.plan()["partition_types"]["t"]
    e = t["internal_stations"][0]                  # x -> A, core_bits [0, 1], 2 stations, leaf (50, 50), W face
    e.update(leg_order="channel", channel_um=[5.0, 30.0])
    t = dict(t, internal_stations=[e])
    pins = [("x", b, "M4", 0.0, 10.0 + b, "W") for b in range(5)]
    got = [(x, y) for x, y, _ in taps.per_bit_station_sites(t, pins)]
    want = []
    for bit in (0, 1, 4):                           # core bits + epoch
        want += IC.sites(0.0, 10.0 + bit, 50.0, 50.0, "W", "in", 5.0, 30.0, bit, 5, 2)
    assert _close(got, want)
    assert all(5.0 <= x <= 30.0 or abs(y - 50.0) < 1e-9 or y < 15.0 for x, y in got)


# ---------------------------------------------------------------------------------------------------- schema
def test_schema_channel_fields():
    import schema
    it = schema.SCHEMA["properties"]["partition_types"]["additionalProperties"]["properties"]["internal_stations"]["items"]
    assert it["properties"]["leg_order"]["enum"] == list(IC.ORDERS)
    assert it["properties"]["channel_um"]["minItems"] == 2 == it["properties"]["channel_um"]["maxItems"]
    js = json.loads((HERE / "die_plan.schema.json").read_text())
    it2 = js["properties"]["partition_types"]["additionalProperties"]["properties"]["internal_stations"]["items"]
    assert it2["properties"]["leg_order"] == it["properties"]["leg_order"]
    assert it2["properties"]["channel_um"] == it["properties"]["channel_um"]
