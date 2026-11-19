"""TYPE-TEMPLATE in the wave (OWNER 11-19): a member of a template group gets no row of its own; the representative launches."""
import json
import subprocess
import sys

from test_kit_wave import KW, cfg, OWN

NAMES = {"kv3_hg_v1__pv00000001": "a" * 12, "kv3_hg_v1__pv00000002": "b" * 12, "kv3_hg_v1__pv00000003": "c" * 12}


def pick(**over):
    c = cfg(**over)
    c["dies"]["qwen_kvsys"].setdefault("_templates", {"kv3_hg_v1__pv00000002": "kv3_hg_v1__pv00000001"})
    p, s = KW.select(KW.parse_owners(OWN), c, "qwen_kvsys", {}, dict(NAMES))
    return sorted(r["item"] for r in p if r["item"].startswith("kv3_hg_v1")), s


def test_member_gets_no_row_representative_and_others_launch():
    items, skip = pick()
    assert items == ["kv3_hg_v1__pv00000001", "kv3_hg_v1__pv00000003"]
    assert skip[KW.TYPE_TEMPLATE_MEMBER] == ["kv3_hg_v1__pv00000002"]


def test_die_options_off_and_build_anyway():
    assert len(pick(type_template=False)[0]) == 3
    assert len(pick(type_template_build=["kv3_hg_v1__pv00000002"])[0]) == 3
    assert len(pick(_templates={})[0]) == 3


def test_direct_plan_row_member():
    d = {"_templates": {"x": "y"}}
    assert KW.template_member(d, "x") == "y" and KW.template_member(d, "y") is None
    assert KW.template_bind_rtl({"kit_rtl": {"mode": "bind", "bind_out": "/b/out"}}) == "/b/out/rtl"
    assert KW.template_bind_rtl({"kit_rtl": {"mode": "plan"}}) is None


def test_probe_returns_member_map(tmp_path):
    def t(name, img):
        return dict(module=name, outline_um=[10, 10], buses=[], contents=[dict(inst="u0", module="m")], hard=False, type_template=True,
                    param_set={"P_u_c0_INSTANCE": '"%s"' % img})
    a, b = "col_x__t1__pv00000001", "col_x__t1__pv00000002"
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps(dict(partition_types={a: t(a, "i0"), b: t(b, "i1"), "other": dict(outline_um=[1, 1], buses=[])}, partitions=[])))
    rtl = tmp_path / "rtl"
    rtl.mkdir()
    for n, i in ((a, "i0"), (b, "i1")):
        (rtl / (n + ".sv")).write_text('module %s (input wire clk);\n rom #(.INSTANCE("%s")) u (.clk(clk));\nendmodule\n' % (n, i))
    args = {"plan": str(plan), "tt_dir": str(KW.Path(KW.__file__).resolve().parents[1] / "fleet"), "bind_rtl": str(rtl)}
    out = subprocess.run([sys.executable, "-c", KW.PROBE_PLAN, json.dumps(args)], capture_output=True, text=True, timeout=120).stdout
    p = json.loads(out.split("AP_JSON ", 1)[1])
    assert not p.get("error"), p
    assert p["templates"] == {b: a} and p["templates_error"] == "" and p["probe_v"] == KW.PROBE_V
    args["bind_rtl"] = None                                  # no bound RTL: nothing is a member
    out = subprocess.run([sys.executable, "-c", KW.PROBE_PLAN, json.dumps(args)], capture_output=True, text=True, timeout=120).stdout
    assert json.loads(out.split("AP_JSON ", 1)[1])["templates"] == {}
