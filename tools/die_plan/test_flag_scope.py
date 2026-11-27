"""FLAG-SCOPE 11-27 (HEAD-INT-R3 W13 ruling, HEAD-EAST-R4): optional `types` regex on the top-level plan flags gpl_td and street_sizing.
Absent types = every type (the 11-26 behaviour, byte-identical); with types only the matching partition types get the flag."""
import json
import math
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import adv_fp_floorplan as F  # noqa: E402
import adv_gpl_td as AG  # noqa: E402
import gpl_td as GT  # noqa: E402
import street_rule as SR  # noqa: E402
from test_adv_fp_floorplan import _type  # noqa: E402

HERE = Path(__file__).resolve().parent
FLAG = {"top_overflow_trigger": 1, "firm_small_clusters": 1, "cell_growth_gate": 2}


def _kit(tmp_path, name):
    kd = tmp_path / name
    kd.mkdir()
    for n in ("face_flops.tcl", "face_flops_release.tcl", "config.mk"):
        (kd / n).write_text("orig\n")
    return kd


def _snap(kd):
    return {p.name: p.read_bytes() for p in sorted(kd.iterdir())}


# ---------------------------------------------------------------------------------------------------------------- gpl_td
def test_unscoped_flag_is_unchanged_for_every_type():
    raw = {"gpl_td": dict(FLAG)}
    want = {"top": 0.25, "firm_small": 20, "growth": 2}
    assert GT.spec(raw) == want
    for tn in ("hd_lep0N", "hd_lep0N_w", "hd_spn_end"):
        assert GT.spec(raw, tn) == want and GT.in_scope(raw, tn)
        assert GT.cfg_lines(raw, tn) == GT.cfg_lines(raw, "other")
        assert GT.firm_small(raw, tn) == 20 and GT.post_gpl_regions(raw, tn) is True and GT.cell_growth_gate(raw, tn) == 2


@pytest.mark.parametrize("fn", ["firm_small", "post_gpl_regions", "cell_growth_gate", "cfg_lines"])
def test_per_type_entry_points_need_the_type_name(fn):
    for tn in (None, ""):
        with pytest.raises(ValueError, match="needs the partition type name"):
            getattr(GT, fn)({"gpl_td": dict(FLAG)}, tn)


def test_apply_needs_the_type_name(tmp_path):
    with pytest.raises(TypeError):
        GT.apply(_kit(tmp_path, "k"), {"gpl_td": dict(FLAG)})


def test_unscoped_apply_is_byte_identical_to_the_old_call(tmp_path):
    raw = {"gpl_td": dict(FLAG)}
    a, b = _kit(tmp_path, "a"), _kit(tmp_path, "b")
    assert GT.apply(a, raw, "hd_lep0N") is True and GT.apply(b, raw, "hd_spn_end") is True
    assert _snap(a) == _snap(b)


def test_scoped_flag_applies_only_to_matching_types(tmp_path):
    raw = {"gpl_td": dict(FLAG, types="^hd_lep0N$")}
    assert GT.spec(raw, "hd_lep0N") == {"top": 0.25, "firm_small": 20, "growth": 2}
    for tn in ("hd_lep0N_w", "hd_spn_end", "xhd_lep0N"):
        assert GT.spec(raw, tn) == {} and GT.cfg_lines(raw, tn) == [] and GT.firm_small(raw, tn) == 0
        assert GT.post_gpl_regions(raw, tn) is False and GT.cell_growth_gate(raw, tn) == 0
    on, off, none = _kit(tmp_path, "on"), _kit(tmp_path, "off"), _kit(tmp_path, "none")
    assert GT.apply(on, raw, "hd_lep0N") is True
    assert GT.apply(off, raw, "hd_spn_end") is False
    assert GT.apply(none, {}, "hd_spn_end") is False
    assert _snap(off) == _snap(none)                                   # out of scope = the unflagged kit, byte for byte
    ref = _kit(tmp_path, "ref")
    GT.apply(ref, {"gpl_td": dict(FLAG)}, "hd_lep0N")
    assert _snap(on) == _snap(ref)                                     # in scope = the 11-26 die-wide kit, byte for byte


