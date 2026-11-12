"""HBM-VSN-XTAP-2 11-11 form A' (DIE-HBM-100): per-hop ft hop lockup latch tap (clock.ft_hop_lockup.tap) and latch
site (clock.ft_hop_lockup.latch_frac).  Physical only: the bound RTL / latency are those of the plain latch form (the
keys are not read by bind / gen_rtl), gen_phys writes OT_HOP_LATCH_CAPTURE_TAP / OT_HOP_LATCH_FRAC_MAP, the REAL
face_flops.tcl sites a matched latch at its fraction, and the REAL Tcl regexp picks exactly the planned latches."""
import copy
import json
import re
import shutil
import subprocess
import sys
import types
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import bind  # noqa: E402
import gen_phys  # noqa: E402
import schema as S  # noqa: E402
import test_ft_hop_lockup as T  # noqa: E402

TAP = {"T": {"L22x3": {"1": "capture", "3": "launch"}, "L9mx2": {"2": "capture"}}}
FRAC = {"T": {"L9mx2": {"2": 0.95}}}


def _raw(**kw):
    return {"clock": {"ft_hop_lockup": dict(types=["T"], **kw)}}


def test_helpers_read_maps():
    assert S.ft_hop_latch_tap({}, "T") == {} and S.ft_hop_latch_frac(_raw(), "T") == {}
    assert S.ft_hop_latch_tap(_raw(tap=TAP), "T") == {"L22x3": {1: "capture", 3: "launch"}, "L9mx2": {2: "capture"}}
    assert S.ft_hop_latch_tap(_raw(tap=TAP), "U") == {}
    assert S.ft_hop_latch_frac(_raw(latch_frac=FRAC), "T") == {"L9mx2": {2: 0.95}}


def test_schema_accepts_and_rejects():
    v = S.validator() if hasattr(S, "validator") else None
    sch = S.SCHEMA["properties"]["clock"]["properties"]["ft_hop_lockup"]
    import jsonschema
    jsonschema.validate(_raw(tap=TAP, latch_frac=FRAC)["clock"]["ft_hop_lockup"], sch)
    for bad in (dict(tap={"T": {"s": {"1": "middle"}}}), dict(tap={"T": {"s": {"x": "capture"}}}),
                dict(latch_frac={"T": {"s": {"1": 0}}}), dict(latch_frac={"T": {"s": {"1": 1.2}}})):
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(_raw(**bad)["clock"]["ft_hop_lockup"], sch)
    del v


def test_schema_file_is_current():
    on_disk = json.loads((HERE / "die_plan.schema.json").read_text())
    assert on_disk["properties"]["clock"]["properties"]["ft_hop_lockup"] == \
        json.loads(json.dumps(S.SCHEMA["properties"]["clock"]["properties"]["ft_hop_lockup"]))


def _P(raw, die="hbm_arch"):
    return types.SimpleNamespace(raw=raw, die={"name": die})


def test_gen_phys_cfg(monkeypatch):
    monkeypatch.delenv("OT_HOP_LATCH_CAPTURE_TAP", raising=False)
    P = _P(_raw(tap=TAP, latch_frac=FRAC))
    v = gen_phys._hop_latch_tap_cfg(P, "T")
    assert v == "u_fl_rst_ u_fl_L201x u_fl_L22x3_[^_]+_1[^0-9] u_fl_L9mx2_[^_]+_2[^0-9]", v
    assert gen_phys._hop_latch_frac_cfg(P, "T") == "u_fl_L9mx2_[^_]+_2[^0-9]=0.95"
    # negative controls: no keys = the pre-change line exactly; another type / another die unchanged
    assert gen_phys._hop_latch_tap_cfg(_P(_raw()), "T") == gen_phys._hop_latch_capture_tap(_P(_raw())) == "u_fl_rst_ u_fl_L201x"
    assert gen_phys._hop_latch_tap_cfg(P, "U") == "u_fl_rst_ u_fl_L201x" and gen_phys._hop_latch_frac_cfg(P, "U") is None
    assert gen_phys._hop_latch_tap_cfg(_P(_raw(), die="s81"), "T") is None
    assert gen_phys._hop_latch_tap_cfg(_P(_raw(tap=TAP), die="s81"), "T") == "u_fl_L22x3_[^_]+_1[^0-9] u_fl_L9mx2_[^_]+_2[^0-9]"
    monkeypatch.setenv("OT_HOP_LATCH_CAPTURE_TAP", "off")
    assert gen_phys._hop_latch_tap_cfg(P, "T") == "u_fl_L22x3_[^_]+_1[^0-9] u_fl_L9mx2_[^_]+_2[^0-9]"


