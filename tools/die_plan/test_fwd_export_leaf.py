"""KV-SENDER-SKEW 11-24: plan clock.fwd_export.<type> = {"from": "leaf", "match_insertion": true} hangs each forwarded
clock export buffer on its ring's launch-flop leaf at POST_CTS (fwd_export_leaf.tcl); absent key = kits unchanged."""
import copy
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import landing_contract as LC  # noqa: E402
import schema  # noqa: E402


class _P:
    def __init__(self, fwd=None, form=None, pins=None):
        clock = {"landing_contract": {"pins": pins if pins is not None else PINS}}
        if form:
            clock["landing_export_form"] = form
        self.types = {"kv3_pv_v12": {"clock": clock}}
        self.raw = {"clock": {"fwd_export": fwd}} if fwd is not None else {}


PINS = [{"name": "fclk_out_ft0_o", "kind": "clock", "dir": "out", "source_clock_port": "clk_t1"},
        {"name": "fclk_out_o_ctl", "kind": "clock", "dir": "out", "source_clock_port": "clk_t2"},
        {"name": "clk_in_l", "kind": "clock", "dir": "in"}]
LEAF = {"from": "leaf", "match_insertion": True}
TN = "kv3_pv_v12"


def test_absent_or_tap_is_unchanged():
    for P in (_P(), _P({}), _P({TN: {"from": "tap"}}), _P({"kv3_hg*": LEAF})):
        assert LC.export_leaf_rows(P, TN) == []
    # the source-tap export text itself never depends on the key
    assert LC.export_tcl(_P({TN: LEAF}), TN) == LC.export_tcl(_P(), TN)


def test_leaf_rows_all_exports_and_prefix_key():
    want = ["fclk_out_ft0_o clk_t1 cland_fwd_fclk_out_ft0_o 0 ft0_o cland_fstart_out_ft0_o",
            "fclk_out_o_ctl clk_t2 cland_fwd_fclk_out_o_ctl 0 o_ctl cland_fstart_out_o_ctl"]
    assert LC.export_leaf_rows(_P({TN: LEAF}), TN) == want
    assert LC.export_leaf_rows(_P({"kv3_pv*": LEAF, "kv3*": {"from": "tap"}}), TN) == want
    assert LC.export_leaf_rows(_P({TN: {"from": "leaf"}}), TN) == want      # match_insertion defaults to true


def test_leaf_rows_ports_and_vector_bterms():
    rows = LC.export_leaf_rows(_P({TN: dict(LEAF, ports=["fclk_out_o_ctl"])}), TN, frozenset({"fclk_out_o_ctl"}))
    assert rows == ["fclk_out_o_ctl[0] clk_t2 cland_fwd_fclk_out_o_ctl 0 o_ctl cland_fstart_out_o_ctl"]


@pytest.mark.parametrize("fwd,form,msg", [
    ({TN: dict(LEAF, ports=["fclk_out_nope"])}, None, "not forwarded outputs"),
    ({TN: {"from": "leaf", "match_insertion": False}}, None, "match_insertion"),
    ({TN: {"from": "root"}}, None, "fwd_export.from"),
    ({TN: dict(LEAF, pad_ps=-1)}, None, "pad_ps"),
    ({TN: LEAF}, "tie", "fwd_buffer")])
def test_leaf_rows_fail_closed(fwd, form, msg):
    with pytest.raises(ValueError, match=msg):
        LC.export_leaf_rows(_P(fwd, form), TN)


def test_schema_accepts_key_and_rejects_typos():
    ex = json.loads((HERE / "examples" / "tiny_plan.json").read_text())
    ok = copy.deepcopy(ex)
    ok.setdefault("clock", {})["fwd_export"] = {"kv3_pv*": dict(LEAF, ports=["fclk_out_ft0_o"], note="x", pad_ps=180)}
    assert schema.validate(ok) == []
    for bad in ({"from": "leaf", "match_insertion": False}, {"from": "root"}, {"from": "leaf", "insertion": True},
                {"from": "leaf", "pad_ps": -5}):
        p = copy.deepcopy(ex)
        p.setdefault("clock", {})["fwd_export"] = {TN: bad}
        assert schema.validate(p) != []


def test_cts_post_anchors_present():
    """gen_phys hooks the leaf pass before the first balance pass and again after leaf_affinity (asserted anchors)."""
    t = (HERE / "cts_post.tcl").read_text()
    assert t.count("# DIE-CORETAP-1119 (FABLE-CLOSURE lever 1, kit side)") == 1
    assert t.count("leaf_affinity.tcl]] }\n") == 1
    assert "fwd_export_leaf" not in t          # default kits: hook text only in kits with the key