def test_scoped_die_wide_reading_keeps_the_values():
    raw = {"gpl_td": dict(FLAG, types="^hd_lep0N$")}
    assert GT.spec(raw) == {"top": 0.25, "firm_small": 20, "growth": 2}     # tn None: validation / reports


@pytest.mark.parametrize("d", [{"types": "^x$"}, dict(FLAG, types=""), dict(FLAG, types=3), dict(FLAG, types="(")])
def test_bad_scope_fails_closed(d):
    with pytest.raises(ValueError, match="gpl_td"):
        GT.spec({"gpl_td": d}, "hd_lep0N")
    with pytest.raises(ValueError, match="gpl_td"):
        GT.spec({"gpl_td": d})


def test_gen_phys_passes_the_type_at_every_call():
    src = (HERE / "gen_phys.py").read_text()
    assert "firm_small=gpl_td.firm_small(P.raw, tn)" in src and "gpl_td.apply(kd, P.raw, tn)" in src
    assert "_gpl_td_mod.post_gpl_regions(P.raw, tn)" in src
    assert "_gpl_td_gate.cell_growth_gate(raw, type_name) != 2" in src
    assert "gpl_td.firm_small(P.raw)" not in src and "gpl_td.apply(kd, P.raw)" not in src and "post_gpl_regions(P.raw)" not in src


def test_logic_cluster_seat_text_follows_the_scope():
    import logic_cluster as LC
    from types import SimpleNamespace as N
    cl = [dict(name="s%d" % i, patterns=["u_s%d/*" % i], rect_um=[1 + 10 * i, 1, 9 + 10 * i, 9], cells=5) for i in range(2)]
    t = dict(outline_um=[100, 50], logic_cluster_rects_um=cl)
    P = N(types={"in": t, "out": t})
    scoped = {"gpl_td": dict(FLAG, types="^in$")}
    plain = {"gpl_td": dict(FLAG)}
    assert LC.tcl(P, "out", firm_small=GT.firm_small(scoped, "out")) == LC.tcl(P, "out", firm_small=GT.firm_small({}, "out"))
    assert LC.tcl(P, "in", firm_small=GT.firm_small(scoped, "in")) == LC.tcl(P, "in", firm_small=GT.firm_small(plain, "in"))
    assert GT.firm_small(scoped, "in") == 20 and GT.firm_small(scoped, "out") == 0


@pytest.mark.parametrize("raw,tn,ok", [
    ({"gpl_td": dict(FLAG)}, "hd_lep0N", True),
    ({"gpl_td": dict(FLAG, cell_growth_gate="fail")}, "hd_lep0N", True),
    ({"gpl_td": dict(FLAG, types="^hd_lep0N$")}, "hd_lep0N", True),
    ({"gpl_td": dict(FLAG, types="^hd_lep0N_w$")}, "hd_lep0N", False),     # out of scope = no hard gate for this type
    ({"gpl_td": dict(FLAG, cell_growth_gate=1)}, "hd_lep0N", False),
    ({}, "hd_lep0N", False),
])
def test_head_post_gpl_reseat_reads_the_gate_of_its_type(tmp_path, monkeypatch, raw, tn, ok):
    import gen_phys as GP
    monkeypatch.setenv("OT_HEAD_POST_GPL_RESEAT", "1")
    cfg = ["export POST_GLOBAL_PLACE_TCL = /work/forest_recluster.tcl"]
    if ok:
        GP.install_head_post_gpl_reseat(cfg, tmp_path, "s81_head", tn, raw)
        assert cfg[0].endswith("/work/head_post_gpl_reseat.tcl")
    else:
        with pytest.raises(ValueError, match="hard cell growth gate"):
            GP.install_head_post_gpl_reseat(cfg, tmp_path, "s81_head", tn, raw)


