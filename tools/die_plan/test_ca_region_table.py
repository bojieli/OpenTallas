"""DIE-S81-92 (COORD 11-15, FABLE-PD-S81-0335 B(c)): S81 strap-form CA region table resolves partitions by their
DECLARED region; overlapping region boxes are allowed (fallback_land.table refuses them)."""
import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("crt", Path(__file__).with_name("ca_region_table.py"))
crt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(crt)


def plan():
    # r1 = {a, c}, r2 = {b}: the r1 bounding box (a at x 0..10, c at x 20..30) covers b's centre (x 15)
    types = {"T": {"outline_um": [10, 10]}}
    parts = [dict(name="a", type="T", origin_um=[0, 0]), dict(name="b", type="T", origin_um=[10, 0]),
             dict(name="c", type="T", origin_um=[20, 0])]
    ports = [dict(id="ab", src=dict(part="a"), dst=dict(part="b"), width=4),
             dict(id="ac", src=dict(part="a"), dst=dict(part="c"), width=2),
             dict(id="cb", src=dict(part="c"), dst=dict(part="b"), width=1, kind="ctl"),
             dict(id="io", src=dict(part="@pad"), dst=dict(part="a"), width=1)]
    return dict(partition_types=types, partitions=parts, ports=ports,
                lanes=[dict(id="L0", ports=["ab", "ac"]), dict(id="L1", ports=["cb"])])


MAP = {"a": "r1", "c": "r1", "b": "r2"}


def test_overlapping_boxes_resolved_by_declaration():
    t = crt.declared_table(plan(), MAP)
    regs = {r["tag"]: r for r in t["regions"]}
    assert regs["r1"]["box_um"] == [0, 0, 30, 10] and regs["r1"]["members"] == ["a", "c"]
    assert regs["r2"]["box_um"] == [10, 0, 20, 10] and regs["r2"]["parts"] == 1
    assert t["part_region"] == MAP
    ports = {p["port"]: p for p in t["ports"]}
    assert set(ports) == {"ab", "cb"}                     # ac is intra-region, io is a pad port
    assert ports["ab"]["src_region"] == "r1" and ports["ab"]["dst_region"] == "r2" and ports["ab"]["lane"] == "L0"
    assert ports["cb"]["kind"] == "ctl" and ports["cb"]["width"] == 1 and ports["cb"]["added_cycles"] == 3


def test_fallback_land_refuses_the_same_map(tmp_path):
    import json
    m = tmp_path / "m.json"
    m.write_text(json.dumps({"part_region": MAP}))
    fallback_script = Path(__file__).resolve().parents[1] / "s81_head" / "fallback_land.py"
    fallback_spec = importlib.util.spec_from_file_location("head_fallback_land", fallback_script)
    fallback = importlib.util.module_from_spec(fallback_spec)
    fallback_spec.loader.exec_module(fallback)
    with pytest.raises(SystemExit):
        fallback.table(plan(), "map:" + str(m))


def test_identity_map_gives_partition_regions():
    t = crt.declared_table(plan(), {"a": "a", "b": "b", "c": "c"})
    assert len(t["regions"]) == 3 and {p["port"] for p in t["ports"]} == {"ab", "ac", "cb"}


def test_fail_closed_on_missing_or_unknown_partitions():
    with pytest.raises(ValueError, match="misses 1"):
        crt.declared_table(plan(), {"a": "r1", "b": "r2"})
    with pytest.raises(ValueError, match="not in the plan"):
        crt.declared_table(plan(), dict(MAP, z="r3"))


def test_cli(tmp_path):
    import json
    p, m, o = tmp_path / "p.json", tmp_path / "m.json", tmp_path / "t.json"
    p.write_text(json.dumps(plan()))
    m.write_text(json.dumps({"part_region": MAP}))
    assert crt.main([str(p), "--regions", str(m), "--out", str(o)]) == 0
    assert json.loads(o.read_text())["granularity"] == "declared"


def test_isolated_cli_without_head_tool(tmp_path):
    import json
    import shutil
    import subprocess
    import sys

    tools = tmp_path / "tools" / "die_plan"
    tools.mkdir(parents=True)
    script = shutil.copyfile(crt.__file__, tools / "ca_region_table.py")
    shutil.copyfile(Path(__file__).with_name("fallback_land.py"), tools / "fallback_land.py")
    p, m, o = tmp_path / "p.json", tmp_path / "m.json", tmp_path / "t.json"
    data = plan()
    data["partition_types"]["T"]["outline_um"] = [10, 4]
    data["partitions"][1]["orient"] = "MYR90"
    p.write_text(json.dumps(data))
    m.write_text(json.dumps({"part_region": MAP}))
    subprocess.run([sys.executable, "-I", script, str(p), "--regions", str(m), "--out", str(o)], check=True)
    table = json.loads(o.read_text())
    assert table["regions"][1]["box_um"] == [10, 0, 14, 10]
    assert table["added_cycles_per_crossing"] == 3
    assert all(port["added_cycles"] == 3 for port in table["ports"])


def test_clock_landings_uses_declared_regions_with_overlapping_boxes():
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from test_clock_landings import vehicle
    from clock_landings import Landings, LandingError
    p, t = vehicle()
    t["regions"][0]["box_um"] = [0, 0, 20, 10]           # r0 box now also covers b's centre: overlap
    with pytest.raises(LandingError, match="expected one whole-partition region"):
        Landings(p, t)
    t["part_region"] = {"a": "r0", "b": "r1"}
    c = Landings(p, t)
    assert c.region == {"a": "r0", "b": "r1"}
    t["part_region"] = {"a": "r0"}
    with pytest.raises(LandingError, match="not in the table part_region"):
        Landings(p, t)
