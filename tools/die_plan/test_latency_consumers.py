"""DIE-HBM-92-LCHK: F4 bind-time latency-consumer consistency (latency_consumers.py), F3 regen_constants fail-closed on an
HBM-like bind (leaves bound without #() under type-local names), and the check.py R8 missing-bus-groups case.
    python3 -m pytest tools/die_plan/test_latency_consumers.py
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import latency_consumers as LC  # noqa: E402
import regen_constants as RC  # noqa: E402

RAW = {"die": {"name": "t"}, "partitions": [{"name": p, "type": "t_" + p} for p in ("pc", "pb", "pq", "pr")]}


def mem(port, src, asb, landed, bits=((0, 3),)):
    return dict(sink_port=port, sink_bits=[list(b) for b in bits], source=src, source_bits=[list(b) for b in bits],
                asbuilt_stages=asb, bound_stages=landed, landed_stages=landed, lane="L1")


def bg_of(groups):
    return dict(die="t", landing=[dict(sink=s, sink_part=sp, src_part=fp, members=ms) for s, sp, fp, ms in groups], replica=[])


def tap_die(rq=2, rr=2, lr=2):
    """an SU LG tap (READ_RETURN 10) whose request / response cross to a bank leaf; an SFU tap sampling c_rq with
    local_read on one edge"""
    leaves = {"su0.u_tap": dict(module="ot_hbm_vm_lg_pair_tap", params=dict(READ_RETURN=10, WRITE_RETURN=7)),
              "vmb0": dict(module="ot_vms_bank_static", params={}),
              "sfu0": dict(module="ot_hgi_sfu_lg_pair_tap_leaf", params={}),
              "cal0": dict(module="cal", params={})}
    bg = bg_of([("vmb0", "pb", "pc", [mem("rq0", "su0.u_tap.near_rq", 0, rq)]),
                ("su0.u_tap", "pc", "pb", [mem("near_rr", "vmb0.rr0", 0, rr)]),
                ("sfu0", "pq", "pr", [mem("c_rq", "cal0.x_rq", 0, 2), mem("local_read", "cal0.lr", 0, lr)])])
    return leaves, bg


def test_mismatch_when_the_bind_adds_cycles_and_no_hook():
    leaves, bg = tap_die(rq=5, rr=3)
    r = LC.check(leaves, bg)
    row = next(x for x in r["contracts"] if x["param"] == "READ_RETURN")
    assert (row["verdict"], row["added"], row["needed"]) == ("FIXED_LATENCY_MISMATCH", 8, 18)
    assert any(e.startswith("FIXED_LATENCY_MISMATCH su0.u_tap") and "needs 18" in e for e in r["errors"])


def fixed_age_die(rq, rr):
    leaves = {"h.u_lrly0": dict(module="qfd_dv_s5_lrly", params={}), "m": dict(module="mem", params={})}
    bg = bg_of([("m", "pm", "pl", [mem("d", "h.u_lrly0.va_addr", 0, rq)]), ("h.u_lrly0", "pl", "pm", [mem("va_q", "m.q", 0, rr)])])
    return leaves, bg


def test_advisory_contract_reports_but_is_never_an_error():
    r = LC.check(*fixed_age_die(5, 4))
    row = next(x for x in r["contracts"] if x["param"] == "ML")
    assert (row["verdict"], row["added"]) == ("ADVISORY_MISMATCH", 9)
    assert r["errors"] == []


def test_advisory_contract_silent_at_zero_delta():
    r = LC.check(*fixed_age_die(0, 0))
    assert not [x for x in r["contracts"] if x["param"] == "ML"] and r["errors"] == []


def test_hook_regenerated_param_is_not_an_error():
    leaves, bg = tap_die(rq=5, rr=3)
    pr = dict(file="hook.py", changed=[dict(inst="su0.u_tap", param="READ_RETURN", asbuilt="10", bound=18)])
    r = LC.check(leaves, bg, pr, dict(param_regen={"file": "hook.py"}))
    assert not [e for e in r["errors"] if "READ_RETURN" in e]
    assert next(x for x in r["contracts"] if x["param"] == "READ_RETURN")["verdict"] == "REGEN"


def test_align_contract_and_zero_delta():
    leaves, bg = tap_die(rq=0, rr=0, lr=5)
    r = LC.check(leaves, bg)
    assert [x["verdict"] for x in r["contracts"]] == ["MISALIGNED"]          # READ_RETURN loop adds 0: MATCH
    assert r["errors"][0].startswith("FIXED_LATENCY_MISALIGNED sfu0")


def test_r8_error_only_without_landing_and_hook():
    """a torn bus (two bits of one as-built bus land +2 / +5) on a die that adds stages: ERROR unless the die lands
    crossings (asbuilt.land_align) or carries a param_regen hook (its own r8 gate, advisory here)"""
    leaves = {"a": dict(module="m", params={}), "b": dict(module="m", params={})}
    bg = bg_of([("b", "pb", "pc", [mem("d", "a.q", 0, 2, ((0, 3),)), mem("d", "a.q", 0, 5, ((4, 7),))])])
    r = LC.check(leaves, bg, raw=RAW)
    assert r["r8"]["verdict"] == "ERROR" and any(e.startswith("R8_UNLANDED") for e in r["errors"])
    for ab in (dict(land_align="r8"), dict(param_regen={"file": "h.py"})):
        r = LC.check(leaves, bg, ab=ab, raw=RAW)
        assert not r["errors"] and r["r8"]["verdict"].startswith("ADVISORY") and r["r8"]["errors"] >= 1


def test_declared_contracts_rtl_attribute_and_hook():
    leaves = {"x": dict(module="my_ctl", params=dict(RT=3), attrs={"ot_fixed_latency": "req_o>rsp_i:RT"}),
              "y": dict(module="my_peer", params={})}
    bg = bg_of([("y", "pb", "pc", [mem("req", "x.req_o", 0, 2)]), ("x", "pc", "pb", [mem("rsp_i", "y.rsp", 0, 2)])])
    r = LC.check(leaves, bg)
    assert any("x (my_ctl) RT" in e and "needs 7" in e for e in r["errors"]), r["errors"]
    assert LC.parse_attr("a,b>c:P;align:u,v") == [dict(param="P", req=["a", "b"], resp=["c"], src="rtl attribute"),
                                                  dict(align=["u", "v"], src="rtl attribute")]
    leaves["x"]["attrs"] = {}
    hook = dict(changed=[], latency_contracts=[dict(module="my_ctl", param="RT", req=["req_o"], resp=["rsp_i"])])
    r = LC.check(leaves, bg, hook, dict(param_regen={"file": "h.py"}))
    assert any("x (my_ctl) RT" in e for e in r["errors"])                  # declared by the hook, not regenerated


def test_advisory_census_is_never_an_error(tmp_path):
    src = tmp_path / "m.sv"
    src.write_text("module ot_x #(parameter integer FOO_LAT = 3)(input clk);\n reg [7:0] c; wire hit = c == FOO_LAT;\nendmodule\n")
    leaves = {"x": dict(module="ot_x", params=dict(FOO_LAT=3), src=f"{src}:1.1-3.9"), "y": dict(module="m", params={})}
    bg = bg_of([("x", "pc", "pb", [mem("d", "y.q", 0, 2)])])
    r = LC.check(leaves, bg)
    assert not r["errors"] and r["advisory"] == [dict(module="ot_x", n=1, eg="x", max_added=2, params={"FOO_LAT": ["3"]})]


# ------------------------------------------------------------------------------------------- F3 regen_constants
def _hbm_like_bind(d, vm_rt=None, hook=None):
    """HBM bind_d shape: the RULES client (rootctl VM_RT) and its bank are bound WITHOUT #() under type-local names
    (u_u_ctl / u_u_vmb); the bus groups name them by as-built path (hb_idx__ctl, vmb_SW0); +2 die stages each way."""
    (d / "rtl").mkdir(parents=True)
    pstr = f" #(.VM_RT({vm_rt}))" if vm_rt is not None else ""
    (d / "rtl" / "q_idx.sv").write_text(
        "module q_idx(input clk);\n"
        f"    // as-built hb_idx__ctl\n    ot_hbm_idx_rootctl_static_am{pstr} u_u_ctl (\n        .clk(clk)\n    );\n"
        "endmodule\n")
    (d / "rtl" / "q_vmb.sv").write_text(
        "module q_vmb(input clk);\n    // as-built vmb_SW0\n    ot_vms_bank_static u_u_vmb (\n        .clk(clk)\n    );\nendmodule\n")
    bg = bg_of([("vmb_SW0", "pb", "pc", [mem("rq4", "hb_idx__ctl.vm_rq", 0, 2)]),
                ("hb_idx__ctl", "pc", "pb", [mem("vm_rr", "vmb_SW0.rr4", 0, 2)])])
    (d / "bus_groups.json").write_text(json.dumps(bg))
    if hook:
        (d / "param_regen.json").write_text(json.dumps(hook))
    return d


def test_regen_fail_open_positive_control_then_fail_closed(tmp_path):
    b = _hbm_like_bind(tmp_path / "b")
    sys.path.insert(0, str(RC.REPO / "tools" / "hbm_die_v16"))
    import d4g_bank_latency as BL
    # positive control: the old lookup ("module #(" regex, bound instance names) sees no client -> PENDING, verdict PASS
    assert RC.Bound(b).rtl_insts("|".join(re.escape(m) for m in BL.RULES)) == {}
    # fail closed: the as-built leaf map finds hb_idx__ctl; VM_RT (default 0) must be 0 + 6 + 2 + 2 - 6 = 4
    d = RC.run("hbm", b)
    r = d["constants"]["BANK_CLIENT_RT"]
    assert r["status"] == "MISMATCH" and r["value"]["hb_idx__ctl.VM_RT"]["value"] == 4, r
    assert "PENDING" not in d["verdict"] and d["verdict"].get("MISMATCH") == 1
    assert RC.main(["--die", "hbm", "--bound", str(b)]) == 1


def test_regen_bound_value_or_hook_must_equal_the_law(tmp_path):
    assert RC.run("hbm", _hbm_like_bind(tmp_path / "a", vm_rt=4))["constants"]["BANK_CLIENT_RT"]["status"] == "OK"
    hook = dict(file="h.py", changed=[dict(inst="hb_idx__ctl", param="VM_RT", asbuilt="0", bound=4)])
    d = RC.run("hbm", _hbm_like_bind(tmp_path / "h", hook=hook))
    assert d["constants"]["BANK_CLIENT_RT"]["status"] == "OK" and d["constants"]["BANK_CLIENT_RT"]["value"]["hb_idx__ctl.VM_RT"]["hook"]


def test_regen_no_leaf_map_but_rules_module_is_an_error(tmp_path):
    b = _hbm_like_bind(tmp_path / "n")
    for f in (b / "rtl").glob("*.sv"):
        f.write_text(f.read_text().replace("// as-built", "// built"))
    b2 = RC.Bound(b)
    b2._leaves = None                       # no as-built map at all (neither asbuilt.json nor leaf comments)
    o = RC.Out("hbm", b2)
    RC.hbm_rules(o, RC.REPO, None)
    assert o.c["BANK_CLIENT_RT"]["status"] == "ERROR"


# ------------------------------------------------------------------------------------------- check.py r8
def test_check_r8_missing_bus_groups_is_error_when_the_bind_adds_stages(tmp_path):
    import check
    (tmp_path / "bind").mkdir()
    R = check.Report()
    assert check.check_r8(None, R, tmp_path) == dict(checked=False)
    assert [i["level"] for i in R.items] == ["WARN"]
    (tmp_path / "bind" / "bind_latency.json").write_text(json.dumps(dict(buses=[dict(asbuilt_stages=[0, 0], delta=2)])))
    R = check.Report()
    st = check.check_r8(None, R, tmp_path)
    assert st["adds"] == 1 and R.errors() and "adds stages" in R.errors()[0]["msg"]


def _ring_bg(req, resp, req0=0, resp0=0):
    g = lambda port, src, sink, asb, land: dict(sink=sink, members=[dict(sink_port=port, source=src, bound_stages=land, landed_stages=land, asbuilt_stages=asb)])
    return dict(landing=[g("d", "p.u_c.emb_code_addr", "mem", req0, req), g("emb_code_q", "mem.q", "p.u_c", resp0, resp)])


def test_design_loop_reports_required_not_only_added():
    leaves = {"p.u_c": dict(module="qfd_native59_dv_headprep_obs1", params={})}
    res = LC.check(leaves, _ring_bg(4, 7, 2, 2))
    r = next(r for r in res["contracts"] if r["param"] == "EMB_CODE_RING")
    assert (r["verdict"], r["added"], r["landed_loop"], r["required"]) == ("ADVISORY_MISMATCH", 7, 11, 11) and res["errors"] == []
    # as-built equal to landed: added 0, but the design loop is still exceeded and must not read MATCH
    r0 = next(r for r in LC.check(leaves, _ring_bg(4, 7, 4, 7))["contracts"] if r["param"] == "EMB_CODE_RING")
    assert (r0["added"], r0["required"], r0["verdict"]) == (0, 11, "ADVISORY_MISMATCH")
    # negative control: a loop at the design depth reports required 0 and no row
    assert not [r for r in LC.check(leaves, _ring_bg(0, 0))["contracts"] if r["param"] == "EMB_CODE_RING"]


def test_yosys_leaves_elab_keep_uses_u_die_paths():
    yjs = dict(modules=dict(bind_elab_keep=dict(attributes=dict(top=1), cells=dict(u_die=dict(type="die"), u_v0=dict(type="leaf"))),
                            die=dict(attributes={}, cells=dict(a=dict(type="leaf"))), leaf=dict(attributes={}, cells={})))
    assert set(LC.yosys_leaves(yjs)) == {"a"}


def test_absolute_hook_unchanged_target_is_explicitly_derived(tmp_path):
    """The actual HBM 11+2+2 law stays15; it must not add4 to stale15."""
    from types import SimpleNamespace
    import bind
    hook = tmp_path / "absolute.py"
    hook.write_text("def regen(ctx): return dict(params={'su0.u_tap': {'READ_RETURN': 15}}, record={'law':'11+2+2'})\n")
    b = bind.Binder.__new__(bind.Binder)
    b.ab = dict(param_regen=dict(file=str(hook)))
    b.base, b.errors = str(tmp_path), []
    b.F = SimpleNamespace(cells=[SimpleNamespace(path='su0.u_tap', module='ot_hbm_vm_lg_pair_tap',
        ytype='tap', params={'READ_RETURN': 15})])
    b.param_defaults = {}
    b.regen_params()
    assert not b.errors and b.param_regen['changed'] == []
    assert b.param_regen['derived'] == [dict(inst='su0.u_tap',param='READ_RETURN',asbuilt='15',bound=15)]
    leaves,bg = tap_die()
    leaves['su0.u_tap']['params']['READ_RETURN']=15
    report=LC.check(leaves,bg,b.param_regen,b.ab)
    row=next(x for x in report['contracts'] if x.get('param')=='READ_RETURN')
    assert (row['verdict'],row['bound'],row['needed'],row['asbuilt_plus_added']) == ('REGEN',15,15,19)
    # Omitting the explicit target still fails even though the hook is present.
    missing=LC.check(leaves,bg,dict(changed=[],derived=[]),b.ab)
    assert any('READ_RETURN' in e for e in missing['errors'])


def test_undeclared_hook_target_cannot_supply_derivation(tmp_path):
    from types import SimpleNamespace
    import bind
    hook=tmp_path/'bad.py'
    hook.write_text("def regen(ctx): return dict(params={'su0.u_tap': {'TYPO_RETURN': 15}})\n")
    b=bind.Binder.__new__(bind.Binder)
    b.ab=dict(param_regen=dict(file=str(hook)));b.base=str(tmp_path);b.errors=[]
    b.F=SimpleNamespace(cells=[SimpleNamespace(path='su0.u_tap',module='ot_hbm_vm_lg_pair_tap',ytype='tap',params={'READ_RETURN':15})])
    b.param_defaults={};b.regen_params()
    assert b.errors and b.param_regen['derived']==[]
    leaves,bg=tap_die();report=LC.check(leaves,bg,b.param_regen,b.ab)
    assert any('READ_RETURN' in e for e in report['errors'])