def test_adv_gpl_td_reports_out_of_scope_types_as_unflagged():
    t = {"logic_cluster_rects_um": [{"name": "a", "patterns": ["x"], "rect_um": [1, 1, 9, 9]}]}
    plan = {"gpl_td": dict(FLAG, types="^A$"), "partition_types": {"A": t, "B": t}}
    rows = {r["type"]: r for r in AG.plan_check(plan)}
    assert rows["A"]["exposed"].startswith("no") and rows["A"]["gpl_td"]
    assert rows["B"]["exposed"] == "yes" and rows["B"]["gpl_td"] == ""
    plan = {"gpl_td": dict(FLAG), "partition_types": {"A": t, "B": t}}
    assert all(r["exposed"].startswith("no") for r in AG.plan_check(plan))


def test_schema_admits_the_scope_and_nothing_else():
    import schema as S
    for key in ("gpl_td", "street_sizing"):
        props = S.SCHEMA["properties"][key]
        assert props["properties"]["types"] == {"type": "string", "minLength": 1} and props["additionalProperties"] is False


# ---------------------------------------------------------------------------------------------------------- street_sizing
def test_street_plan_cfg_scope_parse():
    assert SR.plan_street_cfg({"street_sizing": {"pg": 1}}) == {"street_pg": 1}            # unscoped: unchanged dict
    assert SR.plan_street_cfg({"street_sizing": {"pg": 1, "types": "^hd_lep0N$"}}) == {"street_pg": 1, "_pg_types": "^hd_lep0N$"}
    assert SR.plan_street_cfg({"street_sizing": {"pg": 0, "types": "^hd_lep0N$"}}) == {}
    for bad in ("", 3, "("):
        for pg in (1, 0):                                                   # validated in every reading
            with pytest.raises(ValueError, match="street_sizing.types"):
                SR.plan_street_cfg({"street_sizing": {"pg": pg, "types": bad}})


def test_street_scope_cfg():
    on = dict(SR.DEFAULTS, street_pg=1)
    assert SR.scope_cfg(on, "anything") is on                                   # unscoped: the same object
    sc = dict(on, _pg_types="^hd_lep0N$")
    assert SR.scope_cfg(sc, "hd_lep0N") is sc
    out = SR.scope_cfg(sc, "hd_spn_end")
    assert out["street_pg"] == 0 and SR.need_um(3349, out) == SR.need_um(3349, dict(SR.DEFAULTS))
    assert SR.need_um(3349, sc) > SR.need_um(3349, out)


def _no_regs(monkeypatch):
    monkeypatch.setattr(SR, "pin_registers", lambda t, cores, cfg: [])
    monkeypatch.setattr(SR, "column_points", lambda t, pr=None: [])
    monkeypatch.setattr(SR, "column_boxes", lambda t, pr=None: [])


def test_type_cfg_applies_the_scope(monkeypatch):
    _no_regs(monkeypatch)
    on = dict(SR.DEFAULTS, street_pg=1, face_rule=0)
    sc = dict(on, _pg_types="^in$")
    assert SR.type_cfg(sc, {}, "in")["street_pg"] == 1
    assert SR.type_cfg(sc, {}, "out")["street_pg"] == 0
    assert SR.type_cfg(on, {}, "out") == dict(on, _cols=[], _pinregs=[], _col_boxes=[])     # unscoped: the pre-change dict


def test_content_only_applies_the_scope(monkeypatch):
    _no_regs(monkeypatch)
    seen = []
    monkeypatch.setattr(SR, "extra_boxes", lambda t: [(0, 0, 1, 1)])
    monkeypatch.setattr(SR, "type_face_windows", lambda t: {})
    monkeypatch.setattr(SR, "face_shadow_rule", lambda W, H, xb, w, cfg: seen.append(cfg["street_pg"]) or [])
    monkeypatch.setattr(SR, "station_alleys", lambda t, cfg, xb=None: seen.append(cfg["street_pg"]) or [])
    sc = dict(SR.DEFAULTS, street_pg=1, face_rule=1, _pg_types="^in$")
    t = {"outline_um": [10, 10]}
    SR.content_only(t, sc, "in")
    SR.content_only(t, sc, "out")
    SR.content_only(t, dict(sc, street_pg=0), "out")
    assert seen == [1, 1, 0, 0, 0, 0]


