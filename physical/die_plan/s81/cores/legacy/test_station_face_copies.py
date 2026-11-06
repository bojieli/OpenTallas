"""S81-T51-RECUT: station_face_copies apply/check on a tiny two-child split (shared reset relay output -> face copy)."""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOL = HERE / "station_face_copies.py"
sys.path.insert(0, str(HERE))
import station_face_copies as S  # noqa: E402

D = {"D": "input", "CLK": "input", "QN": "output"}
I = {"A": "input", "Y": "output"}


def _split():
    # W: relay FF u_bound.u_rrl_1 (QN->INV) drives port p00002 AND a local FF D (shared); capture FF on p00001
    w = {"ports": {"clk": {"direction": "input", "bits": [2]}, "p00001": {"direction": "input", "bits": [3]},
                   "p00002": {"direction": "output", "bits": [4]}},
         "cells": {"u_bound.u_rrl_1/q$_DFF_P_": {"type": "DFFHQNx1_ASAP7_75t_R", "port_directions": D,
                                                  "connections": {"D": [3], "CLK": [2], "QN": [5]}},
                   "u_bound.u_rrl_1/_1_": {"type": "INVx1_ASAP7_75t_R", "port_directions": I,
                                            "connections": {"A": [5], "Y": [4]}},
                   "u_bound.u_rrl_2/q$_DFF_P_": {"type": "DFFHQNx1_ASAP7_75t_R", "port_directions": D,
                                                  "connections": {"D": [4], "CLK": [2], "QN": [6]}}},
         "netnames": {}}
    # E: p00002 input -> reset relay driven -> 2 loads (reset input); output p00001 from dedicated FF
    e = {"ports": {"clk": {"direction": "input", "bits": [2]}, "p00002": {"direction": "input", "bits": [3]},
                   "p00001": {"direction": "output", "bits": [4]}},
         "cells": {"u_bound.u_rst_in/q$_DFF_P_": {"type": "DFFHQNx1_ASAP7_75t_R", "port_directions": D,
                                                   "connections": {"D": [3], "CLK": [2], "QN": [5]}},
                   "u_bound.x/q$_DFF_P_": {"type": "DFFHQNx1_ASAP7_75t_R", "port_directions": D,
                                            "connections": {"D": [3], "CLK": [2], "QN": [6]}},
                   "u_bound.y/_1_": {"type": "INVx1_ASAP7_75t_R", "port_directions": I,
                                      "connections": {"A": [5], "Y": [4]}}},
         "netnames": {}}
    top = {"ports": {"clk": {"direction": "input", "bits": [2]}},
           "cells": {"w": {"type": "T_w", "port_directions": {"clk": "input", "p00001": "input", "p00002": "output"},
                           "connections": {"clk": [2], "p00001": [10], "p00002": [11]}},
                     "e": {"type": "T_e", "port_directions": {"clk": "input", "p00002": "input", "p00001": "output"},
                           "connections": {"clk": [2], "p00002": [11], "p00001": [10]}}},
           "netnames": {}}
    return {"modules": {"T": top, "T_w": w, "T_e": e}}


def _pose(p, names):
    body = "".join(f" {{{n}}} {{{1.0 + 2 * i:.6f} 1.080000 1.080000 1.080000 R0 DFFHQNx1_ASAP7_75t_R}} \\\n"
                   for i, n in enumerate(names))
    p.write_text("# Uses FIXED status so ordinary face-flop release cannot collapse the source stages.\n"
                 "set ot_np_ffs [dict create \\\n" + body + "\n]\nset ot_np_blk 1\n"
                 "if {[string match *DFF* [[$ot_np_i getMaster] getName]]} {error \"NATIVE_POSE undeclared source FF $ot_np_nm\"}\n"
                 " $ot_np_i setPlacementStatus FIXED\n")


def test_apply_check(tmp_path):
    sp = tmp_path / "split.json"
    sp.write_text(json.dumps(_split()))
    (tmp_path / "abi.json").write_text(json.dumps({"children": {"w": {}, "e": {}}}))
    _pose(tmp_path / "pw.tcl", ["u_bound.u_rrl_1/q$_DFF_P_", "u_bound.u_rrl_2/q$_DFF_P_"])
    _pose(tmp_path / "pe.tcl", ["u_bound.u_rst_in/q$_DFF_P_", "u_bound.x/q$_DFF_P_"])
    out = tmp_path / "o"
    r = subprocess.run([sys.executable, "-I", str(TOOL), "apply", str(sp), "--top", "T", "--abi", str(tmp_path / "abi.json"),
                        "--pose", f"T_w={tmp_path / 'pw.tcl'}", "--pose", f"T_e={tmp_path / 'pe.tcl'}", "--out", str(out)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr + r.stdout
    rec = json.loads((out / "face_copies.json").read_text())
    assert rec["summary"]["T_w"]["copies"] == 1 and rec["summary"]["T_w"]["ffs_after"] == 3
    assert rec["children"]["T_e"]["reset_ports"] == ["p00002"]
    new = json.loads((out / "split_fc.json").read_text())
    wm = new["modules"]["T_w"]["cells"]
    cp = "u_bound.u_rrl_1/q$_DFF_P___fc_p00002"
    assert wm[cp]["connections"]["D"] == [3] and wm[cp]["attributes"]["ot_face_copy_of"] == "u_bound.u_rrl_1/q$_DFF_P_"
    assert wm["u_bound.u_rrl_2/q$_DFF_P_"]["connections"]["D"] != [4]          # local load moved off the port bit
    pw = (out / "pw.tcl").read_text()
    assert cp in pw and "setPlacementStatus LOCKED" in pw and "FIXED" not in pw.replace("DEF FIXED", "")
    assert "![string match ot_fcap_* $ot_np_nm]" in pw
    # u_rrl_2 drives nothing, and the original u_rrl_1 now only feeds u_rrl_2: both dead -> not posed, recorded
    assert rec["children"]["T_w"]["dead_ffs_not_posed"] == ["u_bound.u_rrl_1/q$_DFF_P_", "u_bound.u_rrl_2/q$_DFF_P_"]
    assert "u_bound.u_rrl_2/" not in pw
    r = subprocess.run([sys.executable, "-I", str(TOOL), "check", str(sp), str(out / "split_fc.json"),
                        str(out / "face_copies.json")], capture_output=True, text=True)
    assert r.returncode == 0 and '"PASS"' in r.stdout, r.stderr
    # a tampered copy (different D) must fail the check
    wm[cp]["connections"]["D"] = [2]
    (out / "bad.json").write_text(json.dumps(new))
    r = subprocess.run([sys.executable, "-I", str(TOOL), "check", str(sp), str(out / "bad.json"),
                        str(out / "face_copies.json")], capture_output=True, text=True)
    assert r.returncode != 0
