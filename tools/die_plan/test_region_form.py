"""QC-REGION-1: region_form.plain_regions + schema link_htree keys."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import region_form as RF  # noqa: E402
import schema as S  # noqa: E402


def _plan(landed):
    parts = [dict(name=n) for n in ("a", "b", "c", "d", "e")]
    ports = [dict(id=f"{s}{d}", src=dict(part=s), dst=dict(part=d)) for s, d in
             (("a", "b"), ("b", "c"), ("c", "d"), ("d", "e"))]
    ports.append(dict(id="xd", src=dict(part="die"), dst=dict(part="d")))
    return dict(partitions=parts, ports=ports,
                clock=dict(landing_network=dict(count_aligned_cycles={p: 2 for p in landed})))


def test_plain_regions_components():
    pr = RF.plain_regions(_plan(["bc"]))
    assert pr == dict(a="a", b="a", c="c", d="c", e="c")


def test_plain_regions_all_landed_singletons():
    pr = RF.plain_regions(_plan(["ab", "bc", "cd", "de"]))
    assert pr == {p: p for p in "abcde"}


def test_schema_spine_link_htree():
    sp = S.SCHEMA["properties"]["clock"]["properties"]["spine"]["properties"]
    assert "link_htree" in sp["topology"]["enum"]
    assert {"path", "sha256"} <= set(sp["region_map"]["required"])
    assert {"path", "sha256", "root"} <= set(sp["feed"]["required"])
