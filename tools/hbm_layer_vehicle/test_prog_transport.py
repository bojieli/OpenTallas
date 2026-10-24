#!/usr/bin/env python3
"""prog_transport lane pricing: K from landing ties, Graph.lane_latency rule (relay 1, landing ceil(N/2)+1+E)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import prog_transport as PT


def chain(n_half, k, rly):
    inst, hops = {}, []
    for i in range(n_half):
        inst[f"h{i}"] = ("hbfd_lh_136_EW_tw", {}); hops.append(f"h{i}")
    kb = format(k, "03b")
    inst["L"] = ("hbfd_land_136_EW_tw", {"k2": f"1'd{kb[0]}", "k1": f"1'd{kb[1]}", "k0": f"1'd{kb[2]}"}); hops.append("L")
    for i in range(rly):
        inst[f"r{i}"] = ("hbfd_rly_136_WE_tw", {}); hops.append(f"r{i}")
    return inst, hops


def test():
    # r18h5 pgp_SW.start: LAND n79 K1 + 13 relays = 40 + 1 + 1 + 13 = 55; cfg_we: LAND n54 K4 = 27 + 1 + 1 = 29
    assert PT.lane_latency(*chain(79, 1, 13))[0] == 55
    assert PT.lane_latency(*chain(54, 4, 0))[0] == 29
    # hcollgi_SW.launch_v: LAND n15 K1 + 38 relays = 48 (= transport_r18h5_kq.json launch_edges, contract-note K)
    assert PT.lane_latency(*chain(15, 1, 38))[0] == 48
    # E = 8 when K == ceil(N/2) mod 8
    assert PT.lane_latency(*chain(16, 0, 0))[0] == 8 + 1 + 8
    assert PT.tie_k({"k2": "1'd1", "k1": "1'd0", "k0": "1'd1"}) == 5
    assert PT.tie_k({"k2": "x", "k1": "1'd0", "k0": "1'd1"}) is None
    print("test_prog_transport PASS")


if __name__ == "__main__":
    test()
