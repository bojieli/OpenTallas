"""PG-AWARE-1 (FABLE-WAVE-REVIEW fix 6, DRT-0255 class): PG stripes where the plan says (pdn_die_phase) and no standard
cell under an M5 x M6 PG crossing at GRT (pg_cell_keepout.tcl).
python3 -m pytest -q tools/die_plan/test_pg_aware.py"""
import copy
import json
import re
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_phys  # noqa: E402
import schema  # noqa: E402

TINY = json.loads((HERE / "examples" / "tiny_plan.json").read_text())


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for k in ("OT_RFLOW", "OT_PG_DIE_PHASE", "OT_PG_CELL_KEEPOUT", "OT_GEN_M8_GRANT"):
        monkeypatch.delenv(k, raising=False)


def stripes(pdn):
    """{layer: (width, spacing, pitch, offset)} of the partition grid {top} of a pdn text."""
    out = {}
    for m in re.finditer(r"add_pdn_stripe -grid \{top\} -layer \{(M[5-7])\} -width \{([\d.]+)\} -spacing \{([\d.]+)\} "
                         r"-pitch \{([\d.]+)\} -offset \{([\d.]+)\}", pdn):
        out[m.group(1)] = tuple(float(v) for v in m.groups()[1:])
    return out


def pair_centres(layer, core_origin, extent, pdn):
    """type-frame pair centres pdngen draws: first stripe centre = core origin + offset (pdngen measures from the core)."""
    w, s, p, off = stripes(pdn)[layer]
    c, out = core_origin + off + (w + s) / 2, []
    while c < extent:
        out.append(round(c, 4))
        c += p
    return out


def test_phase_fix_puts_every_stripe_pair_in_the_plan_band():
    core = (4.32, 4.32, 617.76, 1334.88)          # QC sle_st_b_v2 (DRT-0255 x_fw_ctl_p2_i[464])
    new = gen_phys.pdn_die_phase(gen_phys.PDN, core)
    for ln in ("M5", "M6", "M7"):
        for c in pair_centres(ln, core[1] if ln == "M6" else core[0], 600.0, new):
            assert schema.pg_blocked(ln, c), (ln, c)
    # today's kit (no fix): the M7 pairs sit half a pitch off the plan band, on the face-pin tracks
    old = pair_centres("M7", core[0], 600.0, gen_phys.PDN)
    assert old[:2] == [8.64, 17.28] and not any(schema.pg_blocked("M7", c) for c in old)
    # the measured stripe of the probe: VDD M7 181.488-181.776 (pair centre 181.44) is on a free plan track
    assert 181.44 in old and not schema.pg_blocked("M7", 181.536)


def test_phase_fix_changes_only_m7_at_the_default_margin():
    core = (4.32, 4.32, 100.0, 100.0)
    new = gen_phys.pdn_die_phase(gen_phys.PDN, core)
    a, b = stripes(gen_phys.PDN), stripes(new)
    assert a["M5"] == b["M5"] and a["M6"] == b["M6"]
    assert a["M7"][3] == 4.128 and b["M7"][3] == pytest.approx(8.448)
    diff = [(x, y) for x, y in zip(gen_phys.PDN.splitlines(), new.splitlines()) if x != y]
    assert len(diff) == 1 and "-layer {M7}" in diff[0][0]
    # zero core margin (KW-FIX-45 hard wrappers): pdngen origin = type origin, nothing changes
    assert gen_phys.pdn_die_phase(gen_phys.PDN, (0.0, 0.0, 100.0, 100.0)) == gen_phys.PDN
    # other stripes (core grids with their own width/pitch) are never touched
    other = "add_pdn_stripe -grid {c1} -layer {M7} -width {0.16} -spacing {2.0} -pitch {4.32} -offset {2.16}"
    assert gen_phys.pdn_die_phase(other, core) == other


def kit(d, monkeypatch, env=()):
    for k, v in env:
        monkeypatch.setenv(k, v)
    raw = copy.deepcopy(TINY)
    raw["die"]["name"] = "s81_head"
    kd = Path(gen_phys.write_type_kit(schema.Plan(raw), "mid", d, [], util=0.5))
    return kd, dict(re.findall(r"^export (\w+) = (.*)$", (kd / "config.mk").read_text(), re.M))


def test_kit_default_off_and_gen_env_switch(tmp_path, monkeypatch):
    kd, c = kit(tmp_path / "a", monkeypatch)
    assert c["OT_PG_CELL_KEEPOUT"] == "0" and (kd / "pg_cell_keepout.tcl").is_file()
    assert stripes((kd / "pdn.tcl").read_text())["M7"][3] == 4.128
    kd, c = kit(tmp_path / "b", monkeypatch, [("OT_PG_CELL_KEEPOUT", "1"), ("OT_PG_DIE_PHASE", "1")])
    assert c["OT_PG_CELL_KEEPOUT"] == "1"
    assert stripes((kd / "pdn.tcl").read_text())["M7"][3] == pytest.approx(8.448)


def test_keepout_hooks_are_grt_only():
    pre = (HERE / "grt_pre.tcl").read_text()
    post = (HERE / "grt_post.tcl").read_text()
    tcl = (HERE / "pg_cell_keepout.tcl").read_text()
    # before PG-TRACK-TRUTH (which stays last), gated on the kit variable; removed in POST before 5_1_grt.odb
    assert pre.index("ot_pgcko_add") < pre.index("ot_pgtt_add")
    assert '$::env(OT_PG_CELL_KEEPOUT) eq "1"' in pre and 'OT_PG_CELL_KEEPOUT) ne "1"' in tcl
    assert post.index("ot_pgcko_remove") < post.index("if {[info exists ::env(OT_TAP_GRT_MODE)]")
    assert "dbBlockage_create" in tcl and "dbBlockage_destroy" in tcl and "detailed_placement" in tcl
    import importlib.util
    spec = importlib.util.spec_from_file_location("kit_resume", HERE.parent / "autopilot" / "kit_resume.py")
    kr = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(kr)
    assert kr.VAR_STAGE["OT_PG_CELL_KEEPOUT"] == "grt"