def test_records_write_the_scope_as_a_public_field():
    cfg = dict(SR.DEFAULTS, street_pg=1, _pg_types="^in$", _planwins={}, _xnames=[])
    out = SR.public_cfg(cfg)
    assert out["street_pg_types"] == "^in$" and not any(k.startswith("_") for k in out)
    plain = SR.public_cfg(dict(SR.DEFAULTS, _planwins={}))
    assert "street_pg_types" not in plain and plain == dict(SR.DEFAULTS)
    src = (HERE / "street_rule.py").read_text()
    assert src.count("cfg=public_cfg(cfg)") == 2                          # check and legalize records


def test_set_street_pg_is_not_narrowed_by_the_plan_scope():
    src = (HERE / "street_rule.py").read_text()
    assert 'if k == "_pg_types" and "street_pg" in sets:' in src


def test_schema_json_carries_the_scope():
    j = json.loads((HERE / "die_plan.schema.json").read_text())
    for key in ("gpl_td", "street_sizing"):
        assert j["properties"][key]["properties"]["types"] == {"type": "string", "minLength": 1}
    jsonschema = pytest.importorskip("jsonschema")
    sub = j["properties"]["gpl_td"]
    jsonschema.validate(dict(FLAG, types="^a$"), sub)
    for bad in ("", 3):
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(dict(FLAG, types=bad), sub)


@pytest.mark.parametrize("bad", ["", 3, "("])
def test_adv_fp_bad_scope_fails_closed_without_raising(monkeypatch, bad):
    monkeypatch.delenv("OT_STREET_PG", raising=False)
    w = F.street_worst(_type(bits=1, gap=100.0))
    t = _type(bits=math.floor(0.97 * w[5] / w[4]), gap=100.0)
    out = F.findings({"partition_types": {"A": t}, "street_sizing": {"pg": 1, "types": bad}})
    assert any(x.startswith("FAIL ADV-FP-STREET street_sizing: street_sizing.types") for x in out)
    assert not any("[PG-adjusted]" in x for x in out)
    with pytest.raises(ValueError, match="street_sizing.types"):
        F.pg_enabled({"street_sizing": {"pg": 1, "types": bad}}, "A")
    out0 = F.findings({"partition_types": {"A": t}, "street_sizing": {"pg": 0, "types": bad}})
    assert any(x.startswith("FAIL ADV-FP-STREET street_sizing:") for x in out0)
    monkeypatch.setenv("OT_STREET_PG", "1")
    with pytest.raises(ValueError, match="street_sizing.types"):
        F.pg_enabled({"street_sizing": {"pg": 1, "types": bad}}, "A")


def test_adv_gpl_td_reports_a_malformed_flag_in_the_row():
    t = {"logic_cluster_rects_um": [{"name": "a", "patterns": ["x"], "rect_um": [1, 1, 9, 9]}]}
    rows = AG.plan_check({"gpl_td": {"nope": 1}, "partition_types": {"A": t}})
    assert rows[0]["exposed"] == "yes" and "invalid" in rows[0]["gpl_td"]


def test_adv_fp_street_scope(monkeypatch):
    monkeypatch.delenv("OT_STREET_PG", raising=False)
    w = F.street_worst(_type(bits=1, gap=100.0))
    t = _type(bits=math.floor(0.97 * w[5] / w[4]), gap=100.0)          # borderline: flips only with PG (test_street_pg)
    pt = {"A": t, "B": t}
    scoped = F.findings({"partition_types": pt, "street_sizing": {"pg": 1, "types": "^A$"}})
    assert any("ADV-FP-STREET A [PG-adjusted]" in x for x in scoped)
    assert not any("ADV-FP-STREET B" in x for x in scoped)
    unscoped = F.findings({"partition_types": pt, "street_sizing": {"pg": 1}})
    assert any("ADV-FP-STREET A [PG-adjusted]" in x for x in unscoped) and any("ADV-FP-STREET B [PG-adjusted]" in x for x in unscoped)
    assert F.pg_enabled({"street_sizing": {"pg": 1, "types": "^A$"}}) is True          # die-wide reading (no name)
    monkeypatch.setenv("OT_STREET_PG", "1")                                             # env still forces every type
    assert F.pg_enabled({"street_sizing": {"pg": 1, "types": "^A$"}}, "B") is True
