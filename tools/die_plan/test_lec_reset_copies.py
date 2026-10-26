"""Kept reset-relay copies renamed by ot_rst_copies (QC-LEC-3 10-26, N59 KEEP FAIL 680: 664 were these).

ot_rst_copies adds an alias wire \\ot_rrs__<tag>__c<k> per proven-identical copy bit k of a kept family WN and moves
loads onto it, so synthesis names copy k's flop after the alias.  The flop still exists; kept_registers must count it.
Mutants: a folded copy (one alias missing), a family whose tag matches two gold registers, and an index mismatch
still FAIL."""
import lec
from test_lec import _seq

KEEP = "lec_top/u_dut.u_b.rst_cp\nlec_top/u_dut.u_c.rst_cp\n"


def _keep(tmp_path, text=KEEP):
    k = tmp_path / "gold.keep"
    k.write_text(text)
    return k


def _gold(tmp_path, regs=("u_b.rst_cp[0]", "u_b.rst_cp[1]", "u_b.rst_cp[2]")):
    return _seq(tmp_path, "g", ["d"], list(regs), lambda m, l: {n: l["d"] for n in l if n != "d"})


def _gate(tmp_path, regs):
    return _seq(tmp_path, "t", ["d"], list(regs), lambda m, l: {n: l["d"] for n in l if n != "d"})


def _missing(tmp_path, gold, gate, keep=KEEP):
    g, gm = gold
    t, tm = gate
    L = lec.Lec(g, gm, t, tm)
    declared, missing, const = lec.kept_registers(L, _keep(tmp_path, keep))
    assert not const
    return declared, missing


def test_renamed_reset_copies_are_present(tmp_path):
    rrs = [f"ot_rrs__u_b_rst_cp__c{k}" for k in range(3)]
    declared, missing = _missing(tmp_path, _gold(tmp_path), _gate(tmp_path, rrs))
    assert declared == [f"ff:u_dut.u_b.rst_cp[{k}]" for k in range(3)] and missing == []


def test_old_tool_behaviour_without_rename_fails(tmp_path, monkeypatch):
    monkeypatch.setattr(lec, "kept_reset_copies", lambda L, d: set())
    rrs = [f"ot_rrs__u_b_rst_cp__c{k}" for k in range(3)]
    _, missing = _missing(tmp_path, _gold(tmp_path), _gate(tmp_path, rrs))
    assert len(missing) == 3


def test_folded_copy_still_fails(tmp_path):
    rrs = ["ot_rrs__u_b_rst_cp__c0", "ot_rrs__u_b_rst_cp__c1"]           # copy 2 folded away
    _, missing = _missing(tmp_path, _gold(tmp_path), _gate(tmp_path, rrs))
    assert missing == [f"ff:u_dut.u_b.rst_cp[{k}]" for k in range(3)]


def test_index_mismatch_fails(tmp_path):
    rrs = ["ot_rrs__u_b_rst_cp__c0", "ot_rrs__u_b_rst_cp__c1", "ot_rrs__u_b_rst_cp__c5"]
    _, missing = _missing(tmp_path, _gold(tmp_path), _gate(tmp_path, rrs))
    assert len(missing) == 3


def test_wrong_family_tag_fails(tmp_path):
    rrs = [f"ot_rrs__u_c_rst_cp__c{k}" for k in range(3)]                 # another register's copies
    _, missing = _missing(tmp_path, _gold(tmp_path), _gate(tmp_path, rrs))
    assert len(missing) == 3


def test_ambiguous_tag_claimed_twice_fails(tmp_path):
    # u_b.rst_cp and u_b_rst.cp sanitise to the same tag: neither may take the family
    gold = _gold(tmp_path, ("u_b.rst_cp[0]", "u_b.rst_cp[1]", "u_b_rst.cp[0]", "u_b_rst.cp[1]"))
    rrs = ["ot_rrs__u_b_rst_cp__c0", "ot_rrs__u_b_rst_cp__c1"]
    keep = KEEP + "lec_top/u_dut.u_b_rst.cp\n"
    _, missing = _missing(tmp_path, gold, _gate(tmp_path, rrs), keep)
    assert len(missing) == 4


def test_truncated_tag_uses_last_60_characters(tmp_path):
    long = "u_" + "x" * 70 + ".rst_cp"
    tag = ("u_" + "x" * 70 + "_rst_cp")[-60:]
    gold = _gold(tmp_path, (long + "[0]", long + "[1]"))
    rrs = [f"ot_rrs__{tag}__c{k}" for k in range(2)]
    _, missing = _missing(tmp_path, gold, _gate(tmp_path, rrs), f"lec_top/u_dut.{long}\n")
    assert missing == []
