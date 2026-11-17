"""ft_polarity_local.tcl station matching on the real bound FT names (S81 t47 current819 kit: u_bound.u_ft_ft2_o_5 /
u_bound.u_ft_ft6_o_7 last stations; the canonical _sN form) and its opt-in (gen_phys._ft_polarity_local)."""
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
TCL = HERE / "ft_polarity_local.tcl"

NAMES = {   # instance name -> expected station group ('' = not an FT station flop)
    "u_bound.u_ft_ft2_o_5/q[597]$_DFF_P_": "u_bound.u_ft_ft2_o_5",
    "u_bound.u_ft_ft6_o_7/q[22]$_DFF_P_": "u_bound.u_ft_ft6_o_7",
    "u_bound.u_ft_ft2_i_0/q[1]$_DFF_P_": "u_bound.u_ft_ft2_i_0",
    "u_ft_spare_ft2_o_s3/q[1]$_DFF_P_": "u_ft_spare_ft2_o_s3",
    "u_ft_ft2_o_s5/q[1]$_DFF_P_": "u_ft_ft2_o_s5",
    "u_bound.u_ft_ft2_o_5/eq$_DFF_PNN_": "",
    "u_bound.u_ft_ft2_o_5/_1269_": "",
    "u_bound.u_u_lf1_u_vp_g_wr1_u_w.wdo_q[1][14]$_DFF_P_": "",
}


def station_regexes():
    res = re.findall(r"regexp \{(\^[^}]*)\} \$fpl_name -> fpl_group", TCL.read_text())
    assert len(res) == 2 and res[0] == res[1], res      # group scan and placement use one pattern
    return res[0]


@pytest.mark.skipif(shutil.which("tclsh") is None, reason="tclsh not installed")
def test_station_regex_matches_bound_and_canonical_names():
    pat = station_regexes()
    script = "".join(f"puts [expr {{[regexp {{{pat}}} {{{n}}} -> g] ? $g : {{-}}}}]\n" for n in NAMES)
    out = subprocess.run(["tclsh"], input=script, capture_output=True, text=True, check=True).stdout.split()
    assert out == [g or "-" for g in NAMES.values()]


def test_opt_in_three_ways(monkeypatch):
    import gen_phys as G
    monkeypatch.delenv("OT_FT_POLARITY_LOCAL", raising=False)
    tn = "ot_s81sl_leaf__t47"
    assert not G._ft_polarity_local({}, tn)
    assert G._ft_polarity_local({"ft_polarity_local": True}, tn)
    assert G._ft_polarity_local({"ft_polarity_local_types": ["ot_s81sl_leaf__t47"]}, tn)
    assert G._ft_polarity_local({"ft_polarity_local_types": ["ot_s81sl_leaf"]}, "ot_s81sl_leaf__t62")
    assert not G._ft_polarity_local({"ft_polarity_local_types": ["ot_s81sl_leaf__t28"]}, tn)
    monkeypatch.setenv("OT_FT_POLARITY_LOCAL", "1")
    assert G._ft_polarity_local({}, tn)


def test_hook_is_shipped_and_sourced():
    src = (HERE / "gen_phys.py").read_text()
    assert '"ft_polarity_local.tcl"' in src
    assert 'export OT_FT_POLARITY_LOCAL = 1' in src
    assert "source /work/ft_polarity_local.tcl" in (HERE / "face_flops.tcl").read_text()
