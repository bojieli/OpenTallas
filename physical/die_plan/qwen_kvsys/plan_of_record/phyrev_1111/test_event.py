"""phyrev_1111: reversed core->face station entries are flipped; nothing else changes; idempotent."""
import importlib.util, json
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("phyrev_event", HERE / "event.py")
ev = importlib.util.module_from_spec(spec); spec.loader.exec_module(ev)


def _plan():
    st = [{"conn": "bus:o_x", "from_um": [864.0, 619.5], "to_um": [306.6, 963.4],
           "regs_um": [[686.2, 734.2], [508.5, 848.8], [330.7, 963.4]], "launch": "u_core.pi2", "capture": "face flop"},
          {"conn": "bus:i_y", "from_um": [864.0, 100.0], "to_um": [306.6, 200.0],
           "regs_um": [[686.2, 120.0], [330.7, 190.0]], "launch": "face", "capture": "u_core.pi0"}]
    t = {"outline_um": [864.0, 1520.64], "internal_stations": st}
    return {"die": {}, "partition_types": {"kv3_phy": t, "kv3_phy_v1": json.loads(json.dumps(t)), "kv3_other": {"outline_um": [1, 1]}}}


def test_flip_only_reversed_entries():
    text = json.dumps(_plan(), indent=1) + "\n"
    out, done = ev.apply(text)
    q = json.loads(out)
    assert len(done) == 2
    e, f = q["partition_types"]["kv3_phy"]["internal_stations"]
    assert e["from_um"] == [306.6, 963.4] and e["to_um"] == [864.0, 619.5]
    assert e["regs_um"][0] == [330.7, 963.4] and e["regs_um"][-1] == [686.2, 734.2]
    assert f == _plan()["partition_types"]["kv3_phy"]["internal_stations"][1]
    assert q["partition_types"]["kv3_other"] == {"outline_um": [1, 1]}
    out2, done2 = ev.apply(out)
    assert out2 == out and done2 == []
