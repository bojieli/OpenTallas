"""PATH-HBM-R13 multicast/direction lane model + structural options: synthetic checks (new opt-in tool)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hbm_r13_mcast as M  # noqa: E402
import hbm_r10_delta as R10  # noqa: E402


def _hub():
    # 1000x400 hub, core A (output 'o' 10 b, input 'i' 6 b); out buses Lo1 (N) / Lo2 (S) 10 b each, in bus Li (W) 6 b
    cores = [dict(inst="A", module="m", origin_um=[400.0, 100.0], outline_um=[200.0, 200.0])]
    st = []
    for b, fp in (("Lo1", [500.0, 400.0]), ("Lo2", [500.0, 0.0])):
        st.append(dict(conn="bus:" + b, launch="A.o", capture="face bus " + b, from_um=[500.0, 300.0], to_um=fp,
                       bits=10, regs_um=[]))
        st.append(dict(conn="bus:" + b, launch="A.i", capture="face bus " + b, from_um=[400.0, 200.0], to_um=fp,
                       bits=6, regs_um=[]))
    st.append(dict(conn="bus:Li", launch="face bus Li", capture="A.o", from_um=[0.0, 200.0], to_um=[500.0, 300.0],
                   bits=10, regs_um=[]))
    st.append(dict(conn="bus:Li", launch="face bus Li", capture="A.i", from_um=[0.0, 200.0], to_um=[400.0, 200.0],
                   bits=6, regs_um=[]))
    buses = [dict(name="Lo1", dir="out", width=10), dict(name="Lo2", dir="out", width=10),
             dict(name="Li", dir="in", width=6)]
    return dict(outline_um=[1000.0, 400.0], hard_cores=cores, internal_stations=st, buses=buses)


def test_ports_parse():
    d = M.module_ports("module m(input wire [3:0] a, b, output logic o, /* x */ input c); endmodule")
    assert d == {"a": "input", "b": "input", "o": "output", "c": "input"}


def test_direction_and_multicast_shared_net():
    t = _hub()
    st, rep = M.resolve_lanes_mcast(t, {}, dirs={"m": {"o": "output", "i": "input"}})
    lanes = [s for s in st if s.get("r10")]
    # output o feeds BOTH out buses at full width (one cover + one multicast copy), input i only from Li
    o = sorted((s["r10"]["bus"], s["bits"], s.get("r13", "cover")) for s in lanes if s["launch"] == "A.o")
    assert [x[:2] for x in o] == [("Lo1", 10), ("Lo2", 10)] and {x[2] for x in o} == {"cover", "mcast"}
    i = [(s["r10"]["bus"], s["bits"]) for s in lanes if s.get("capture") == "A.i" or s.get("launch") == "A.i"]
    assert i == [("Li", 6)]
    assert rep["mcast_bits"] == 10 and rep["unused_bus_bits"] == 0
    # same source net (launch, from) for the copy -> one bundle in the per-sink cut
    assert len({(s["launch"], tuple(s["from_um"])) for s in lanes if s["launch"] == "A.o"}) == 1
    # direction-blind R10 leaves 10 out bits unused
    _, r10 = R10.resolve_lanes(_hub(), {}, log=lambda *a: None)
    assert r10["unused_bus_bits"] >= 10


def test_face_affine_moves_we_legs_to_face_copy():
    s = dict(conn="bus:L", bits=6, r9_share=0.5, _r13_bits=10, _r13_id=7)
    Q = dict(S=2, stations=[(dict(s), ("C", "u__q0", (1.0, 1.0)), ("F", None, (1000.0, 50.0)), 0, 1),
                            (dict(s, bits=5), ("C", "u__q1", (1.0, 1.0)), ("F", None, (1000.0, 50.0)), 1, 1)])
    moved = M.face_affine(Q, 1000.0)
    assert len(Q["stations"]) == 1 and Q["stations"][0][1][1] == "u__q1" and Q["stations"][0][0]["bits"] == 10
    assert moved == 6


def test_joint_face_pins_moves_whole_face_pins_off_partner_group():
    fixed = [dict(from_um=[100.0, 0.0], to_um=[500.0, 200.0], bits=60, regs_um=[],
                  r10=dict(face="S", fend="from", bus="P", ivx=[50.0, 150.0], ivy=[0.0, 400.0]))]
    flex = [dict(from_um=[101.0, 0.0], to_um=[500.0, 200.0], bits=60, regs_um=[],
                 r10=dict(face="S", fend="from", bus="F", ivx=[0.0, 1000.0], ivy=[0.0, 400.0]))]
    st = fixed + flex
    moved, peak = M.joint_face_pins(st, 1000.0, 400.0, 6.0)
    assert moved == 1 and st[0]["from_um"][0] == 100.0 and abs(st[1]["from_um"][0] - 100.0) >= 9.0
    assert peak["S"] <= 6.0 + 1e-9
