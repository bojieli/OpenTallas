"""P-RESET-RECEIPT: rebind_nr_serdes accepts a changed hd_serdes partition only with a receipt on the NEW digest whose exercised plan fields cover the whole diff."""
import importlib.util
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
SRC = (HERE / "rebind_nr_serdes.py").read_text()


def load(src=None):
    path = HERE / "rebind_nr_serdes.py"
    if src is None:
        spec = importlib.util.spec_from_file_location("rebind_nr_serdes_t", path)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        return m
    ns = {"__name__": "rebind_mut"}
    exec(compile(src, "mut", "exec"), ns)

    class M:
        pass
    m = M()
    m.__dict__.update(ns)
    return m


OLD = {"lk_EN0": {"type": "hd_serdes", "reset_entry_phase": 4, "id_straps": {"strap_rst_ph": 0}},
       "lk_WN1": {"type": "hd_serdes", "reset_entry_phase": 3, "id_straps": {"strap_rst_ph": 1}},
       "lk_WN2": {"type": "hd_serdes", "reset_entry_phase": 2, "id_straps": {"strap_rst_ph": 0}}}
NEW = {"lk_EN0": {"type": "hd_serdes", "reset_entry_phase": 3, "id_straps": {"strap_rst_ph": 1}},
       "lk_WN1": {"type": "hd_serdes", "reset_entry_phase": 2, "id_straps": {"strap_rst_ph": 0}},
       "lk_WN2": {"type": "hd_serdes", "reset_entry_phase": 2, "id_straps": {"strap_rst_ph": 0}}}
FIELDS = ["partitions[*].reset_entry_phase", "partitions[*].id_straps.strap_rst_ph"]
DIG = "d" * 64


def receipt(digest=DIG, fields=FIELDS):
    r = {"plan_sha256": digest, "proof": {"verdict": "PASS"}}
    if fields is not None:
        r["proof"]["exercised_plan_fields"] = fields
    return r


def test_part_diff_lists_every_changed_leaf():
    m = load()
    assert m.part_diff(OLD, NEW) == ["partitions[lk_EN0].id_straps.strap_rst_ph", "partitions[lk_EN0].reset_entry_phase",
                                     "partitions[lk_WN1].id_straps.strap_rst_ph", "partitions[lk_WN1].reset_entry_phase"]
    assert m.part_diff(OLD, OLD) == []


def test_accept_when_receipt_covers_the_whole_diff():
    m = load()
    assert len(m.check_changed_binding(OLD, NEW, receipt(), DIG)) == 4


def test_unchanged_partitions_need_no_receipt():
    assert load().check_changed_binding(OLD, OLD, None, DIG) == []


@pytest.mark.parametrize("nr,why", [
    (None, "bindings changed"),                                        # no receipt at all: the old behaviour
    (receipt(digest="e" * 64), "not for the new plan digest"),         # receipt of another plan (the old receipt)
    (receipt(fields=None), "no exercised plan fields"),                # producer did not declare what it exercised
    (receipt(fields=["partitions[*].reset_entry_phase"]), "does not cover"),   # partial cover: strap not exercised
])
def test_refusals(nr, why):
    with pytest.raises(ValueError, match=why):
        load().check_changed_binding(OLD, NEW, nr, DIG)


def test_uncovered_extra_key_refused():
    new = {k: dict(v) for k, v in NEW.items()}
    new["lk_WN2"]["pad_extra"] = 1                                      # a changed key the receipt never exercised
    with pytest.raises(ValueError, match="does not cover partitions\\[\\*\\]\\.pad_extra"):
        load().check_changed_binding(OLD, new, receipt(), DIG)


@pytest.mark.parametrize("old,new", [
    ("    if new_receipt is None:\n        raise ValueError(\"HEAD native reset instance bindings changed\")\n", ""),
    ("if new_receipt.get(\"plan_sha256\") != new_digest:", "if False:"),
    ("    if not fields:\n", "    if False:\n"),
    ("    if bad:\n", "    if False:\n"),
    ("bad = sorted({norm_field(p) for p in diff} - covered)", "bad = sorted({norm_field(p) for p in diff} - covered)[:0]"),
    ("    if not diff:\n        return diff\n", "    if not diff:\n        return diff\n    return diff\n"),
])
def test_mutants_killed(old, new):
    assert old in SRC, old
    mut = load(SRC.replace(old, new, 1))
    killed = False
    for nr in (None, receipt(digest="e" * 64), receipt(fields=None), receipt(fields=["partitions[*].reset_entry_phase"])):
        try:
            mut.check_changed_binding(OLD, NEW, nr, DIG)
        except ValueError:
            continue                                   # still a clean fail-closed refusal
        except Exception:
            killed = True                              # crashes instead of refusing: behaviour changed
            continue
        killed = True
    assert killed, "mutant survived every refusal case"
    try:
        r = mut.check_changed_binding(OLD, NEW, receipt(), DIG)
        assert len(r) == 4 or killed
    except Exception:
        killed = True
    assert killed


def test_guard_still_refuses_in_main_without_new_receipt():
    assert "check_changed_binding(serdes_parts(old), serdes_parts(new), nr, head_native_release.digest(new))" in SRC
    assert "parser.add_argument(\"--new-receipt\"" in SRC and "default=None" in SRC
