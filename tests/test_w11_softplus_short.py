"""W11 short sqrt(softplus) record: pins, exhaustive coverage, depths and the schedule agree (fast)."""

import json
import re

from tools.w11_softplus_short import DEPTHS, NEW, OUT, PARTS, ROOT, SCHEDULE, sources


def _record():
    return json.loads(OUT.read_text())


def test_record_pins_current_sources():
    rec = _record()
    assert rec["status"] == "pass"
    assert rec["sources_sha256"] == sources()


def test_every_32bit_input_matches_the_committed_pipes():
    ex = _record()["exactness"]["exhaustive"]
    assert len(ex) == len(PARTS)
    for unit in ex.values():
        assert unit["every_32bit_input"] and unit["inputs"] == 1 << 32
        assert unit["partitions"] == unit["partitions_expected"]
        assert unit["errors"] == 0 and unit["pass_"]


def test_random_units_cover_every_constant():
    u3 = _record()["exactness"]["random_units"]
    assert u3["pass_"] and len(u3["hstep_by_constant"]) == 13
    for h in u3["hstep_by_constant"].values():
        assert h["checked"] >= 50_000_000
        assert h["errors"] == 0 and h["unjustified_refusals"] == 0
    assert u3["mul_x2_vs_qmul_qmul2"]["errors"] == 0
    assert u3["addpos2_vs_qadd_same_sign"]["errors"] == 0


def test_depths_are_the_rtl_localparams():
    src = (ROOT / NEW).read_text()
    rec = _record()["depth"]
    assert re.search(r"localparam integer DEPTH  = T_SP \+ 16;\s+// 107", src)
    assert re.search(r"localparam integer DEPTH = T_P \+ 1;\s+// 33", src)
    assert re.search(r"localparam integer DEPTH = ND \+ 3;\s+// 16", src)
    assert rec["before"] == sum(b for _, b, _ in SCHEDULE) == 162
    assert rec["after"] == sum(a for _, _, a in SCHEDULE) == 107
    assert rec["saved_cycles"] == 55
    assert [u["depth"] for u in rec["units"]] == [d[1] for d in DEPTHS]


def test_prefix_widths_are_all_proved():
    from tools.w11_softplus_short import INC_WIDTHS, KSADD_WIDTHS
    src = (ROOT / NEW).read_text()
    lit = {"RW+1": 33, "Q_W+2": 28}
    ks = {lit.get(w, None) or int(w) for w in re.findall(r"ot_hdc_ksadd_k #\(\.W\(([^)]+)\)\)", src)}
    inc = {lit.get(w, None) or int(w) for w in re.findall(r"ot_hdc_inc_k #\(\.W\(([^)]+)\)\)", src)}
    assert ks <= set(KSADD_WIDTHS) and inc <= set(INC_WIDTHS)
    proofs = _record()["exactness"]["prefix_adder_proofs"]
    assert all(v == "proved" for v in proofs.values())
    assert len(proofs) == len(KSADD_WIDTHS) + len(INC_WIDTHS)
