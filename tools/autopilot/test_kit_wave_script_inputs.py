"""KW-FIX-44 11-10 (COORD, s81 leaf t42 kit_rtl FileNotFoundError on epyc8): the missing-source probe covers an
item's own item_inputs (kit_rtl script, plan) and the paths named by the files that script names"""
import subprocess
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave as K

SCRIPT = "/srv/opentallas-scratch2/claude/canon/s81/kit_rtl_ctapw.sh"
BIND = "/srv/opentallas-scratch2/claude/die-s81-85/s81p7/bind10_ctap"
ASB = "/srv/opentallas-scratch2/claude/type-safe-4/s81p3/asbuilt_f.json"
ROMQ = "/srv/opentallas-scratch2/claude/type-safe-4/s81p3/romq_rtl/a.hard_params.json"
OLD = "/srv/opentallas-scratch2/claude/wt/kw-fix-4-s81h10"


class FakeAP:
    HUB_NAME = "intel2"
    def sh(self, argv, timeout=0):
        return 0, "", ""
    def log(self, m):
        pass


def cfg():
    return {"dies": {"s81": {"gen_host": "epyc7", "gen_hosts": ["epyc7", "epyc4", "epyc8"], "event": "e",
                             "src": "/s/src", "plan": "/p/plan_of_record/plan.json",
                             "item_inputs": {"leaf__t42": {"kit_rtl": {"script": SCRIPT}, "plan": "/p/plan_c839.json",
                                                           "note": "KW-FIX-43 /srv/opentallas-scratch2/claude/x"}}}}}


def fake(table):
    def run(h, cmd):
        return 0, "T /s/src 4000\nT /p/plan_of_record 158\n" + "".join(ln + "\n" for ln in table.get(h, []))
    return run


def test_item_inputs_probed_without_notes():
    ps = K.item_inputs(cfg(), "s81")["leaf__t42"]
    assert SCRIPT in ps and "/p/plan_c839.json" in ps
    assert not any("/claude/x" in p for p in ps)


def test_item_script_bind_missing_marks_item_host():
    c = cfg()
    bad = K.src_incomplete(FakeAP(), c, run=fake({"epyc8": [f"D {SCRIPT} {BIND}"]}))
    assert bad == {}                                   # the die stays; only the item avoids epyc8
    assert BIND in c["_item_incomplete"]["epyc8"]["s81"]["leaf__t42"]
    assert "epyc7" not in c["_item_incomplete"] and "epyc4" not in c["_item_incomplete"]


def test_second_level_counts_only_where_another_host_has_it():
    c = cfg()
    K.src_incomplete(FakeAP(), c, run=fake({"epyc8": [f"N {SCRIPT} {ROMQ}", f"N {SCRIPT} {OLD}"],
                                            "epyc7": [f"N {SCRIPT} {OLD}"], "epyc4": [f"N {SCRIPT} {OLD}"]}))
    why = c["_item_incomplete"]["epyc8"]["s81"]["leaf__t42"]
    assert ROMQ in why and OLD not in why               # OLD is absent everywhere: old provenance, not an input
    assert "epyc7" not in c["_item_incomplete"]


def test_second_level_needs_a_host_that_probed_the_script():
    c = cfg()
    c["dies"]["qc"] = {"gen_hosts": ["epyc2"], "event": "e", "src": "/s/src", "plan": "/p/plan_of_record/q.json"}
    K.src_incomplete(FakeAP(), c, run=fake({"epyc8": [f"N {SCRIPT} {ROMQ}"], "epyc7": [f"N {SCRIPT} {ROMQ}"],
                                            "epyc4": [f"N {SCRIPT} {ROMQ}"]}))
    assert not c["_item_incomplete"]                    # epyc2 never probed the script: no evidence ROMQ exists


def test_probe_shell_walks_script_inputs(tmp_path):
    pre = str(tmp_path)
    j = lambda p: Path(pre + p)
    for p in (SCRIPT, ASB):
        j(p).parent.mkdir(parents=True, exist_ok=True)
    j(SCRIPT).write_text(f"export S81_ASBUILT={pre}{ASB}\nexport S81_BIND_OUT={pre}{BIND}\nexec bash physical/x.sh\n")
    j(ASB).write_text('{"romq": ["%s"], "old": "%s"}' % (pre + ROMQ, pre + OLD))
    j(ROMQ).parent.mkdir(parents=True, exist_ok=True)
    cmd = K._deep_probe_cmd([SCRIPT]).replace("/srv/opentallas-scratch", pre + "/srv/opentallas-scratch")
    out = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True).stdout.replace(pre, "")
    lines = set(out.split("\n")) - {""}
    assert f"D {SCRIPT} {BIND}" in lines                 # named by the script, absent
    assert f"N {SCRIPT} {ROMQ}" in lines and f"N {SCRIPT} {OLD}" in lines   # named by the script's json input
    j(ROMQ).write_text("{}"); j(BIND).mkdir(parents=True)
    out = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True).stdout.replace(pre, "")
    assert set(out.split("\n")) - {""} == {f"N {SCRIPT} {OLD}"}


def test_asbuilt_base_sources_checked_on_host(tmp_path):
    """KV kv3_pv 11-10: asbuilt base kw32/src_27db6 was a 15-file stub on epyc8 -> bind 'preferred HDL source missing'"""
    pre = str(tmp_path)
    base = "/srv/opentallas-scratch2/claude/kw32/src_27db6"
    asb = "/srv/opentallas-scratch2/claude/kw43-canon/kv/asbuilt_kvc_zb.json"
    Path(pre + asb).parent.mkdir(parents=True)
    Path(pre + base + "/rtl").mkdir(parents=True)
    Path(pre + asb).write_text('{"base": "%s", "files": ["rtl/a.sv"], "prefer": ["rtl/b.sv"], "rtl_roots": ["rtl"], '
                               '"netlist": ["n.v.gz"]}' % (pre + base))
    cmd = K._deep_probe_cmd([asb]).replace("/srv/opentallas-scratch", pre + "/srv/opentallas-scratch")
    run = lambda: set(subprocess.run(["bash", "-c", cmd], capture_output=True, text=True).stdout
                      .replace(pre, "").split("\n")) - {""}
    assert run() == {f"D {asb} {base}/rtl/a.sv", f"D {asb} {base}/rtl/b.sv", f"D {asb} {base}/n.v.gz"}
    for r in ("rtl/a.sv", "rtl/b.sv", "n.v.gz"):
        Path(pre + base + "/" + r).write_text("x")
    assert run() == set()
    c = cfg(); c["dies"]["s81"]["kit_rtl"] = {"mode": "bind", "asbuilt": asb}
    bad = K.src_incomplete(FakeAP(), c, run=fake({"epyc8": [f"D {asb} {base}/rtl/a.sv"]}))
    assert set(bad) == {"epyc8"} and f"{base}/rtl/a.sv missing" in bad["epyc8"]["s81"]
