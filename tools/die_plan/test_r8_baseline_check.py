import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import r8_baseline_check as C  # noqa: E402

TYPE = ("ERROR R8 type kv3_pc_v1__cl7f648944: instances need different landing pads at {n} sites (e.g. {site}: pads {pads}); "
        "a type is hardened once: split the type or re-plan the cut so the replicas see equal lane depth")
SITE = "slg_*_0.vreq <- vport_*_0.vq0_valid"
BUS = "ERROR R8 bus group L12 (kv3_hg): unequal added delay {d}"
INV = "ERROR R8 order inversion slg_EN_4 (pc_EN_0): afk led kreq as built (3 < 5) but lands after it (9 > 7)"


def t(n=10, site=SITE, pads="[3, 7]"):
    return TYPE.format(n=n, site=site, pads=pads)


def test_type_pad_values_not_compared():
    new, missing, _ = C.compare([t()], [t(pads="[3, 8]")])
    assert not new and not missing


def test_type_site_count_change_fails():
    new, _, _ = C.compare([t()], [t(n=11)])
    assert sum(new.values()) == 1


def test_type_example_site_change_fails():
    new, _, _ = C.compare([t()], [t(site="slg_*_1.afu <- slg_*_3.af__fault")])
    assert sum(new.values()) == 1


def test_bus_delay_figures_not_compared_and_new_group_fails():
    assert not C.compare([BUS.format(d="[1, 2]")], [BUS.format(d="[1, 3]")])[0]
    assert C.compare([], [BUS.format(d="[1, 2]")])[0]


def test_inversion_accepted_once_per_face():
    new, _, acc = C.compare([], [INV])
    assert not new and acc == ["EN"]
    new, _, _ = C.compare([], [INV, INV])
    assert sum(new.values()) == 1


def test_main_reads_logs(tmp_path):
    b, a = tmp_path / "b.log", tmp_path / "a.log"
    b.write_text("R8 FAIL {}\n" + t() + "\n")
    a.write_text("R8 FAIL {}\n" + t(pads="[3, 8]") + "\n")
    assert C.main(["x", str(b), str(a)]) == 0
    a.write_text("R8 FAIL {}\n" + t(n=11) + "\n")
    assert C.main(["x", str(b), str(a)]) == 1
