"""REQ-CHARGE-1122 (COORD 11-23): an explicit --mem far above a script class's past runs is charged its request, not the class p90.
S81-BKSEL-R7 asked 110 GB, was charged 7 GB from small runs of the same script name, and yosys was OOM-killed (rc 137)."""
import importlib.machinery, importlib.util, pathlib, tempfile

P = str(pathlib.Path(__file__).with_name("ot-heavy-reconcile"))
loader = importlib.machinery.SourceFileLoader("ot_heavy_reconcile_reqcharge", P)
R = importlib.util.module_from_spec(importlib.util.spec_from_loader("ot_heavy_reconcile_reqcharge", loader))
loader.exec_module(R)


def hist_file(rows):
    f = tempfile.NamedTemporaryFile("w", suffix=".tsv", delete=False)
    f.write("".join(f"t\tu{i}\t{c}\t{l}\t{p}\t100\t0\n" for i, (c, l, p) in enumerate(rows)))
    f.close()
    return R.peak_history(f.name)


def test_large_request_of_a_small_class_is_charged_its_request():
    h = hist_file([("prepare.sh", 16, 6.5)] * 10)
    assert R.expected_peak("prepare.sh", 110, h) == 110.0           # BKSEL: no comparable run -> the request
    assert R.expected_peak("prepare.sh", 16, h) == 6.5              # the repeated small job keeps its measured charge
    assert R.expected_peak("prepare.sh", 24, h) == 6.5              # 16 >= 0.5 x 24: comparable


def test_comparable_history_still_lowers_a_big_request():
    h = hist_file([("lec.py", 96, 30.0)] * 5 + [("lec.py", 8, 2.0)] * 20)
    assert R.expected_peak("lec.py", 96, h) == 30.0
    assert R.expected_peak("lec.py", 110, h) == 30.0


def test_old_behaviour_switch_and_plain_dicts():
    h = hist_file([("prepare.sh", 16, 6.5)] * 10)
    assert R.comparable_peaks("prepare.sh", 110, h, cmp_frac=0) == [6.5] * 10
    assert R.expected_peak("route", 48, {"route": [10.0] * 9 + [40.0]}) == 40.0     # a plain dict (no launch sizes): unchanged


def test_running_unit_reserve_uses_the_same_rule():
    h = hist_file([("prepare.sh", 16, 6.5)] * 10)
    assert R.peak_reserve([("u", 110.0, "prepare.sh", 4.0)], h, 1.0) == 106.0