# ODB mock: ring r_o[0..2] launched by f1/f2 (leaf net leafA under clk_t1) and f3 (leafX under clk_t9); export buffer xb
# on the clk_t1 root net at (0, 0).
MOCK = r"""
namespace eval ord {}
proc ord::get_db_block {} {return blk}
proc ord::get_db_tech {} {return tech}
proc mk {name body} {proc $name {m args} $body}
set ::dpl 0
proc detailed_placement {} { incr ::dpl }
array set NET {xb_a root1 f1_clk leafA f2_clk leafA f3_clk leafX}
array set LOC {xb {0 0} f1 {50000 40000} f2 {52000 40000} f3 {90000 90000}}
set ::sig {}
mk tech {return 1000}
mk ca {switch $m {xMin {return 0} yMin {return 0} xMax {return 100000} yMax {return 100000}}}
mk blk {switch $m {
  getBTerms {return {bt_d0 bt_d1 bt_d2 bt_fclk bt_t1 bt_t9}}
  findInst {set n [lindex $args 0]; if {$n eq "cland_fwd_fclk_out_r_o"} {return xb}; if {$n in $::INSTS} {return $n}; return NULL}
  getCoreArea {return ca}}}
foreach {b n io net} {bt_d0 r_o[0] OUTPUT n_d0 bt_d1 r_o[1] OUTPUT n_d1 bt_d2 r_o[2] OUTPUT n_d2 bt_fclk fclk_out_r_o OUTPUT n_f
                      bt_t1 clk_t1 INPUT root1 bt_t9 clk_t9 INPUT root9} {
  mk $b "switch \$m {getIoType {return $io} getName {return {$n}} getNet {return $net}}"
}
# data nets: d0 <- f1, d1 <- obuf <- f2, d2 <- f3
mk n_d0 {switch $m {getITerms {return {f1_q}} getBTerms {return {bt_d0}}}}
mk n_d1 {switch $m {getITerms {return {ob_y}} getBTerms {return {bt_d1}}}}
mk n_d2 {switch $m {getITerms {return {f3_q}} getBTerms {return {bt_d2}}}}
mk n_o1 {switch $m {getITerms {return {f2_q ob_a}} getBTerms {return {}}}}
mk ob {switch $m {getITerms {return {ob_a ob_y}}}}
mk ob_a {switch $m {isOutputSignal {return 0} isInputSignal {return 1} getNet {return n_o1} getMTerm {return mt_A}}}
mk ob_y {switch $m {isOutputSignal {return 1} isInputSignal {return 0} getInst {return ob} getMTerm {return mt_Y}}}
foreach f {f1 f2 f3} {
  mk $f "switch \$m {getITerms {return {${f}_clk ${f}_d ${f}_q}} getLocation {return \$::LOC($f)}}"
  mk ${f}_clk "switch \$m {getMTerm {return mt_CLK} getNet {return \$::NET(${f}_clk)} isOutputSignal {return 0} isInputSignal {return 1}}"
  mk ${f}_d {switch $m {getMTerm {return mt_D} isOutputSignal {return 0} isInputSignal {return 1}}}
  mk ${f}_q "switch \$m {getMTerm {return mt_QN} isOutputSignal {return 1} isInputSignal {return 0} getInst {return $f}}"
}
foreach t {CLK D QN A Y} { mk mt_$t "return $t" }
# clock: clk_t1 -> root1 -> lb1 -> leafA ; clk_t9 -> root9 -> lb9 -> leafX
foreach {lf lb rt bt} {leafA lb1 root1 bt_t1 leafX lb9 root9 bt_t9} {
  mk $lf "switch \$m {getBTerms {return {}} getITerms {return {${lb}_y}} getName {return $lf} setSigType {lappend ::sig $lf}}"
  mk $lb "switch \$m {getITerms {return {${lb}_a ${lb}_y}}}"
  mk ${lb}_a "switch \$m {isOutputSignal {return 0} isInputSignal {return 1} getNet {return $rt}}"
  mk ${lb}_y "switch \$m {isOutputSignal {return 1} isInputSignal {return 0} getInst {return $lb}}"
  mk $rt "switch \$m {getBTerms {return {$bt}} getName {return $rt}}"
}
mk xb {switch $m {
  findITerm {return xb_a} getMaster {return xm} getLocation {return $::LOC(xb)}
  setLocation {set ::LOC(xb) $args} getPlacementStatus {return PLACED} setPlacementStatus {}}}
mk xm {switch $m {getWidth {return 1000} getHeight {return 270}}}
mk xb_a {switch $m {getNet {return $::NET(xb_a)} disconnect {set ::NET(xb_a) NULL} connect {set ::NET(xb_a) [lindex $args 0]}}}
proc ord::get_db {} {return db}
mk db {switch $m {findMaster {return pm}}}
namespace eval odb {}
proc odb::dbInst_create {blk m name} {
  lappend ::INSTS $name; set ::NET(${name}_a) NULL; set ::LOC($name) {0 0}
  mk $name "switch \$m {findITerm {return ${name}_\[string tolower \[lindex \$args 0\]\]} setLocation {set ::LOC($name) \$args} setPlacementStatus {}}"
  mk ${name}_a "switch \$m {getNet {return \$::NET(${name}_a)} disconnect {set ::NET(${name}_a) NULL} connect {set ::NET(${name}_a) \[lindex \$args 0\]}}"
  mk ${name}_y "switch \$m {connect {set ::DRV(${name}) \[lindex \$args 0\]}}"
  return $name
}
proc odb::dbNet_create {blk name} { mk $name {switch $m {setSigType {}}}; return $name }
set ::INSTS {}
"""


