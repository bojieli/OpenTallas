import csv
import importlib.util
from pathlib import Path
import sys

import pytest

spec = importlib.util.spec_from_file_location("clock_overlay", Path(__file__).with_name("clock_overlay.py"))
overlay = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = overlay
spec.loader.exec_module(overlay)


def test_centroid_ledger_cannot_masquerade_as_actual(tmp_path):
    p = tmp_path / "n59_subtap.tsv"
    p.write_text("subtap\tport\tkind\tx_um\ty_um\tsinks\tmean_dist_um\tmax_dist_um\n"
                 "n59_dt0\tck_t1\treg\t10\t20\t400\t20\t61.5\n")
    with pytest.raises(ValueError, match="actual_odb"):
        overlay.read_tap_overlay(p)
    taps = overlay.read_tap_overlay(p, basis="planned")
    assert taps[0].coordinate_basis == "planned"
    assert taps[0].cap_sinks is None
    assert taps[0].name == "n59_dt0" and taps[0].owner_root == "ck_t1"


def test_actual_plot_retains_owner_limits_and_actual_coords(tmp_path):
    p = tmp_path / "actual.tsv"
    header = "inst owner_root x_um y_um load_sinks radius_um cap_sinks radius_limit_um coordinate_basis checkpoint_sha256".split()
    with p.open("w") as out:
        writer = csv.writer(out, delimiter="\t")
        writer.writerow(header)
        writer.writerow(["dt0", "ck_t7", 11.34, 20.25, 401, 61.5, 400, 60, "actual_odb", "abc"])
    taps = overlay.read_tap_overlay(p)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots()
    summary = overlay.draw_tap_overlay(ax, taps, show_radius=True)
    assert tuple(ax.collections[0].get_offsets()[0]) == (11.34, 20.25)
    assert "ck_t7" in ax.texts[0].get_text()
    assert "n=401/400 r=61.5/60um" in ax.texts[0].get_text()
    assert "PLANNED" not in ax.texts[0].get_text()
    assert summary["violations"] == [{"inst": "dt0", "reasons": ["load", "radius"]}]
    assert summary["checkpoints"] == ["abc"]
    plt.close(fig)
    # A missing owner and a nonfinite coordinate both prevent an actual plot.
    for field, value in (("owner_root", ""), ("x_um", "nan")):
        row = dict(zip(header, ["dt0", "ck_t7", "11.34", "20.25", "401", "61.5", "400", "60", "actual_odb", "abc"]))
        row[field] = value
        with p.open("w") as out:
            writer = csv.DictWriter(out, fieldnames=header, delimiter="\t")
            writer.writeheader()
            writer.writerow(row)
        with pytest.raises(ValueError):
            overlay.read_tap_overlay(p)
