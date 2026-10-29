"""DIE-KV-13: write-group prep + check (fixture: the dcal bcfg group as built 6/6/5/5)."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[3] / "tools/die_plan"))
import r8_write_groups as WG  # noqa: E402
import r8  # noqa: E402

G = WG.load_groups(HERE / "write_groups.json")


def bg():
    ms = [dict(sink_port=p, sink_bits=[[0, w - 1]], source=f"kvs_ctl.boot__link_cfg_{p[5:]}", source_bits=[[0, w - 1]],
               asbuilt_stages=a, bound_stages=b, landed_stages=b, lane=l)
          for p, w, a, b, l in (("bcfg_addr", 6, 6, 55, "L1431"), ("bcfg_data", 32, 6, 56, "L1432"),
                                ("bcfg_rx_we", 1, 5, 53, "L1433"), ("bcfg_tx_we", 1, 5, 53, "L1434"))]
    return dict(die="qwen_kvsys", landing=[dict(sink="dcal", sink_part="sys_c", src_part="hub_C", members=ms)], replica=[])


def raw():
    return dict(die="qwen_kvsys", partitions=[dict(name="sys_c", type="kv3_sys_c"), dict(name="hub_C", type="kv3_hub_C")])


def table(b):
    mem = r8.solve(b, raw(), replica="type", bus="leaf")
    mem = mem[0] if isinstance(mem, tuple) else mem
    return dict(members=mem)


def test_generic_r8_lands_we_early_and_check_catches_it():
    bad, _ = WG.check(table(bg()), G)
    assert bad and "ONE edge" in bad[0]


def test_prep_lands_group_on_one_edge_ids_kept():
    b, rep = WG.prep(bg(), G)
    assert rep[0]["event_stage"] == 6
    t = table(b)
    land = {m["sink_port"]: m["landed"] for m in t["members"]}
    assert land == {"bcfg_addr": 56, "bcfg_data": 56, "bcfg_rx_we": 56, "bcfg_tx_we": 56}
    assert {m["sink_port"]: m["pad"] for m in t["members"]}["bcfg_rx_we"] == 3
    assert any(m["id"].endswith("@5") for m in t["members"])
    assert WG.check(t, G)[0] == []


def test_partial_group_fails_closed():
    b = bg(); b["landing"][0]["members"].pop()
    try:
        WG.prep(b, G)
    except SystemExit as e:
        assert "ports" in str(e)
    else:
        raise AssertionError("partial group accepted")


def test_bindview_raw_asbuilt_same_landing():
    t = table(WG.prep(bg(), G)[0])
    v, n = WG.bindview(t, G)
    assert n == 2
    by = {m["sink_port"]: m for m in v["members"]}
    assert by["bcfg_rx_we"]["asbuilt"] == 5 and by["bcfg_rx_we"]["asbuilt_group"] == 6 and by["bcfg_addr"]["asbuilt"] == 6
    assert {p: m["landed"] for p, m in by.items()} == {p: m["landed"] for p, m in ((m["sink_port"], m) for m in t["members"])}
    assert WG.check(v, G)[0] == []


if __name__ == "__main__":
    for k, f in list(globals().items()):
        if k.startswith("test_"):
            f()
            print("PASS", k)
