import plan_cut as PC


def _plan(stations, cores=()):
    return {"partition_types": {"t": {"outline_um": [100.0, 100.0], "internal_stations": stations,
                                      "hard_cores": list(cores)}}}


def test_broadcast_is_one_tree():
    st = [{"launch": "a.q", "from_um": [10.0, 50.0], "to_um": [90.0, 50.0], "bits": 100},
          {"launch": "a.q", "from_um": [10.0, 50.0], "to_um": [90.0, 60.0], "bits": 100}]
    r = PC.analyse(_plan(st))["types"]["t"]
    assert r["nets"] == 1 and r["multi_sink_nets"] == 1
    assert r["cut"]["x"]["bits"] == 100            # crosses x cuts once, not twice


def test_cut_use_and_core_blockage():
    st = [{"launch": "face bus L1", "from_um": [0.0, 50.0], "to_um": [100.0, 50.0], "bits": 1000}]
    free = PC.analyse(_plan(st))["types"]["t"]["cut"]["x"]
    # tracks across a 100-um vertical cut: 100 x 0.75 / 0.048 + 100 x 0.75 / 0.064 = 1562.5 + 1171.875
    assert free["tracks"] == 2734 and abs(free["max_use"] - 1000 / 2734.375) < 1e-3
    core = {"inst": "c", "origin_um": [20.0, 0.0], "outline_um": [40.0, 100.0]}
    blk = PC.analyse(_plan(st, [core]))["types"]["t"]["cut"]["x"]
    assert blk["tracks"] == 1171                   # M4 blocked over the core, M6 left
    assert blk["face_bits"] == 1000


def test_relaxed_moves_core_to_its_pins():
    core = {"inst": "c", "origin_um": [0.0, 0.0], "outline_um": [10.0, 10.0]}
    st = [{"launch": "face bus L1", "from_um": [95.0, 50.0], "to_um": [5.0, 5.0], "bits": 500}]
    r = PC.analyse(_plan(st, [core]), relaxed=True)["types"]["t"]
    assert r["cut"]["x"]["max_use"] > r["relaxed_cut"]["x"]["max_use"]
    assert r["repack_can_pass"] is True
