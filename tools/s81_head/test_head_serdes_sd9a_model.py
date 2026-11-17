import importlib.util
import json
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("sd9a_model", Path(__file__).with_name("head_serdes_sd9a_model.py"))
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)

# intel2 ~/head-serdes-o-logs/sd9a_bank_census.log (sd9a_guard1 post-CTS, 11-16), BANK_CENSUS lines verbatim
CENSUS = """\
OpenROAD 26Q3-1510-g6cb3f2b704
BANK_CENSUS kreg_all sequential_ff=323 ff_area_um2=94.2305400000005 all_named_cell_area_um2=94.2305400000005 masters=DFFHQNx1_ASAP7_75t_R 320 DFFHQNx2_ASAP7_75t_R 3
BANK_CENSUS kreg_data sequential_ff=320 ff_area_um2=93.3557400000005 all_named_cell_area_um2=93.3557400000005 masters=DFFHQNx1_ASAP7_75t_R 317 DFFHQNx2_ASAP7_75t_R 3
BANK_CENSUS oreg_all sequential_ff=557 ff_area_um2=166.3140600000002 all_named_cell_area_um2=166.3140600000002 masters=DFFHQNx1_ASAP7_75t_R 290 DFFHQNx2_ASAP7_75t_R 267
BANK_CENSUS oreg_data sequential_ff=554 ff_area_um2=165.43926000000025 all_named_cell_area_um2=165.43926000000025 masters=DFFHQNx1_ASAP7_75t_R 287 DFFHQNx2_ASAP7_75t_R 267
"""


def test_receiver_is_880_ff_260_5446_um2():
    r = M.receiver()
    assert (r["ff"], r["um2"]) == (880, 260.5446)
    assert r["banks"] == {"DK": {"ff": 323, "um2": 94.23054}, "DO": {"ff": 557, "um2": 166.31406}}


def test_area_scales_with_receivers_latency_does_not():
    assert M.area(12) == {"receivers": 12, "ff": 10560, "um2": 3126.5352}
    one = M.rx_latency(1)
    assert (one["edges"], one["ps"], one["clock"]) == (2, 1666, "pma_rck")
    assert M.model(receivers=12)["rx_latency"] == one          # no x12 on latency
    assert M.rx_latency(2)["ps"] == 3332                       # two traversals, e.g. a request and its return


def test_ddx_follows_the_decoder_rule():
    assert M.ddx() == 2
    assert M.ddx({"DKREG": 1, "DOREG": 0}) == 1
    assert M.ddx({"DKREG": 0, "DOREG": 0}) == 0
    assert M.rx_latency(1, {"DKREG": 1, "DOREG": 0})["ps"] == 833


def test_measured_census_matches():
    assert M.check_census(CENSUS) == []


def test_census_mismatch_and_missing_rows_are_errors():
    old = CENSUS.replace("oreg_all sequential_ff=557", "oreg_all sequential_ff=554")
    assert any(e.startswith("oreg_all") for e in M.check_census(old))
    cut = "\n".join(l for l in CENSUS.splitlines() if "kreg_data" not in l)
    assert M.check_census(cut) == ["kreg_data: missing from the census"]
    with pytest.raises(ValueError):
        M.parse_census(CENSUS + CENSUS.splitlines()[1] + "\n")


def test_source_is_form_a():
    assert M.check_source() == []
    assert set(M.source_params()) == set(M.LINK_SOURCES)


def test_source_drift_is_an_error(tmp_path):
    for rel in M.LINK_SOURCES:
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text((M.ROOT / rel).read_text().replace(".DOREG(1)", ".DOREG(0)"))
    bad = M.check_source(tmp_path)
    assert len(bad) == 2 and all("DOREG is 0" in e for e in bad)


def test_cli_writes_the_model(tmp_path):
    c = tmp_path / "census.log"
    c.write_text(CENSUS)
    out = tmp_path / "m.json"
    assert M.main(["--census", str(c), "--out", str(out)]) == 0
    m = json.loads(out.read_text())
    assert m["errors"] == [] and m["params"]["DDX"] == 2 and m["tx_clock"]["priced_here"] is False
    c.write_text(CENSUS.replace("sequential_ff=323", "sequential_ff=322"))
    assert M.main(["--census", str(c), "--out", str(out)]) == 1
