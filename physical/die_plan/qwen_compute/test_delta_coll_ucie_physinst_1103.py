"""delta_coll_ucie_physinst_1103: coll_ucie PHY content gets the bound-kit physical identity; nothing else changes."""
import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "tools" / "die_plan"))
spec = importlib.util.spec_from_file_location("dcu", HERE / "delta_coll_ucie_physinst_1103.py")
D = importlib.util.module_from_spec(spec)
spec.loader.exec_module(D)


def _plan():
    return {"partition_types": {
        "coll_ucie": {"contents": [
            {"inst": "u_io_ucie", "module": "ot_qfd_ucie_x64_phy", "status": "reuse", "origin_um": [0.0, 0.0],
             "outline_um": [777.6, 777.6], "lef": "x.lef"},
            {"inst": "u_shared", "module": "qfd_ucie_static_share", "status": "reuse"}]},
        "native59": {"contents": [{"inst": "u_bound.u_core.u_mem", "module": "ot_sram", "lef": "s.lef",
                                   "origin_um": [1.0, 1.0]}]}}}


def test_sets_identity_and_only_that():
    p = _plan()
    before = copy.deepcopy(p)
    assert D.apply(p) is True
    c = p["partition_types"]["coll_ucie"]["contents"][0]
    assert (c["physical_inst"], c["physical_master"]) == ("u_bound.u_io_ucie", "ot_qfd_ucie_x64_phy")
    c.pop("physical_inst"), c.pop("physical_master")
    assert p == before


def test_idempotent():
    p = _plan()
    D.apply(p)
    assert D.apply(p) is False


def test_gen_phys_places_bound_path():
    import gen_phys
    p = _plan()
    D.apply(p)
    P = type("P", (), {"types": p["partition_types"]})
    names = [m[0] for m in gen_phys.type_macros(P, "coll_ucie")]
    assert names == ["u_bound.u_io_ucie"]


def test_refuses_conflicting_identity():
    p = _plan()
    p["partition_types"]["coll_ucie"]["contents"][0].update(physical_inst="u_x", physical_master="ot_qfd_ucie_x64_phy")
    with pytest.raises(SystemExit):
        D.apply(p)


def test_refuses_missing_content():
    p = _plan()
    p["partition_types"]["coll_ucie"]["contents"].pop(0)
    with pytest.raises(SystemExit):
        D.apply(p)


def test_main_roundtrip_bytes(tmp_path):
    p = _plan()
    f = tmp_path / "plan.json"
    f.write_text(json.dumps(p) + "\n")
    sys.argv = ["x", str(f)]
    D.main()
    out = f.read_text()
    q = json.loads(out)
    D_ = q["partition_types"]["coll_ucie"]["contents"][0]
    assert D_["physical_inst"] == "u_bound.u_io_ucie" and out.endswith("\n") and "\n" not in out[:-1]
