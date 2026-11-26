"""gen_phys logic_cluster_rects_um (QC-GLUE 11-25, opt-in)."""
from types import SimpleNamespace as N
import pytest
import logic_cluster as LC


def plan(rows):
    t = dict(outline_um=[100, 50])
    if rows is not None:
        t["logic_cluster_rects_um"] = rows
    return N(types={"T": t})


ROW = dict(name="rec", patterns=[r"^u_bound\.u_sys_face\.u_ot_pr_core\.u_record\."], rect_um=[10, 5, 60, 40])


def test_absent_key_emits_nothing():
    assert LC.tcl(plan(None), "T") == ""


def test_emits_region_group_and_checks():
    s = LC.tcl(plan([ROW, dict(name="rx", patterns=["rx_payload__ot_q", "u_head_tx"], rect_um=[0, 0, 5, 5])]), "T")
    assert "odb::dbRegion_create" in s and "INCLUSIVE" in s and "odb::dbGroup_create $reg $name" in s
    assert "ot_logic_cluster rec 10 5 60 40 [list {" in s
    assert "matches no instance" in s and "exceeds 0.7" in s
    assert s.count("\not_logic_cluster ") == 2 and "{rx_payload__ot_q} {u_head_tx}" in s


@pytest.mark.parametrize("row,msg", [
    (dict(ROW, rect_um=[90, 0, 101, 5]), "outside"),
    (dict(ROW, rect_um=[5, 5, 5, 6]), "outside"),
    (dict(ROW, patterns=[]), "patterns"),
    (dict(ROW, patterns=["a{2}"]), "braces"),
    (dict(ROW, patterns=["("]), "missing|unterminated"),
    (dict(ROW, name="1x"), "invalid"),
    (dict(ROW, rect_um=[1, 2, 3]), "four"),
])
def test_bad_rows_fail_closed(row, msg):
    with pytest.raises(Exception, match=msg):
        LC.tcl(plan([row]), "T")


def test_repeated_name_and_empty_list_fail():
    with pytest.raises(ValueError, match="repeated"):
        LC.tcl(plan([ROW, ROW]), "T")
    with pytest.raises(ValueError, match="non-empty"):
        LC.tcl(plan([]), "T")


def test_cluster_inside_effective_phy_row_cut_fails_early():
    domains = [("phy", [0, 400, 2885.76, 1226.88])]
    r7e2 = dict(ROW, name="serdes_syndrome_local", rect_um=[1935.36, 400.68, 2073.6, 423.36])
    r7e3 = dict(r7e2, rect_um=[2201.04, 352.08, 2304.72, 382.32])
    crossing = dict(r7e2, rect_um=[1935.36, 395.28, 2073.6, 416.88])

    def emit(row, no_core_rows=()):
        p = N(types={"hd_serdes": dict(outline_um=[2885.76, 1226.88], logic_cluster_rects_um=[row])})
        return LC.tcl(p, "hd_serdes", no_core_rows=no_core_rows)

    with pytest.raises(ValueError, match="serdes_syndrome_local is fully inside PHY domain phy"):
        emit(r7e2, domains)
    for row in (r7e3, crossing):
        assert emit(row, domains) == emit(row)
    assert "ot_logic_cluster serdes_syndrome_local" in emit(r7e2)


def test_gen_phys_wires_the_hook():
    import gen_phys as GP
    from pathlib import Path
    src = Path(GP.__file__).read_text()
    assert "logic_cluster.tcl" in src and "import logic_cluster" in src


def test_schema_accepts_the_key():
    import schema
    props = schema.SCHEMA["properties"]["partition_types"]["additionalProperties"]["properties"]
    assert props["logic_cluster_rects_um"]["items"]["required"] == ["name", "patterns", "rect_um"]
