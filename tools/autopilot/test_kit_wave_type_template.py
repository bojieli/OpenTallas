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


class FakeAP:
    DRY = False

    def __init__(self, ap_dir):
        self.AP_DIR = str(ap_dir)
        self.lines = []

    def log(self, s):
        self.lines.append(s)


def _credit_world(tmp_path, job_status="SIGNED-UNVERSIONED", q_status="SIGNED"):
    rep, mem = "kv3_hg_v1__pv00000001", "kv3_hg_v1__pv00000002"
    c = cfg(kit_rtl={"mode": "bind", "bind_out": "/b/out"})
    d = c["dies"]["qwen_kvsys"]
    st = {"plans": {f"{d['gen_host']}:{d['plan']}|{d['event']}": {"templates": {mem: rep}, "blocks": {rep: "a" * 64, mem: "b" * 64}}},
          "items": {"k": {"die": "qwen_kvsys", "item": rep, "q_status": q_status, "q_id": "job1", "block_sha": "a" * 64}}}
    (tmp_path / "state.json").write_text(json.dumps({"jobs": {"job1": {"status": job_status, "kit": "h:/k", "signoff": {"tt_wns": -3.0, "ff_wns": 2.0}}}}))
    calls = []

    def rpy(host, code, args, timeout=0):
        calls.append((host, args))
        assert args["judged"]["verdict"] == "SIGNED" and args["bind_rtl"] == "/b/out/rtl" and args["rep"] == rep
        return {"records": [{"schema": "opentallas.col_inherit.v1", "sibling": mem, "representative": rep, "credit": True},
                            {"schema": "opentallas.col_inherit.v1", "sibling": "bad", "representative": rep, "credit": False,
                             "credit_blockers": ["macro LEF sha not equal"]}]}
    return c, st, rpy, calls, rep, mem


def test_credit_step_writes_counter_rows_once(tmp_path):
    c, st, rpy, calls, rep, mem = _credit_world(tmp_path)
    ap, notices = FakeAP(tmp_path), {}
    assert KW.template_credit_step(ap, c, st, notices, str(tmp_path), rpy=rpy) == 1
    rows = [l.split("\t") for l in (tmp_path / KW.INHERIT_MEMBERS).read_text().splitlines()]
    assert len(rows) == 1 and rows[0][:3] == ["qwen_kvsys", mem, rep]
    rec = json.loads(open(rows[0][3]).read())
    assert rec["sibling"] == mem and rec["credit"] is True
    import hashlib
    assert rows[0][4] == hashlib.sha256(open(rows[0][3], "rb").read()).hexdigest()
    assert "1 member(s) credited, 1 refused" in ap.lines[-1] and notices["qwen_kvsys"]
    assert KW.template_credit_step(ap, c, st, notices, str(tmp_path), rpy=rpy) == 0 and len(calls) == 1     # once per (die, rep, block)
    # the counter accepts the row (same reader the hub count uses)
    sys.path.insert(0, str(KW.Path(KW.__file__).resolve().parents[1] / "fleet"))
    import release_tree_plan as RT
    row = RT.inherit_rows(tmp_path / KW.INHERIT_MEMBERS)[0]
    assert RT.inherit_record_ok(row) == (True, "")
    stc = {rep: ["ref"]}
    assert RT.inherit_credit("qwen_kvsys", stc, {mem: "m", rep: "m"}, [row]) == [mem] and "via inherit" in stc[mem][0]


def test_credit_step_waits_for_a_signed_representative(tmp_path):
    for js, qs in (("RUNNING", "SIGNED"), ("SIGNED-UNVERSIONED", "FAIL")):
        c, st, rpy, calls, _rep, _mem = _credit_world(tmp_path, js, qs)
        assert KW.template_credit_step(FakeAP(tmp_path), c, st, {}, str(tmp_path), rpy=rpy) == 0 and calls == []
    c, st, rpy, calls, rep, _mem = _credit_world(tmp_path)
    st["items"]["k"]["block_sha"] = "c" * 64                      # signed on another plan block: not this template
    assert KW.template_credit_step(FakeAP(tmp_path), c, st, {}, str(tmp_path), rpy=rpy) == 0
    c["dies"]["qwen_kvsys"]["type_template"] = False
    st["items"]["k"]["block_sha"] = "a" * 64
    assert KW.template_credit_step(FakeAP(tmp_path), c, st, {}, str(tmp_path), rpy=rpy) == 0


