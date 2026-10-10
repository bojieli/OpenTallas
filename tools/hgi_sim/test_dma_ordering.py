"""Check DMA dependency ordering with pipelined record service (no checkpoint or RTL build)."""
from hgi_sim import timing as T
from hgi_sim.qwen_compiler import Builder
from hgi_sim.records import MDesc, Rec


def check():
    vm = lambda base: MDesc(space="VM", fmt="FP32", base=base, n=8)
    hb = lambda base: MDesc(space="HBM", fmt="FP32", base=base, n=8)
    b = Builder(None)
    b.add(Rec("DMA", "LOAD", desc=dict(A=hb(0), O=vm(0)), tag="load"), [], ["buf"])
    b.add(Rec("DMA", "STORE", desc=dict(A=vm(0), O=hb(1024)), tag="store"), ["buf"], [])
    b.add(Rec("DMA", "LOAD", desc=dict(A=hb(32), O=vm(0)), tag="reload"), [], ["buf"])
    b.add(Rec("DMA", "LOAD", desc=dict(A=hb(64), O=vm(64)), tag="independent"), [], ["other"])
    recs = T.rebuild_waits(b.recs)
    result = T.schedule(recs, 0, "S2", cost_fn=lambda r, d, L: (100, "test", "pipelined DMA"))
    assert not result["races"], result["races"]
    assert result["start"][1] >= result["end"][0]
    assert result["start"][2] >= result["end"][1]
    assert result["start"][3] < result["end"][2], "independent DMA lost overlap"
    for r in recs:
        r.wait = 0
    negative = T.schedule(recs, 0, "S2", cost_fn=lambda r, d, L: (100, "test", "pipelined DMA"))
    assert negative["races"], "missing waits were not detected"
    print("DMA dependent LOAD/STORE/reload ordered, independent LOAD overlaps; missing-wait mutant fails: PASS")


if __name__ == "__main__":
    check()
