"""Focused controls for the standalone historical clock-only candidate."""
import importlib.util
import os
from pathlib import Path
import pytest

P = Path(__file__).with_name("kv_hhp_clock_mesh_role.py")
spec = importlib.util.spec_from_file_location("mesh_role", P)
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)
ROOT = P.parents[5]
CAPSULE = None
INPUTS = ROOT / "results/hhp_ft_roles_1102/inputs"
PREP = ROOT / "results/hhp_historical_boundary_1102/SOURCE_PREP.json"


@pytest.fixture(scope="module", autouse=True)
def whole_capsule(tmp_path_factory):
    global CAPSULE
    if os.environ.get("HHP_HISTORICAL_CAPSULE"):
        CAPSULE = Path(os.environ["HHP_HISTORICAL_CAPSULE"])
    else:
        import tarfile
        target = tmp_path_factory.mktemp("historical_hhp")
        archive = ROOT / "results/hhp_historical_boundary_1102/complete_source_capsule_r4.tar.gz"
        with tarfile.open(archive) as tar:
            for member in tar.getmembers():
                assert not Path(member.name).is_absolute() and ".." not in Path(member.name).parts
                assert not member.issym() and not member.islnk()
            tar.extractall(target)
        CAPSULE = target / "capsule_r4"


def run(**kw):
    return M.proposal(CAPSULE, INPUTS, PREP, "pc_EN_0", **kw)


@pytest.mark.parametrize("part", ["pc_EN_0", "pc_WN_0"])
def test_exact_whole_capsule_positive(part):
    d = M.proposal(CAPSULE, INPUTS, PREP, part, enable=True)
    assert len(d["raw_private_edges"]) == 16
    assert len(d["source_public_mesh_drivers"]) == 8
    assert len(d["physical_join_intent"]) == 8
    assert len(d["ports"]) == 5
    assert all(p[-1] == "port:root" for p in d["actual_ancestry"].values())
    assert not d["qualified"] and not d["enabled_by_default"]
    assert M.fixture(d).count(M.BUF + " ") == 16


def test_default_is_existing_generic_rejection():
    with pytest.raises(M.F.FtError, match="two declared arcs"):
        run()


@pytest.mark.parametrize("kwargs,message", [({"request_type": "kv3_pc_v3"}, "TYPE"),
                                               ({"kind": "reset"}, "only clock")])
def test_wrong_type_or_control_kind(kwargs, message):
    with pytest.raises(ValueError, match=message):
        run(enable=True, **kwargs)


def test_actual_source_mutant_rejected(tmp_path):
    # Source-byte admission is required before any role can be returned.
    prep, _ = M.load_context(CAPSULE, INPUTS, PREP)
    import shutil
    for part, info in prep["parts"].items():
        dst = tmp_path / part / "rtl"
        dst.mkdir(parents=True)
        for name in info["source_files_sha256"]:
            (dst / name).symlink_to(CAPSULE / part / "rtl" / name)
    p = tmp_path / "pc_EN_0/rtl/qkd_kvs_pc_h_head_p.sv"
    text = p.read_text().replace(".Y(ft_ck_o_0__p1)", ".Y(ft_ck_o_0)")
    p.unlink()
    p.write_text(text)
    with pytest.raises(ValueError, match="actual source differs"):
        M.proposal(tmp_path, INPUTS, PREP, "pc_EN_0", enable=True)


def test_graph_source_mutant_rejected(tmp_path):
    for p in INPUTS.iterdir():
        (tmp_path / p.name).symlink_to(p)
    p = tmp_path / "historical_ft_manifest.json"
    text = p.read_text().replace("ckm_w_ckm_n10_h1111111101", "clk_t1")
    p.unlink()
    p.write_text(text)
    with pytest.raises(ValueError, match="pinned graph/manifest differs"):
        M.proposal(CAPSULE, tmp_path, PREP, "pc_EN_0", enable=True)


@pytest.mark.parametrize("mutation,message", [("polarity", "master/polarity"), ("role", "cell role"),
                                               ("missing", "missing or multiple"), ("multiple", "missing or multiple"),
                                               ("cycle", "cycle"), ("wrongroot", "missing ancestry")])
def test_ancestry_controls(mutation, message):
    placed = {"a": {"kind": "node", "lib": M.BUF}, "b": {"kind": "rep", "lib": M.BUF}}
    incoming = {"a": [{"drv": "b"}], "b": [{"drv": "port:root"}]}
    assert M.ancestry("a", incoming, placed) == ["a", "b", "port:root"]
    if mutation == "polarity": placed["b"]["lib"] = "INVx1_ASAP7_75t_R"
    if mutation == "role": placed["b"]["kind"] = "data"
    if mutation == "missing": incoming["b"] = []
    if mutation == "multiple": incoming["b"] *= 2
    if mutation == "cycle": incoming["b"] = [{"drv": "a"}]
    if mutation == "wrongroot": incoming["b"] = [{"drv": "port:data"}]
    with pytest.raises(ValueError, match=message): M.ancestry("a", incoming, placed)


def test_generic_data_multidriver_stays_rejected():
    with pytest.raises(M.F.FtError):
        M.F.declaration([dict(cell="a", source="data_a", sink="data_y", kind="clock"),
                         dict(cell="b", source="data_b", sink="data_y", kind="clock")], "control")


def test_missing_master_requires_explicit_pinned_family():
    placed = {"a": {"kind": "node"}}
    incoming = {"a": [{"drv": "port:root"}]}
    with pytest.raises(ValueError, match="missing actual master"):
        M.ancestry("a", incoming, placed)
    with pytest.raises(ValueError, match="source-family"):
        M.ancestry("a", incoming, placed, {})
    assert M.ancestry("a", incoming, placed, {"a": {"kind": "node", "master": M.BUF}}) == ["a", "port:root"]


@pytest.mark.parametrize("extra", ["assign mesh = 1'b0;", "BUFx4 rogue (.A(data), .Y(mesh));", "assign data = mesh;", "always @* mesh = data;"])
def test_unclassified_source_driver_or_use_rejected(extra):
    call = "BUF normal (.A(clock), .Y(mesh));"
    source = "module t(input wire clock, output wire mesh, input wire data); " + call + " endmodule"
    assert M.closed_reference_census(source, {"clock", "mesh"}, [call])["unclassified_references"] == 0
    with pytest.raises(ValueError, match="unclassified extra"):
        M.closed_reference_census(source.replace("endmodule", extra + " endmodule"), {"clock", "mesh"}, [call])