def test_credit_step_probe_error_retries(tmp_path):
    c, st, _rpy, _calls, rep, _mem = _credit_world(tmp_path)
    ap = FakeAP(tmp_path)
    assert KW.template_credit_step(ap, c, st, {}, str(tmp_path), rpy=lambda *a, **k: {"error": "boom"}) == 0
    assert not st.get("template_credit") and "retried next tick" in ap.lines[-1]


def test_credit_probe_runs_records(tmp_path):
    def t(name, img):
        return dict(module=name, outline_um=[10, 10], buses=[], contents=[dict(inst="u0", module="m")], hard=False, type_template=True,
                    hard_cores=[], param_set={"P_u_c0_INSTANCE": '"%s"' % img})
    a, b = "col_h9_r1__t1__cl11111111__pv00000001", "col_h9_r1__t1__cl11111111__pv00000002"
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps(dict(partition_types={a: t(a, "i0"), b: t(b, "i1")}, partitions=[])))
    rtl = tmp_path / "rtl"
    rtl.mkdir()
    for n, i in ((a, "i0"), (b, "i1")):
        (rtl / (n + ".sv")).write_text('module %s (input wire clk);\n rom #(.INSTANCE("%s")) u (.clk(clk));\nendmodule\n' % (n, i))
    args = dict(tt_dir=str(KW.Path(KW.__file__).resolve().parents[1] / "fleet"), plan=str(plan), bind_rtl=str(rtl), src=str(tmp_path), rom_dir=None,
                rep=a, signoff="h:/k", judged=dict(path="h:/k", sha256="j", verdict="SIGNED", reasons=[], drc=0, gates={}, tt_wns_ps=-1, ff_hold_wns_ps=1))
    out = subprocess.run([sys.executable, "-c", KW.PROBE_TT_CREDIT, json.dumps(args)], capture_output=True, text=True, timeout=120).stdout
    p = json.loads(out.split("AP_JSON ", 1)[1])
    assert not p.get("error"), p
    assert [(r["sibling"], r["credit"]) for r in p["records"]] == [(b, True)]


def test_strict_rule_is_passed_only_when_the_die_sets_it_and_open_members_retry(tmp_path):
    c, st, _rpy, _calls, rep, mem = _credit_world(tmp_path)
    seen = []

    def rpy(host, code, args, timeout=0):
        seen.append(args)
        return {"records": [{"schema": "opentallas.col_inherit.v1", "sibling": mem, "representative": rep, "credit": len(seen) > 2,
                             "credit_blockers": ["no via map for x"]}]}
    d = c["dies"]["qwen_kvsys"]
    d.update(type_template_rule="strict", type_template_kits={mem: "/k"}, type_template_weights=["/w"], type_template_rom_dir="/r")
    ap = FakeAP(tmp_path)
    assert KW.template_credit_step(ap, c, st, {}, str(tmp_path), rpy=rpy) == 0
    assert (seen[0]["rule"], seen[0]["kits"], seen[0]["weights"], seen[0]["rom_dir"]) == ("strict", {mem: "/k"}, ["/w"], "/r")
    assert not st.get("template_credit") and not (tmp_path / KW.INHERIT_MEMBERS).exists()
    nlog = len(ap.lines)
    assert KW.template_credit_step(ap, c, st, {}, str(tmp_path), rpy=rpy) == 0 and len(ap.lines) == nlog          # same refusal: quiet retry
    assert KW.template_credit_step(ap, c, st, {}, str(tmp_path), rpy=rpy) == 1 and st["template_credit"]          # now credited, closed
    c2, st2, rpy2, calls2, _r, _m = _credit_world(tmp_path / "b" if (tmp_path / "b").mkdir() is None else tmp_path)
    assert KW.template_credit_step(FakeAP(tmp_path / "b"), c2, st2, {}, str(tmp_path / "b"), rpy=rpy2) == 1
    assert "rule" not in calls2[0][1]
