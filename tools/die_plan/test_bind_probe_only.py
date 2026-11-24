"""PROBE-ONLY-1123: OT_BIND_ONLY_TYPES type selection."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bind  # noqa: E402
import pytest  # noqa: E402

BY = {"svc_a__t1": ["p1"], "svc_a__t1__v1": ["p2"], "slw_b": ["p3"], "cut_x": ["p4"]}
TY = {"svc_a__t1": {}, "svc_a__t1__v1": {"split_of": "svc_a__t1"}, "slw_b": {}, "cut_x": {"split_of": "base_x"}}


def test_unset_is_full_bind(monkeypatch):
    monkeypatch.delenv("OT_BIND_ONLY_TYPES", raising=False)
    assert bind.only_types_select(BY, TY) is None


def test_selects_name_variants_and_split_base(monkeypatch):
    monkeypatch.setenv("OT_BIND_ONLY_TYPES", "svc_a__t1, base_x")
    assert bind.only_types_select(BY, TY) == {"svc_a__t1", "svc_a__t1__v1", "cut_x"}
    monkeypatch.setenv("OT_BIND_ONLY_TYPES", "slw_*")
    assert bind.only_types_select(BY, TY) == {"slw_b"}


def test_unknown_name_refuses(monkeypatch):
    monkeypatch.setenv("OT_BIND_ONLY_TYPES", "slw_b,nope")
    with pytest.raises(bind.BindError):
        bind.only_types_select(BY, TY)


def test_whole_die_gate_findings_filtered_on_probe():
    errs = ["LF_CS_DEPTH ot_leaf__t1: no bound module file in /o/rtl", "LF_CS_DEPTH svc_a__t1: depth 3 != 2"]
    assert bind.probe_only_filter(errs, None) == errs
    assert bind.probe_only_filter(errs, {"emitted": ["svc_a__t1"]}) == errs[1:]


def test_scope_split_out_of_scope_warns_in_scope_fails():
    probe = {"emitted": ["svc_a__t1"]}
    known = ["svc_a__t1", "slw_b"]
    errs = ["LATCH_EXCEPT_MODULE qfd_x_romleaf: matches no bound lockup module (bound lockup modules: [])",
            "LATCH_EXCEPT_MODULE slw_b/m: matches no bound lockup module in this type",
            "LATCH_EXCEPT_MODULE svc_a__t1/m: matches no bound lockup module in this type",
            "EMIT svc_a__t1: gap", "LF_CS_DEPTH slw_b: depth", "R7_TOP top-level problem"]
    mt = {"qfd_x_romleaf": {"slw_b"}}
    keep, warn = bind.probe_scope_split(errs, probe, known, mt)
    assert keep == errs[2:4] + errs[5:]            # in-scope typed errors and typeless errors still fail
    assert [w.split(" ", 1)[1] for w in warn] == [errs[0], errs[1], errs[4]]
    assert all(w.startswith("WARN-OUT-OF-SCOPE ") for w in warn)


def test_scope_split_full_bind_keeps_everything():
    errs = ["LATCH_EXCEPT_MODULE m: x", "EMIT slw_b: gap"]
    assert bind.probe_scope_split(errs, None, ["slw_b"]) == (errs, [])


def test_untyped_latch_key_owned_by_emitted_type_or_unmapped_still_fails():
    probe = {"emitted": ["svc_a__t1"]}
    known = ["svc_a__t1", "slw_b"]
    e_own = "LATCH_EXCEPT_MODULE m_shared: matches no bound lockup module"
    e_emit = "LATCH_EXCEPT_MODULE m_emit: matches no bound lockup module"
    e_unk = "LATCH_EXCEPT_MODULE m_unknown: matches no bound lockup module"
    e_out = "LATCH_EXCEPT_MODULE m_out: matches no bound lockup module"
    mt = {"m_shared": {"slw_b", "svc_a__t1"}, "m_emit": {"svc_a__t1"}, "m_out": {"slw_b"}}
    keep, warn = bind.probe_scope_split([e_own, e_emit, e_unk, e_out], probe, known, mt)
    assert keep == [e_own, e_emit, e_unk]
    assert warn == ["WARN-OUT-OF-SCOPE " + e_out]


# ---- SCOPED-BIND-OOS 11-24 (FABLE-RC-QC e066364e): UNDRIVEN_OPEN and path-named errors on out-of-scope types
def test_undriven_open_on_out_of_scope_type_is_a_warning():
    probe = {"emitted": ["cbx_q10__a"]}
    known = ["cbx_q10__a", "sle_ctl__b", "sle_fw_v1__c"]
    e_out = ("UNDRIVEN_OPEN dvs_E0.u_core.u_rp.w518_cp[88:0] (qfd_dv_s8_rp1, type sle_ctl__b): 89 input bit(s) the as-built "
             "instance leaves unconnected")
    e_in = "UNDRIVEN_OPEN cbx0.u_core.x[3:0] (m, type cbx_q10__a): 4 input bit(s)"
    e_src = "UNDRIVEN_OPEN cbx0.u.y (m, type cbx_q10__a; source leaf of a split / composed type): 1 bit"
    keep, warn = bind.probe_scope_split([e_out, e_in, e_src], probe, known)
    assert keep == [e_in, e_src]
    assert warn == ["WARN-OUT-OF-SCOPE " + e_out]


def test_path_named_error_maps_through_owned_cells():
    probe = {"emitted": ["cbx_q10__a"]}
    known = ["cbx_q10__a", "sle_ctl__b"]
    pt = {"dvs_E0.u_core": {"sle_ctl__b"}, "cbx0": {"cbx_q10__a"}, "shared0": {"sle_ctl__b", "cbx_q10__a"}}
    e_out = "TIED dvs_E0.u_core.u_rp.d[3]: input reads z"
    e_in = "TIED cbx0.d[0]: input reads z"
    e_both = "TIED shared0.d: input reads z"
    e_none = "TIED nowhere.d: input reads z"
    keep, warn = bind.probe_scope_split([e_out, e_in, e_both, e_none], probe, known, None, pt)
    assert keep == [e_in, e_both, e_none]          # in scope, shared with an emitted type, or unmapped: still errors
    assert warn == ["WARN-OUT-OF-SCOPE " + e_out]


def test_error_naming_an_emitted_and_an_out_of_scope_type_still_fails():
    probe = {"emitted": ["cbx_q10__a"]}
    e = "CROSS x.y (type sle_ctl__b -> type cbx_q10__a): width"
    keep, warn = bind.probe_scope_split([e], probe, ["cbx_q10__a", "sle_ctl__b"])
    assert keep == [e] and warn == []
