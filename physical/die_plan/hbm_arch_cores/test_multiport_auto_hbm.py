"""DIE-HBM-61/HOLD 11-03 (class MULTIPORT-HOLD + CLK-BAND): default-on forms of gen_core_kit_hbm.

A native multi-port core (vms_bank q0_faces: clk + clk_n/e/s/w + clk_macro*) without a reviewed density contract used
to get one independent TritonCTS tree per port, padded only to the fixed 250-ps tap target -> face trees 50-95 ps early
-> face->body zero-logic FF hold -158..-212 ps (d44v vb64bbf321780, v39c3624d7cc9, v5d4099d7f96c).  The generator now
takes the reviewed per-port density + common alignment form by default for that class (--multiport-density off = old),
and writes the typed hard_core_latency contract by default (--no-hard-core-latency = old)."""
import argparse
import importlib.util
import json
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("coregen_mpa", HERE / "gen_core_kit_hbm.py")
coregen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(coregen)

VMS = ["clk", "clk_e", "clk_macro0", "clk_macro1", "clk_macro2", "clk_n", "clk_s", "clk_w"]


def test_auto_applies_to_plain_native_multiport():
    assert coregen.multiport_density_auto(VMS, None, None, None, "off")


@pytest.mark.parametrize("clocks,contract,profile,sites,taps,mode", [
    (["clk"], None, None, None, "off", "auto"),                 # single clock: unchanged
    (["clk", "clk"], None, None, None, "off", "auto"),          # one distinct port
    (VMS, "reviewed.json", None, None, "off", "auto"),          # reviewed contract wins
    (VMS, None, {"x": 1}, None, "off", "auto"),                 # source-profile cuts keep the explicit hold
    (VMS, None, None, [[1, 2]], "off", "auto"),                 # planned clock sites keep their form
    (VMS, None, None, None, "off", "off"),                      # opt-out
])
def test_auto_not_applied(clocks, contract, profile, sites, taps, mode):
    assert not coregen.multiport_density_auto(clocks, contract, profile, sites, taps, mode)


def test_auto_applies_on_density_request():
    # 11-05 B5: --clock-taps density on a multi-port core takes the auto form, not the CTS hold
    assert coregen.multiport_density_auto(VMS, None, None, None, "density", "auto")


def test_auto_contract_is_exact_and_valid(tmp_path):
    c = coregen.auto_multiport_density_contract("hfd_vms_bank_native_q0_faces", VMS[::-1])
    assert c["clock_ports"] == sorted(VMS) and c["merge_roots"] is False and c["common_alignment"] is True
    assert c["layout"] == "density" and c["review"]["verdict"] == "AUTO"
    assert c["delay_cell"] == "BUFx12_ASAP7_75t_R"
    # same schema the reviewed path accepts once a geometry review marks it PASS
    p = tmp_path / "c.json"
    p.write_text(json.dumps(dict(c, review=dict(verdict="PASS"))))
    assert coregen.multiport_density_contract(p, "hfd_vms_bank_native_q0_faces", VMS)["clock_ports"] == sorted(VMS)


def _parse(argv):
    """The generator's own flag definitions (hard-core-latency pair) on a bare parser."""
    src = (HERE / "gen_core_kit_hbm.py").read_text()
    assert 'dest="hard_core_latency", action="store_true", default=True' in src
    assert 'dest="hard_core_latency", action="store_false"' in src
    assert '"--multiport-density", default="auto"' in src
    ap = argparse.ArgumentParser()
    ap.add_argument("--hard-core-latency", dest="hard_core_latency", action="store_true", default=True)
    ap.add_argument("--no-hard-core-latency", dest="hard_core_latency", action="store_false")
    return ap.parse_args(argv)


def test_hard_core_latency_default_on_with_opt_out():
    assert _parse([]).hard_core_latency is True
    assert _parse(["--hard-core-latency"]).hard_core_latency is True
    assert _parse(["--no-hard-core-latency"]).hard_core_latency is False


def test_contract_written_by_default(tmp_path):
    (tmp_path / "sdc_lint.json").write_text(json.dumps(dict(time_unit_ps=1.0, insertion_ff_ps=202.5, insertion_tol_ps=40)))
    coregen.write_boundary_context(tmp_path, VMS, ["rst_n"], _parse([]).hard_core_latency)
    cj = json.loads((tmp_path / "core.json").read_text())
    assert cj["clock_contract"]["kind"] == "hard_core_latency"


def test_auto_config_lines_follow_density_contract():
    src = (HERE / "gen_core_kit_hbm.py").read_text()
    i = src.index("multiport_density_auto(clks, a.clock_density_contract")
    assert 'a.clock_taps = "density"' in src[i:i + 400]
    assert 'cfg.append("export OT_DTAP_DELAY_CELL = " + density_contract["delay_cell"])' in src
    # the explicit MULTIPORT_CTS_HOLD guard stays for every multi-port kit that has no contract
    assert "and not density_contract" in src
