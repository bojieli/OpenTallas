"""HBM-MU-QUAD-6/CLK (COORD 10-27, 12.8a): a core clock entry / island over a hard-core macro is a G0C ERROR
(check.check_clock_entry_macro, sidecar PLANDIR/core_macros.json)."""
import json
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check


class _T:
    def __init__(self, types):
        self.types = types


SRAM = dict(name="u_sram", rect_um=[34.56, 121.5, 205.848, 199.284])


def _plan(tmp_path, xy, island, status="KNOWN", halo=0.0, inst="u_ep_N0", key=None):
    types = dict(NW_io=dict(outline_um=[1000.0, 1000.0], hard_cores=[dict(inst=inst, module="hfd_ep_static",
                                                                        origin_um=[0.0, 0.0], outline_um=[250.56, 375.84])]))
    ce = dict(NW_io={key or inst: dict(xy_um=xy, island_um=island, port="clk", module="hfd_ep_static")})
    mac = dict(schema="opentallas.core_macros.v1", halo_um=halo,
               cores=dict(hfd_ep_static=dict(status=status, outline_um=[250.56, 375.84],
                                             macros=[SRAM] if status == "KNOWN" else [])))
    (tmp_path / "clock_entries.json").write_text(json.dumps(ce))
    (tmp_path / "core_macros.json").write_text(json.dumps(mac))
    return _T(types)


def _run(P, d, completeness=True):
    R = check.Report(completeness)
    out = check.check_clock_entry_macro(P, R, d)
    return out, [i for i in R.errors() if i["check"] == "clock_entry_macro"], R


def test_entry_over_sram_fails(tmp_path):
    P = _plan(tmp_path, [125.28, 185.76], [120.96, 181.44, 129.6, 190.08])       # planU6c ep entry, inside SRAM1
    out, errs, _ = _run(P, tmp_path)
    assert out["over_macro"] == 1 and len(errs) == 1 and "u_sram" in errs[0]["msg"]


def test_entry_in_channel_passes(tmp_path):
    P = _plan(tmp_path, [125.256, 204.12], [120.96, 199.8, 129.6, 208.44])       # centre band above SRAM1
    out, errs, _ = _run(P, tmp_path)
    assert out["checked"] == 1 and out["over_macro"] == 0 and not errs


def test_touching_edge_passes_halo_fails(tmp_path):
    isl = [120.96, 199.284, 129.6, 207.924]                                       # island bottom on the SRAM top edge
    out, errs, _ = _run(_plan(tmp_path, [125.256, 203.6], isl), tmp_path)
    assert not errs
    out, errs, _ = _run(_plan(tmp_path, [125.256, 203.6], isl, halo=1.0), tmp_path)
    assert len(errs) == 1


def test_hub_split_instance_uses_parent_entry(tmp_path):
    P = _plan(tmp_path, [125.28, 185.76], [120.96, 181.44, 129.6, 190.08], inst="u_ep_N0__q1", key="u_ep_N0")
    out, errs, _ = _run(P, tmp_path)
    assert out["entries"] == 1 and len(errs) == 1


def test_unknown_macros_warn_only(tmp_path):
    out, errs, R = _run(_plan(tmp_path, [125.28, 185.76], [120.96, 181.44, 129.6, 190.08], status="UNKNOWN"), tmp_path)
    assert not errs and out["unknown_macros"] == 1
    assert any(i["check"] == "clock_entry_macro" and i["level"] == "WARN" for i in R.items)


def test_is_g0c_warn_without_completeness(tmp_path):
    assert "clock_entry_macro" in check.G0C_CHECKS
    P = _plan(tmp_path, [125.28, 185.76], [120.96, 181.44, 129.6, 190.08])
    out, errs, R = _run(P, tmp_path, completeness=False)
    assert not errs and any(i["msg"].startswith("[G0C]") for i in R.items)