def _run(tmp_path, rows, tail="fwd_export_leaf cts\nputs \"NET $::NET(xb_a) LOC $::LOC(xb) DPL $::dpl\"\n"):
    if not shutil.which("tclsh"):
        pytest.skip("no tclsh")
    (tmp_path / "rows.txt").write_text("\n".join(rows) + "\n")
    body = (HERE / "fwd_export_leaf.tcl").read_text().replace("/work/", str(tmp_path) + "/")
    body = body.replace(str(tmp_path) + "/fwd_export_leaf.txt", str(tmp_path / "rows.txt"))
    (tmp_path / "t.tcl").write_text(MOCK + body + tail)
    return subprocess.run(["tclsh", str(tmp_path / "t.tcl")], capture_output=True, text=True)


ROW = "fclk_out_r_o clk_t1 cland_fwd_fclk_out_r_o 0 r_o cland_fstart_out_r_o"


def test_tcl_hangs_buffer_on_majority_source_leaf(tmp_path):
    r = _run(tmp_path, [ROW])
    assert r.returncode == 0, r.stderr
    # f1 + f2 (through the output buffer) on leafA under clk_t1; f3 is on another tap and does not vote
    assert "OT_FWD_LEAF cts fclk_out_r_o <- leafA (src clk_t1): 2 of 3 launch flop(s) on it, 0 on other leaves" in r.stdout
    assert "1 off the tap" in r.stdout
    assert "NET leafA LOC 51000 40000 DPL 1" in r.stdout
    assert not (tmp_path / "FAIL_POSTCTS").exists()


def test_tcl_second_pass_is_idempotent(tmp_path):
    r = _run(tmp_path, [ROW], tail="fwd_export_leaf cts\nfwd_export_leaf after_leaf_affinity\n"
                                    "puts \"NET $::NET(xb_a) DPL $::dpl\"\n")
    assert r.returncode == 0, r.stderr
    assert "OT_FWD_LEAF after_leaf_affinity: 0 export(s) hung on their launch leaf, 1 already there, 0 moved" in r.stdout
    assert "NET leafA DPL 1" in r.stdout


def test_tcl_fails_closed_without_source_tap_flop(tmp_path):
    r = _run(tmp_path, [ROW.replace("clk_t1", "clk_t5", 1)])
    assert r.returncode != 0 and "OT_FWD_LEAF FAIL 1" in r.stderr
    assert "none of 3 launch flop(s) on source tap clk_t5" in (tmp_path / "FAIL_POSTCTS").read_text()


def test_gen_hook_text_inserts_both_passes():
    t = (HERE / "cts_post.tcl").read_text()
    a1, a2 = "# DIE-CORETAP-1119 (FABLE-CLOSURE lever 1, kit side)", "leaf_affinity.tcl]] }\n"
    k = t.replace(a1, LC.FWD_LEAF_HOOK + a1).replace(a2, a2 + LC.FWD_LEAF_AGAIN)
    assert k.index("fwd_export_leaf cts") < k.index("subtree_balance.tcl]]") < k.index("fwd_export_leaf after_leaf_affinity")
    assert k.index("leaf_affinity.tcl]] }") < k.index("fwd_export_leaf after_leaf_affinity") < k.index("landing_export_check.tcl")