def test_launch_overrides_die_default_capture(monkeypatch):
    """11-12: a plan "launch" hop on a slot the die default hangs on capture (u_fl_L201x) leaves that hop on its launch
    tap; the slot's other hops stay on capture (explicit per-hop regexes); other tokens and types unchanged."""
    monkeypatch.delenv("OT_HOP_LATCH_CAPTURE_TAP", raising=False)
    tap = {"T": {"L201x1": {"0": "launch", "2": "launch"}}}
    P = types.SimpleNamespace(raw=_raw(tap=tap), die={"name": "hbm_arch"},
                              types={"T": {"ft_slots": [{"name": "L201x1", "stations": 5}, {"name": "L9x2", "stations": 3}]}})
    v = gen_phys._hop_latch_tap_cfg(P, "T")
    assert v == "u_fl_rst_ u_fl_L201x1_[^_]+_1[^0-9] u_fl_L201x1_[^_]+_3[^0-9]", v
    toks = v.split()
    hit = lambda n: any(re.search(t, n) for t in toks)  # noqa: E731
    assert not hit("u_bound.u_fl_L201x1_o_0/q[0]$_DLATCH_N_") and not hit("u_bound.u_fl_L201x1_o_2/q[5]$_DLATCH_N_")
    assert hit("u_bound.u_fl_L201x1_o_1/q[0]$_DLATCH_N_") and hit("u_bound.u_fl_L201x1_o_3/q[9]$_DLATCH_N_")
    assert hit("u_bound.u_fl_rst_3/q") and not hit("u_bound.u_fl_L9x2_o_0/q[0]$_DLATCH_N_")
    assert gen_phys._hop_latch_tap_cfg(P, "U") == "u_fl_rst_ u_fl_L201x"


NAMES = ["u_bound.u_fl_L22x3_o_1/q[0]$_DLATCH_N_", "u_bound.u_fl_L22x3_o_10/q[3]$_DLATCH_N_",
         "u_bound.u_fl_L22x3_o_11/q[3]$_DLATCH_N_", "u_bound.u_fl_L22mx3_o_1/q[0]$_DLATCH_N_",
         "u_bound.u_fl_L22x3w_o_1/q[0]$_DLATCH_N_", "u_bound.u_fl_L22x3_o_3/q[1]$_DLATCH_N_",
         "u_bound.u_ft_L22x3_o_1/q[0]$_DFF_P_", "u_bound.u_fl_L9mx2_o_2.q[7]$_DLATCH_N_"]


@pytest.mark.skipif(not shutil.which("tclsh"), reason="no tclsh")
def test_tcl_regexp_picks_exactly_the_planned_latches():
    res = gen_phys._hop_latch_tap_cfg(_P(_raw(tap=TAP), die="s81"), "T")
    tcl = "foreach n {%s} { set h 0; foreach re {%s} { if {[regexp -- $re $n]} { set h 1 } }; puts \"$h $n\" }" % (
        " ".join("{%s}" % n for n in NAMES), res)
    out = subprocess.run(["tclsh"], input=tcl, text=True, capture_output=True, check=True).stdout.split("\n")
    hit = [ln.split(" ", 1)[1] for ln in out if ln.startswith("1 ")]
    assert hit == [NAMES[0], NAMES[7]], out
    assert [n for n in NAMES if any(re.search(r, n) for r in res.split())] == hit


