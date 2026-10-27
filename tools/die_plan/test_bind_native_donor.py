import gzip
import json
from types import SimpleNamespace

import bind_compose
import native_istations
from test_bind_compose import fixture, Rules


def test_gz_composition_has_identical_real_rtl_and_terminals(tmp_path):
    results = []
    for name in ("compose.json", "compose.json.gz"):
        f, spec = fixture()
        path = tmp_path / name
        payload = json.dumps(spec).encode()
        path.write_bytes(gzip.compress(payload) if name.endswith(".gz") else payload)
        b = SimpleNamespace(F=f, R=Rules(), base=str(tmp_path), extra_lib=[])
        bind_compose.apply(b, name)
        results.append(([open(p).read() for p in b.extra_lib], b.composition_receipt))
    assert results[0] == results[1]


def test_passthrough_skip_is_explicit_and_keeps_other_source_geometry():
    typ = dict(buses=[dict(name="skip", dir="out"), dict(name="live", dir="out")],
               internal_stations=[dict(conn="bus:skip", regs_um=[[1, 2]]),
                                  dict(conn="bus:live", regs_um=[[3, 4]])])
    assert len(native_istations.source_entries(typ)) == 2
    assert native_istations.source_entries(typ, ["skip"]) == [typ["internal_stations"][1]]
    assert len(native_istations.source_entries(typ, ["ski"])) == 2
