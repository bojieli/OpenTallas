"""pin_sites: two different interior pins on one layer site are an error (HEAD hd_spn_end arst_n / rst_o_2, GRT-0080)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import pin_sites as PS


class _P:
    types = {"t": {}, "h": {"hard": True}}


def test_duplicate_site_is_error(monkeypatch):
    monkeypatch.setattr(PS, "type_pins", lambda P, tn: [("arst_n", "M7", 578.4, 1209.632, "tap"),
                                                       ("rst_o_2", "M7", 578.4, 1209.632, "reset_out"),
                                                       ("rst_o_6", "M7", 8.16, 1209.632, "reset_out")])
    errs, warns = PS.check(_P())
    assert len(errs) == 1 and "arst_n (tap)" in errs[0] and "rst_o_2 (reset_out)" in errs[0] and not warns


def test_other_layer_or_site_is_clean(monkeypatch):
    monkeypatch.setattr(PS, "type_pins", lambda P, tn: [("arst_n", "M7", 578.4, 1209.632, "tap"),
                                                       ("rst_o_2", "M5", 578.4, 1209.632, "reset_out"),
                                                       ("start_o_2", "M7", 576.224, 1209.632, "reset_out")])
    assert PS.check(_P()) == ([], [])


def test_uncomputable_type_warns(monkeypatch):
    def boom(P, tn):
        raise ValueError("no sites")
    monkeypatch.setattr(PS, "type_pins", boom)
    errs, warns = PS.check(_P())
    assert errs == [] and len(warns) == 1