@pytest.mark.skipif(not shutil.which("tclsh"), reason="no tclsh")
def test_face_flops_frac_map_sites_only_matched_latch():
    out = T._ff_run(True, "", "set ::env(OT_HOP_LATCH_FRAC_MAP) {u_fl_tx_s1[^0-9]=0.9}\n")
    hl = [ln.split("\t") for ln in out.splitlines() if "\thl\t" in ln]
    assert [(r[0].split("/")[0], float(r[2])) for r in hl] == [("u_fl_tx_s0", 50.0), ("u_fl_tx_s1", 190.0)], hl
    assert "1 at their per-hop fraction (OT_HOP_LATCH_FRAC_MAP, 1 items)" in out, out
    st = {r[1]: float(r[2]) for r in (ln.split("\t") for ln in out.splitlines()) if r[1:2] and r[1].startswith("st")}
    assert st == {"st1": 100.0, "st2": 200.0}, out
    # map wins over the global fraction; unmatched latches keep the global one
    out = T._ff_run(True, "", "set ::env(OT_HOP_LATCH_FRAC) 0.25\nset ::env(OT_HOP_LATCH_FRAC_MAP) {u_fl_tx_s1[^0-9]=0.9}\n")
    hl = [ln.split("\t") for ln in out.splitlines() if "\thl\t" in ln]
    assert [(r[0].split("/")[0], float(r[2])) for r in hl] == [("u_fl_tx_s0", 25.0), ("u_fl_tx_s1", 190.0)], hl


@pytest.mark.skipif(not shutil.which("tclsh"), reason="no tclsh")
def test_face_flops_no_map_unchanged():
    a, b = T._ff_run(True, ""), T._ff_run(True, "", "set ::env(OT_HOP_LATCH_FRAC_MAP) {}\n")
    assert a == b and "per-hop fraction" not in a


@pytest.mark.skipif(not shutil.which("tclsh"), reason="no tclsh")
@pytest.mark.parametrize("bad", ["u_fl_=0", "u_fl_=1.5", "=0.5", "u_fl_=mid", "u_fl_"])
def test_face_flops_frac_map_rejects(bad, tmp_path):
    FF = T.FF
    a = FF.index("set ff_st 0; set ff_st_miss 0")
    body = (T.MOCK + T._procs(FF) + "\nproc ff_put_near {f x y} { return [list $x $y] }\n"
            + "design 1 {}\nset ff_done {}\nset ff_ft [dict create tx [list 3 W E {}]]\n"
            + "set ::env(OT_HOP_LATCH_FRAC_MAP) {%s}\n" % bad + FF[a:FF.index("close $ff_out", a)])
    (tmp_path / "ff.tcl").write_text(body)
    r = subprocess.run(["tclsh", str(tmp_path / "ff.tcl")], text=True, capture_output=True)
    assert r.returncode != 0 and "OT_HOP_LATCH_FRAC_MAP item must be" in r.stderr, (r.stdout, r.stderr)


@pytest.mark.skipif(not T.HAVE_YOSYS, reason="no Yosys")
def test_bind_ignores_the_physical_keys(tmp_path):
    """EQ / latency negative controls: the strict bind of the plain latch form is byte-identical (bound RTL, cells,
    verify report counts) with and without the two physical keys; the live control (xtap_flop) does change it."""
    base = json.loads((T.EX / "die_plan_lanes.json").read_text())
    base["partition_types"]["tf"]["ft_slots"][0]["stations"] = 3
    base["latency"]["lanes"]["a0y"].update(cycles=5, stations=3)
    base.setdefault("clock", {})["ft_hop_lockup"] = {"types": ["tf"]}
    base["asbuilt"]["base"] = str(T.EX)
    slot = base["partition_types"]["tf"]["ft_slots"][0]["name"]
    phys = copy.deepcopy(base)
    phys["clock"]["ft_hop_lockup"].update(tap={"tf": {slot: {"0": "capture", "1": "launch"}}},
                                          latch_frac={"tf": {slot: {"0": 0.95}}})
    live = copy.deepcopy(base)
    live["clock"]["ft_hop_lockup"]["xtap_flop"] = {"tf": {slot: [0]}}
    live["latency"]["lanes"]["a0y"].update(cycles=6, stations=4)
    res = []
    for nm, P in (("base", base), ("phys", phys), ("live", live)):
        pf = tmp_path / f"{nm}.json"
        pf.write_text(json.dumps(P))
        out = tmp_path / nm
        for c in ("elab", "bind", "verify"):
            rc = bind.main([c, str(pf), "--out", str(out), "--mem", "4"])
            if rc:
                break
        v = json.loads((out / "verify_report.json").read_text())
        res.append((rc, v["verdict"], v["counts"], (out / "rtl" / "bt_tf.sv").read_text(),
                    (out / "rtl" / "bind_cells.sv").read_text()))
    assert res[0][:2] == (0, "PASS") and res[0] == res[1], (res[0][:3], res[1][:3])
    assert res[2][:2] == (0, "PASS") and res[2][3] != res[0][3] and "u_fx_" in res[2][3]
