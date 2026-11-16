"""Opt-in FT endpoint placement and declared output-clock cohort contracts."""
import shutil
import subprocess
import sys
from pathlib import Path

import jsonschema
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_phys as G
import schema as S

BASE = Path(__file__).resolve().parent
SLOT = dict(name="ft0", in_face="E", out_face="W", width=512, stations=8,
            regs_um=[[2800-400*i, 200] for i in range(8)])
RX = r"(?:^|[/.])(u_enc(?=[/.])|u_ft_ft0_o_7(?=[/.]))"


def test_legacy_exports_are_unchanged():
    assert G.ft_stage0_exports({}) == []
    assert G.ft_stage0_exports({"ft_slots": [SLOT]}) == []
    assert G.ft_stage0_exports({"ft_slots": [dict(SLOT, explicit_stage0=False)]}) == []
    assert G.tap_group_exports({"clock": {"tap_group": {"re": RX}}}) == [
        "export OT_TAP_GROUP_RE = " + RX]


def test_stage0_requires_opt_in_and_complete_sites():
    assert G.ft_stage0_exports({"ft_slots": [dict(SLOT, explicit_stage0=True)]}) == [
        "export OT_FT_EXPLICIT_STAGE0 = ft0"]
    with pytest.raises(ValueError, match="all stage waypoints"):
        G.ft_stage0_exports({"ft_slots": [dict(SLOT, explicit_stage0=True, regs_um=[])]})
    with pytest.raises(ValueError, match="boolean"):
        G.ft_stage0_exports({"ft_slots": [dict(SLOT, explicit_stage0="yes")]})


def test_fixed_group_export_is_explicit_and_safe():
    assert G.tap_group_exports({"clock": {"tap_group": {
        "re": RX, "fixed_taps": {"u_ft_ft0_o_7": "clk_t41"}}}}) == [
            "export OT_TAP_GROUP_RE = " + RX,
            "export OT_TAP_GROUP_FIXED = u_ft_ft0_o_7:clk_t41"]
    with pytest.raises(ValueError, match="unsafe"):
        G.tap_group_exports({"clock": {"tap_group": {"re": RX, "fixed_taps": {"x": "clk;bad"}}}})


def test_new_plan_fields_are_schema_checked():
    typ = S.SCHEMA["properties"]["partition_types"]["additionalProperties"]["properties"]
    jsonschema.validate(dict(SLOT, explicit_stage0=True), typ["ft_slots"]["items"])
    jsonschema.validate({"re": RX, "fixed_taps": {"u_ft_ft0_o_7": "clk_t41"}},
                        typ["clock"]["properties"]["tap_group"])
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(dict(SLOT, explicit_stage0="yes"), typ["ft_slots"]["items"])


def tcl_stage0(body):
    if not shutil.which("tclsh"):
        pytest.skip("tclsh unavailable")
    source = (BASE/"face_flops.tcl").read_text()
    start = source.index("proc ff_place_explicit_stage0")
    end = source.index("# RELAY-PLACE-1 11-12", start)
    helper = source[start:end]
    mock = r"""
set ff_dbu 1
set calls {}
proc ff_lane_xy {slot bt ob xy t} {
  if {$t != 0.0} {error "stage0 used an interior-stage blend"}
  return $xy
}
proc ff_put_stage {f slot j nm xy} {
  lappend ::calls [list $f $slot $j $nm $xy]
  return $xy
}
set data_nets {D old_data CLK old_clock Q old_q}
"""
    return subprocess.run(["tclsh"], input=helper+mock+body,
                          text=True, capture_output=True)


def test_stage0_consumer_off_keeps_old_site():
    r = tcl_stage0(r"""
set got [ff_place_explicit_stage0 same_ff ft0 {ft0_i[98]} bt ob 8 {}]
puts "GOT <$got> CALLS <$calls> NETS $data_nets"
""")
    assert r.returncode == 0, r.stderr
    assert "GOT <> CALLS <> NETS D old_data CLK old_clock Q old_q" in r.stdout


def test_stage0_consumer_moves_existing_ff_at_plan_stage0():
    r = tcl_stage0(r"""
set ::env(OT_FT_EXPLICIT_STAGE0) ft0
set regs {2798 208 2395 208 1992 208 1589 208 1186 208 783 208 442 191 100 174}
puts [ff_place_explicit_stage0 same_ff ft0 {ft0_i[98]} bt ob 8 $regs]
puts "CALLS $calls NETS $data_nets"
""")
    assert r.returncode == 0, r.stderr
    assert "2798 208" in r.stdout
    assert "same_ff ft0 0" in r.stdout
    assert "NETS D old_data CLK old_clock Q old_q" in r.stdout


def test_stage0_requested_missing_plan_refuses_silently_ignoring():
    r = tcl_stage0(r"""
set ::env(OT_FT_EXPLICIT_STAGE0) ft0
if {[catch {ff_place_explicit_stage0 same_ff ft0 {ft0_i[98]} bt ob 8 {1 2}} e]} {
  puts stderr $e
  exit 1
}
""")
    assert r.returncode != 0
    assert "lacks complete waypoints/sites" in r.stderr



def test_stage0_with_legacy_internal_bit_table_uses_planned_point():
    r = tcl_stage0(r"""
set ::env(OT_FT_EXPLICIT_STAGE0) ft0
set ff_bit_site_cells {ft0 {1.404 0.27}}
set ff_bit_sites {ft0,1,98 {2400 208}}
proc ff_put_near {f x y} {puts "NEAR $f $x $y"; return [list $x $y]}
set regs {2798 208 2395 208 1992 208 1589 208 1186 208 783 208 442 191 100 174}
puts [ff_place_explicit_stage0 same_ff ft0 {ft0_i[98]} bt ob 8 $regs]
""")
    assert r.returncode == 0, r.stderr
    assert "NEAR same_ff 2798 208" in r.stdout
