"""DIE-HBM-90-PEV 11-07: drop_face_shell_pins.py drops from a core's plan pin table only the input pins the kit face
shell cut as unread top bits (face_shell.json 'dropped', shell port [keep-1:0], core fed {n'd0, bus__fq}), repoints
the module's cores to the new table, keeps every other row byte for byte, and fails closed otherwise."""
import copy
import gzip
import hashlib
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import drop_face_shell_pins as D  # noqa: E402

MOD = "ot_q"
OLD, NEW = "cores/ot_q__10x10.json", "cores/ot_q__10x10__drop.json"
RTL = """module ot_q (
    input wire clk,
    input wire [6:0] st,
    output wire [1:0] y
);
    wire [6:0] st__fq;
    (* keep *) ot_hbm_face_reg #(.W(7)) u_bin_st (.clk(clk), .d(st), .q(st__fq));
    ot_q__fcore u_core (
        .clk(clk),
        .st({1'd0, st__fq}),
        .y(y)
    );
endmodule
"""


def shell(**kw):
    s = dict(schema=D.SCHEMA, module=MOD, dropped=["st[7]"], unread_kept=[], widths=dict(clk=1, st=8, y=2),
             keep=dict(clk=1, st=7, y=2), dirs=dict(clk="input", st="input", y="output"))
    s.update(kw)
    return s


def rows():
    r = [dict(name="clk", layer="M5", x=5.0, y=5.0)]
    r += [dict(name=f"st[{b}]", layer="M5", x=1.0 + b, y=9.9) for b in range(8)]
    r += [dict(name=f"y[{b}]", layer="M4", x=0.1, y=1.0 + b) for b in range(2)]
    return r


def plan():
    hc = lambda i, pf: dict(inst=i, module=MOD, pins_file=pf, outline_um=[10, 10], origin_um=[0, 0])
    return dict(partition_types=dict(t_a=dict(hard_cores=[hc("u_q0", OLD), dict(inst="u_m", module="ot_other", pins_file="cores/o.json")]),
                                     t_b=dict(hard_cores=[hc("u_q1", OLD), hc("u_q2", "cores/ot_q__other.json")])),
                note="base")


def test_check_drops_accepts_shell_cut_top_bit():
    assert D.check_drops(MOD, shell(), RTL, rows()) == ["st[7]"]


@pytest.mark.parametrize("sh,rtl,why", [
    (shell(module="ot_x"), RTL, "is not"),
    (shell(dropped=[]), RTL, "drops no pin"),
    (shell(dropped=["st[3]"]), RTL, "not a cut top bit"),
    (shell(dropped=["y[1]"], keep=dict(clk=1, st=7, y=1)), RTL, "is not an input"),
    (shell(dropped=["st[9]"]), RTL, "not in the old plan table"),
    (shell(), RTL.replace("[6:0] st,", "[7:0] st,"), "does not declare"),
    (shell(), RTL.replace("{1'd0, st__fq}", "{st_x, st__fq}"), "does not feed"),
])
def test_check_drops_fails_closed(sh, rtl, why):
    with pytest.raises(SystemExit, match=why):
        D.check_drops(MOD, sh, rtl, rows())


def test_apply_repoints_only_old_table_cores_and_keeps_rows():
    raw, new, inst = D.apply(plan(), MOD, OLD, NEW, ["st[7]"], rows())
    assert inst == ["t_a.u_q0", "t_b.u_q1"]
    hcs = {h["inst"]: h["pins_file"] for t in raw["partition_types"].values() for h in t["hard_cores"]}
    assert hcs == {"u_q0": NEW, "u_m": "cores/o.json", "u_q1": NEW, "u_q2": "cores/ot_q__other.json"}
    assert new == [r for r in rows() if r["name"] != "st[7]"]


def test_apply_kit_pins_must_equal_new_table():
    kit = [dict(bus="clk", bit=None)] + [dict(bus="st", bit=b) for b in range(7)] + [dict(bus="y", bit=b) for b in range(2)]
    D.apply(plan(), MOD, OLD, NEW, ["st[7]"], rows(), kit)
    with pytest.raises(SystemExit, match="kit pins != new table"):
        D.apply(plan(), MOD, OLD, NEW, ["st[7]"], rows(), kit[:-1])


def test_apply_no_core_on_old_table_fails():
    with pytest.raises(SystemExit, match="no hard core"):
        D.apply(plan(), MOD, "cores/none.json", NEW, ["st[7]"], rows())


def test_main_on_plan_dir(tmp_path):
    pd = tmp_path / "d"
    (pd / "cores").mkdir(parents=True)
    raw = json.dumps(plan()).encode()
    with open(pd / "die_plan.json.gz", "wb") as f, gzip.GzipFile(fileobj=f, mode="wb", mtime=0, filename="") as g:
        g.write(raw)
    (pd / OLD).write_text(json.dumps(rows()) + "\n")
    (pd / "SHA256SUMS").write_text(f"{hashlib.sha256(raw).hexdigest()}  die_plan.json\nabc  other.json\n")
    k = tmp_path / "kit"
    k.mkdir()
    (k / "face_shell.json").write_text(json.dumps(shell()))
    (k / "sh.sv").write_text(RTL)
    before = (pd / OLD).read_bytes()
    assert D.main([str(pd), "--module", MOD, "--old-table", OLD, "--new-table", NEW, "--face-shell", str(k / "face_shell.json"),
                   "--shell-rtl", str(k / "sh.sv"), "--event", "ev1", "--by", "T", "--ruling", "R"]) == 0
    assert (pd / OLD).read_bytes() == before
    nt = (pd / NEW).read_text()
    assert nt.endswith("\n") and json.loads(nt) == [r for r in rows() if r["name"] != "st[7]"]
    p = json.loads(gzip.decompress((pd / "die_plan.json.gz").read_bytes()))
    assert [h["pins_file"] for h in p["partition_types"]["t_b"]["hard_cores"]] == [NEW, "cores/ot_q__other.json"]
    ev = json.loads((pd / "ev1_event.json").read_text())
    assert ev["pins_removed"] == ["st[7]"] and ev["table_pins"] == [11, 10] and ev["instances"] == ["t_a.u_q0", "t_b.u_q1"]
    sums = dict(reversed(l.split(None, 1)) for l in (pd / "SHA256SUMS").read_text().splitlines())
    assert sums["other.json"] == "abc"
    assert sums["die_plan.json"] == hashlib.sha256(gzip.decompress((pd / "die_plan.json.gz").read_bytes())).hexdigest()
    assert sums[NEW] == hashlib.sha256((pd / NEW).read_bytes()).hexdigest()
    assert sums["ev1_event.json"] == hashlib.sha256((pd / "ev1_event.json").read_bytes()).hexdigest()
    # second run: the new table exists -> fail closed
    with pytest.raises(SystemExit):
        D.main([str(pd), "--module", MOD, "--old-table", OLD, "--new-table", NEW, "--face-shell", str(k / "face_shell.json"),
                "--shell-rtl", str(k / "sh.sv"), "--event", "ev1", "--by", "T", "--ruling", "R"])
