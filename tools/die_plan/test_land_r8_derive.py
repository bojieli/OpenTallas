"""land_r8_derive.py: the r8 landing table is derived from the bind's bus_groups at compose, never carried."""
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import land_r8_derive as D  # noqa: E402
import r8  # noqa: E402

RAW = {"die": {"name": "t"}, "partitions": [{"name": f"hc{i}", "type": f"th{i}"} for i in range(4)] +
       [{"name": "tap", "type": "ttap"}]}


def mem(port, bits, src, asb, bound, lane="L"):
    return dict(sink_port=port, sink_bits=bits, source=src, source_bits=bits, asbuilt_stages=asb,
                bound_stages=bound, landed_stages=bound, lane=lane)


def bus_groups(qreg=0):
    """four heads fed by one source; `qreg` adds one bound stage on head 2's lane (a plan qreg / a substituted stage)"""
    land = []
    for h, d in enumerate([6, 4, 2, 4]):
        d += qreg if h == 2 else 0
        land.append(dict(sink=f"u_h{h}", sink_part=f"hc{h}", src_part="tap",
                         members=[mem("a", [[0, 31]], "u_tap.a", 0, d, lane=f"L{h}"),
                                  mem("v", [[0, 0]], "u_tap.v", 0, d, lane=f"L{h}")]))
    rep = [dict(source="u_tap.a", source_bits=[[0, 31]], asbuilt_stages=0, sink_parts=["hc0", "hc1", "hc2", "hc3"])]
    return dict(die="t", landing=land, replica=rep)


def _table(tmp_path, bg, replica="all"):
    r8.configure()
    p, _ = r8.write_pads(RAW, bg, tmp_path / f"r8_{replica}", replica)
    return json.loads(p.read_text()), p.read_text()


def test_derive_is_byte_identical_to_r8_pads(tmp_path):
    ref, text = _table(tmp_path, bus_groups())
    got, _ = D.derive(RAW, bus_groups(), D.options(ref))
    assert got == text
    assert D.diff(ref, json.loads(got))["equal"]


def test_carried_table_is_stale_after_a_stage_and_derive_fixes_it(tmp_path):
    old, _ = _table(tmp_path, bus_groups())
    new_bg = bus_groups(qreg=1)          # head 2: 2 -> 3, the class max (6) is unchanged: pad 4 -> 3
    d = D.diff(old, json.loads(D.derive(RAW, new_bg, D.options(old))[0]))
    assert not d["equal"] and d["changed"] == 2 and d["added"] == d["removed"] == 0   # id keeps; bound/pad move
    text, _ = D.derive(RAW, new_bg, D.options(old))
    new = json.loads(text)
    h2 = [m for m in new["members"] if m["sink"] == "u_h2"]
    assert {m["bound"] for m in h2} == {3} and {m["pad"] for m in h2} == {3} and {m["landed"] for m in h2} == {6}
    assert D.diff(new, json.loads(D.derive(RAW, new_bg, D.options(new))[0]))["equal"]


def test_options_are_taken_from_the_current_table(tmp_path):
    ref, text = _table(tmp_path, bus_groups(), replica="type")
    assert D.options(ref)["replica"] == "type"
    assert D.derive(RAW, bus_groups(), D.options(ref))[0] == text


def test_cli_derive_writes_atomically_and_check_gates(tmp_path, monkeypatch):
    import schema as S
    monkeypatch.setattr(S, "load", lambda p: RAW)
    _, text = _table(tmp_path, bus_groups())
    tab = tmp_path / "r8_sw2.json"
    tab.write_text(text)
    twin = tmp_path / "twin.json"
    os.link(tab, twin)                                  # a hard-linked tree copy of the carried table
    bg = tmp_path / "bus_groups.json"
    bg.write_text(json.dumps(bus_groups(qreg=1)))
    assert D.main(["check", "plan.json", str(bg), "--table", str(tab)]) == 1        # carried table: STALE
    rep = tmp_path / "rep.json"
    assert D.main(["derive", "plan.json", str(bg), "--like", str(tab), "--out", str(tab), "--json", str(rep)]) == 0
    assert twin.read_text() == text                      # the hard-linked copy is untouched
    assert tab.read_text() != text
    assert D.main(["check", "plan.json", str(bg), "--table", str(tab)]) == 0
    r = json.loads(rep.read_text())
    assert r["diff"]["changed"] == 2 and r["diff"]["lanes"] == {"L2": 2} and r["out_sha256"]
