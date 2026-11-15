"""KW-FIX-35-RD 11-08 (COORD 09:4x RESTAGE-DEPS): a gen / restage host must hold every input the die's kit_rtl and the
item name -- checked on that host, through symlinks, bind.f and the kit_rtl script's own paths"""
import subprocess
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave as K

SH = "/srv/opentallas-scratch3/claude/kw35/t45ov/kit_rtl_s81_kw35_t45.sh"
LAND = "/srv/opentallas-scratch3/claude/cwb/src_28fc7/h2/landed_sidecar_h2.json"
KVOV = "/srv/opentallas-scratch3/claude/die-s81-70/kvov/bind"


class FakeAP:
    HUB_NAME = "intel2"
    def sh(self, argv, timeout=0):
        return 0, "", ""
    def log(self, m):
        pass


def cfg():
    return {"dies": {"s81": {"gen_host": "epyc5", "gen_hosts": ["intel1", "epyc5", "epyc6"], "event": "e",
                             "src": "/s/src", "plan": "/p/plan/plan.json",
                             "work_root": "/srv/opentallas-scratch3/claude/kw26/runs",
                             "kit_rtl": {"mode": "script", "script": SH, "asbuilt": "/srv/x/asb.json",
                                         "note": "see /srv/old/never/probed.json"},
                             "gen_args": ["--hold-ff-margin", "0", "--clock-landing", LAND],
                             "item_env": {"leaf__t1": {"OT_GRT_ALLOW_CONGESTION": "1", "OT_CTX": "/srv/ctx/t1.json"},
                                          "leaf__t2": {"OT_MACRO_MOVES": "u_a:1.0:2.0"}},
                             "type_args": {"serdes__t4": ["--native-cell-cap", "517000", "--ov=/srv/ov/s4.json"]}}}}


def fake(table):
    """table[h] = extra probe lines (M / D) after whole src/plan counts; a host not in table is unreachable"""
    def run(h, cmd):
        if h not in table:
            raise OSError("unreachable")
        return 0, "T /s/src 4000\nT /p/plan 10\n" + "".join(x + "\n" for x in table[h])
    return run


def test_inputs_collected_notes_skipped():
    c = cfg()
    assert K.deep_inputs(c, "s81") == [SH, "/srv/x/asb.json", LAND]
    assert K.item_inputs(c, "s81") == {"leaf__t1": ["/srv/ctx/t1.json"], "serdes__t4": ["/srv/ov/s4.json"]}


def test_script_named_symlink_tree_broken_drops_host():
    """the 11-08 case: the wrapper names die-s81-70/kvov/bind, whose links point at a bind absent on epyc6"""
    c = cfg()
    bad = K.src_incomplete(FakeAP(), c, run=fake({"intel1": [], "epyc5": [],
                                                  "epyc6": [f"D {SH} {KVOV}/bind_report.json"]}))
    assert set(bad) == {"epyc6"} and "bind_report.json missing" in bad["epyc6"]["s81"]
    c["_src_incomplete"] = bad
    assert K.gen_hosts(c, "s81") == ["intel1", "epyc5"]
    c["_otrun_status"] = {h: {"admit": 500, "load": 1, "cores": 128} for h in ("intel1", "epyc5")}
    c["_otrun_status"]["epyc6"] = {"admit": 9000, "load": 0, "cores": 128}       # best by far, but lacks inputs
    assert K.pick_gen_host(c, "s81") != "epyc6"


def test_gen_args_path_missing_drops_host():
    c = cfg()
    bad = K.src_incomplete(FakeAP(), c, run=fake({"intel1": [], "epyc5": [], "epyc6": [f"M {LAND}"]}))
    assert bad == {"epyc6": {"s81": f"{LAND} missing"}}


def test_item_path_only_drops_host_for_that_item():
    c = cfg()
    bad = K.src_incomplete(FakeAP(), c, run=fake({"intel1": [], "epyc5": ["M /srv/ctx/t1.json"], "epyc6": []}))
    assert bad == {}
    assert c["_item_incomplete"] == {"epyc5": {"s81": {"leaf__t1": "/srv/ctx/t1.json missing"}}}
    assert "epyc5" not in K.gen_hosts(c, "s81", "leaf__t1")
    assert "epyc5" in K.gen_hosts(c, "s81", "leaf__t2") and "epyc5" in K.gen_hosts(c, "s81")
    # no status: the configured gen_host, unless it lacks the item's inputs
    assert K.pick_gen_host(c, "s81", item="leaf__t2") == "epyc5"
    assert K.pick_gen_host(c, "s81", item="leaf__t1") in ("intel1", "epyc6")
    # a bound restage never returns to a host without the item's inputs
    sp = {"item": "leaf__t1", "gen_host": "intel1"}
    K.bind_restage(c, "s81", {"restage_host": "epyc5"}, sp)
    assert sp["gen_host"] == "intel1"
    sp = {"item": "leaf__t2", "gen_host": "intel1"}
    K.bind_restage(c, "s81", {"restage_host": "epyc5"}, sp)
    assert sp["gen_host"] == "epyc5"


def test_item_missing_everywhere_keeps_die_hosts():
    c = cfg()
    c["_item_incomplete"] = {h: {"s81": {"leaf__t1": "x"}} for h in ("intel1", "epyc5", "epyc6")}
    assert K.gen_hosts(c, "s81", "leaf__t1") == K.gen_hosts(c, "s81")


def test_unreachable_unknown():
    c = cfg()
    assert K.src_incomplete(FakeAP(), c, run=fake({"intel1": []})) == {}
    assert c["_item_incomplete"] == {}


def test_probe_shell(tmp_path):
    """the real shell: absent path -> M; a .sh naming an absent /srv lane path -> D <script> <path>; whole -> silent"""
    sh = tmp_path / "w.sh"
    gone = "/srv/opentallas-scratch-kw35rd-test/claude/lane/a/bind"
    sh.write_text(f"export S81_BIND_OUT={gone}\nexport X=\"/srv\"\nexec bash physical/x.sh\n")
    ok = tmp_path / "ok.json"; ok.write_text("{}")
    out = subprocess.run(["bash", "-c", K._deep_probe_cmd([str(sh), str(ok), str(tmp_path / "none.json")])],
                         capture_output=True, text=True, check=True).stdout.split("\n")
    assert f"D {sh} {gone}" in out and f"M {tmp_path / 'none.json'}" in out
    assert not [x for x in out if str(ok) in x]


def test_probe_shell_bind_dir(tmp_path):
    """link scan + bind.f sources below a lane sub-dir, run where the dir lives (here a fake lane via a path rewrite)"""
    cmd = K._deep_probe_cmd(["/srv/opentallas-scratch3/claude/lane/x/bind"])
    lane = tmp_path / "srv/opentallas-scratch3/claude/lane/x/bind"
    lane.mkdir(parents=True)
    (lane / "good.sv").write_text("")
    (lane / "l.sv").symlink_to(tmp_path / "absent.sv")
    (lane / "bind.f").write_text(f"{lane}/good.sv\n{tmp_path}/gone.sv\n")
    cmd = cmd.replace("/srv/*/claude/*/*/*", f"{tmp_path}/srv/*/claude/*/*/*").replace(
        "ckd /srv/", f"ckd {tmp_path}/srv/")
    out = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True, check=True).stdout.split("\n")
    assert f"D {lane} {lane}/l.sv" in out and f"D {lane} {tmp_path}/gone.sv" in out
