"""FLOW-FLEET-R2 X1: a module whose variants were exported as <module>_<tag>__<rest> is archived (4 attn_tr_x designs sat in pending_archive)."""
import json, pathlib, sys, time
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import archive_gate as AG   # noqa: E402

HEAD = "die\telement\tkind\trecord\tdb\trtx_db\tsize\tsha256\tpack\tmeta\tstatus\tsrc\n"


def gate(tmp_path, rows):
    p = tmp_path / "idx.json"
    p.write_text(json.dumps({"agidock": [], "agidock_listed": time.time(), "agidock_index_tsv": HEAD + "".join(rows)}))
    return AG.Gate(listing=str(p), store=str(tmp_path / "nostore"))


def row(el, status="RTX-FULL-AGI-META"):
    return "s81\t%s\tc\tr\t\t\t1\tx\t\t\t%s\t\n" % (el, status)


def test_variant_element_archives_its_module(tmp_path):
    g = gate(tmp_path, [row("ot_hdc_v41x_attn_tr_x_xoff0__h8_1119")])
    ok, miss = g.check("s81", ["ot_hdc_v41x_attn_tr_x", "ot_hdc_v41x_attn_tr_x#60.48x259.2/8ef509b60c09476d"])
    assert ok and "variant ot_hdc_v41x_attn_tr_x_xoff0__h8_1119" in ok and miss is None


def test_longer_module_name_is_not_a_variant(tmp_path):
    g = gate(tmp_path, [row("ot_s81_cfg7_seq_bfp"), row("ot_s81_su_smc__h259")])
    assert g.check("s81", ["ot_s81_cfg7_seq"])[0] is None and g.check("s81", ["ot_s81_su_sm"])[0] is None


def test_unarchived_variant_status_does_not_count(tmp_path):
    g = gate(tmp_path, [row("m_x__y", status="NO-DB")])
    assert g.check("s81", ["m"])[0] is None


def test_variant_of():
    assert AG.variant_of("m", "m_a__b") and AG.variant_of("m", "m_a1__b_c") and not AG.variant_of("m", "m_a") and not AG.variant_of("m", "mm_a__b")
