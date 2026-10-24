"""R8 bus-coherent latency (r8.py): the xt1 head case, valid/data order, replica sets, reset exemption, type pads."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import r8  # noqa: E402

RAW = {"die": {"name": "t"}, "partitions": [
    {"name": "tap", "type": "ttap"}, {"name": "hc0", "type": "th0"}, {"name": "hc1", "type": "th1"},
    {"name": "hc2", "type": "th2"}, {"name": "hc3", "type": "th3"},
    {"name": "s_A_x", "type": "ts"}, {"name": "s_B_x", "type": "ts"}]}


def mem(port, bits, src, asb, bound, lane="L", landed=None):
    return dict(sink_port=port, sink_bits=bits, source=src, source_bits=bits, asbuilt_stages=asb,
                bound_stages=bound, landed_stages=bound if landed is None else landed, lane=lane)


def heads():
    """xt1: tap.hw reaches heads at +6/+4/+2/+4 (forwarded chain), cid direct at 5/4/2/3"""
    land, rep = [], []
    for h, (hw, cid) in enumerate([(6, 5), (4, 4), (2, 2), (4, 3)]):
        land.append(dict(sink=f"u_xh{h}", sink_part=f"hc{h}", src_part="tap",
                         members=[mem("a_d", [[0, 99]], "u_tap.hw", 0, hw), mem("cid", [[0, 5]], "u_tap.cid", 0, cid)]))
    for s in ("u_tap.hw", "u_tap.cid"):
        rep.append(dict(source=s, source_bits=[[0, 5]], asbuilt_stages=0, sink_parts=["hc0", "hc1", "hc2", "hc3"]))
    return dict(die="t", landing=land, replica=rep)


def test_xt1_heads_fail_then_pass(tmp_path):
    bg = heads()
    msgs, st = r8.check(bg, RAW)
    assert st["groups_unequal"] == 2 and st["replica_unequal"] == 2      # hc0 6 vs 5, hc3 4 vs 3
    p, sm = r8.write_pads(RAW, bg, tmp_path)
    js = json.loads(p.read_text())
    assert {m["landed"] for m in js["members"]} == {6}                    # every head, every bit at 6
    assert sm["max_offset_before"] == sm["max_offset_after"] == 6
    lm, _ = r8.load_landing(p)
    msgs, st = r8.check(bg, RAW, lm)
    assert not msgs and st["replica_unequal"] == 0 and st["groups_unequal"] == 0
    assert js["bus_groups_digest"] == r8.bg_digest(bg)


def test_valid_data_order_kept(tmp_path):
    """valid one cycle ahead as built (2 vs 3); the plan flattened both to 4 -> unequal + kept order after pads"""
    bg = dict(landing=[dict(sink="rx", sink_part="hc0", src_part="tap", members=[
        mem("v", [[0, 0]], "u_tap.v", 2, 4), mem("d", [[0, 63]], "u_tap.d", 3, 4)])], replica=[])
    msgs, st = r8.check(bg, RAW)
    assert st["groups_unequal"] == 1 and st["inversions"] == 0
    p, _ = r8.write_pads(RAW, bg, tmp_path)
    lm, js = r8.load_landing(p)
    land = {m["sink_port"]: m["landed"] for m in js["members"]}
    assert land == {"v": 4, "d": 5}                                       # valid still one cycle ahead
    assert not r8.check(bg, RAW, lm)[0]


def test_inversion_detected():
    bg = dict(landing=[dict(sink="rx", sink_part="hc0", src_part="tap", members=[
        mem("rv", [[0, 0]], "u_tap.rv", 10, 6), mem("rd", [[0, 7]], "u_tap.rd", 11, 5)])], replica=[])
    msgs, st = r8.check(bg, RAW)
    assert st["inversions"] == 1 and any("order inversion" in m for _, m in msgs)


def test_reset_and_spine_exempt():
    bg = dict(landing=[dict(sink="x", sink_part="hc0", src_part="tap", members=[
        mem("hbm_rst_n", [[0, 0]], "host.hbm_rst_n", 80, 2), mem("d", [[0, 7]], "u_tap.d", 1, 3),
        mem("q", [[0, 0]], "host.boot", 90, 2, lane="spine")])], replica=[])
    msgs, st = r8.check(bg, RAW)
    assert not msgs and st["async_skipped"] == 2


def test_type_pads_must_agree(tmp_path):
    """two instances of type ts fed by one replica set at different depths: their pads differ -> type ERROR"""
    bg = dict(landing=[dict(sink=f"s_{k}.u", sink_part=f"s_{k}_x", src_part="tap",
                            members=[mem("d", [[0, 3]], "u_tap.y", 0, b)]) for k, b in (("A", 2), ("B", 5))],
              replica=[dict(source="u_tap.y", source_bits=[[0, 3]], asbuilt_stages=0, sink_parts=["s_A_x", "s_B_x"])])
    p, _ = r8.write_pads(RAW, bg, tmp_path)
    msgs, st = r8.check(bg, RAW, r8.load_landing(p)[0])
    assert st["types_conflicting"] == 1 and any("R8 type ts" in m for _, m in msgs)


def test_replica_type_mode():
    bg = heads()
    N, uf, used = r8.classes(bg, RAW, replica="type")
    assert used == 0                                                      # heads are distinct types
    N, uf, used = r8.classes(bg, RAW, replica="all")
    assert used == 2 and len({uf.find(i) for i in range(len(N))}) == 1