def test_leaf_rows_pad_cells():
    r = LC.export_leaf_rows(_P({TN: dict(LEAF, pad_ps=180)}), TN)
    assert r[0].split()[3] == str(-(-180 // int(LC.FWD_PAD_STAGE_PS)))     # ceil(180 / 22) = 9
    assert LC.export_leaf_rows(_P({TN: dict(LEAF, pad_ps=0)}), TN)[0].split()[3] == "0"


def test_tcl_pad_chain_between_leaf_and_export(tmp_path):
    row = ROW.replace(" 0 r_o", " 3 r_o")
    r = _run(tmp_path, [row], tail="fwd_export_leaf cts\nfwd_export_leaf after_leaf_affinity\n"
             "puts \"PAD0 $::NET(cland_fwd_fclk_out_r_o_pad0_a) PAD1 $::NET(cland_fwd_fclk_out_r_o_pad1_a) "
             "XB $::NET(xb_a) DRV2 $::DRV(cland_fwd_fclk_out_r_o_pad2) N [llength $::INSTS] LOC $::LOC(cland_fwd_fclk_out_r_o_pad2)\"\n")
    assert r.returncode == 0, r.stderr
    # leaf -> pad0 -> pad1 -> pad2 -> export buffer; built once (second pass finds pad0 already on the leaf)
    assert ("PAD0 leafA PAD1 cland_fwd_fclk_out_r_o_padnet0 XB cland_fwd_fclk_out_r_o_padnet2 "
            "DRV2 cland_fwd_fclk_out_r_o_padnet2 N 3 LOC 51000 40000") in r.stdout
    assert "after_leaf_affinity: 0 export(s) hung on their launch leaf, 1 already there" in r.stdout


# export net placed along the old route: xb -> r1 -> r2 -> fclk port at (91000, 40000); once xb moves next to its flops
# (51000, 40000) the two repeaters go evenly on the straight line to the port
CHAIN = r"""
mk xb {switch $m {
  findITerm {return xb_a} getITerms {return {xb_a xb_y}} getMaster {return xm} getLocation {return $::LOC(xb)}
  setLocation {set ::LOC(xb) $args} getPlacementStatus {return PLACED} setPlacementStatus {}}}
mk xb_a {switch $m {getNet {return $::NET(xb_a)} disconnect {set ::NET(xb_a) NULL} connect {set ::NET(xb_a) [lindex $args 0]}
  isOutputSignal {return 0} isInputSignal {return 1}}}
mk xb_y {switch $m {isOutputSignal {return 1} isInputSignal {return 0} getNet {return n_x}}}
mk n_x {switch $m {getBTerms {return {}} getITerms {return {xb_y r1_a}}}}
mk n_r {switch $m {getBTerms {return {}} getITerms {return {r1_y r2_a}}}}
mk n_p {switch $m {getBTerms {return {bt_fclk}} getITerms {return {r2_y}}}}
mk bt_fclk {switch $m {getIoType {return OUTPUT} getName {return fclk_out_r_o} getNet {return n_p} getBBox {return pbb}}}
mk pbb {switch $m {xMin {return 91000} xMax {return 91000} yMin {return 40000} yMax {return 40000}}}
foreach {r i o} {r1 n_x n_r r2 n_r n_p} {
  set ::LOC($r) {5000 5000}
  mk $r "switch \$m {getITerms {return {${r}_a ${r}_y}} getMaster {return xm} getPlacementStatus {return PLACED}
    setLocation {set ::LOC($r) \$args} setPlacementStatus {}}"
  mk ${r}_a "switch \$m {isOutputSignal {return 0} isInputSignal {return 1} getInst {return $r} getNet {return $i}}"
  mk ${r}_y "switch \$m {isOutputSignal {return 1} isInputSignal {return 0} getInst {return $r} getNet {return $o}}"
}
"""


def test_tcl_respaces_export_repeaters_on_buffer_to_port_line(tmp_path):
    r = _run(tmp_path, [ROW], tail=CHAIN + "fwd_export_leaf cts\nputs \"XB $::LOC(xb) R1 $::LOC(r1) R2 $::LOC(r2)\"\n")
    assert r.returncode == 0, r.stderr
    assert "1 moved next to their flops (1 repeater chain(s) re-spaced), 0 failed" in r.stdout
    # 51000 + (91000 - 51000) * j / 3
    assert "XB 51000 40000 R1 64333 40000 R2 77667 40000" in r.stdout


def test_tcl_no_respace_when_export_net_forks(tmp_path):
    fork = CHAIN + "mk n_x {switch $m {getBTerms {return {}} getITerms {return {xb_y r1_a r2_a}}}}\n"
    r = _run(tmp_path, [ROW], tail=fork + "fwd_export_leaf cts\nputs \"R1 $::LOC(r1)\"\n")
    assert r.returncode == 0, r.stderr
    assert "(0 repeater chain(s) re-spaced)" in r.stdout and "R1 5000 5000" in r.stdout
