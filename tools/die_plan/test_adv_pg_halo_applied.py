"""ADV-PG-HALO-APPLIED (FP-CONVERGE-QC 11-25): pass case plus one mutant per class."""
import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adv_pg_halo_applied as H  # noqa: E402
import plan_advisory as PA  # noqa: E402


def core(inst, halo=1.296, **kw):
    c = dict(inst=inst, module="st_a_region", origin_um=[10.0, 10.0], outline_um=[20.0, 20.0])
    if halo is not None:
        c["pg_halo_um"] = halo
    return dict(c, **kw)


def plan(**tkw):
    t = {"outline_um": [100.0, 100.0], "hard_cores": [core("u_r0"), core("u_r1")]}
    t.update(tkw)
    return {"partition_types": {"sle_st_a_v1": t, "sle_st_a_v2": copy.deepcopy(t)}}


def classes(raw):
    return sorted({l.split()[2] for l in H.findings(raw, "p.json") if l.startswith("WARN")})


def test_pass_case():
    assert H.findings(plan(), "p.json") == []
    assert H.findings(plan(core_pg_connect=True), "p.json") == []
    assert H.findings({"partition_types": {"t": {"outline_um": [1, 1], "hard_cores": [core("u", halo=None)]}}}, "p.json") == []


def test_mutants_each_class():
    assert classes(plan(core_pg_connect=False)) == ["HALO-INERT"]
    assert classes(plan(hard_cores=[core("u_r0", 0.1)])) == ["HALO-SMALL"]
    assert classes(plan(hard_cores=[core("u_r0", 20.0)])) == ["HALO-LARGE"]
    assert classes(plan(hard_cores=[core("u_r0", -1.0)])) == ["HALO-BAD"]
    assert classes(plan(hard_cores=[core("u_r0", "1.3")])) == ["HALO-BAD"]
    assert classes(plan(hard_cores=[core("u_r0", 1.296), core("u_r0", 2.0)])) == ["HALO-CLASH"]
    m = plan()
    m["partition_types"]["sle_st_a_v2"]["hard_cores"][1].pop("pg_halo_um")     # a row dropped one halo key
    out = H.findings(m, "p.json")
    assert out[0].startswith("WARN ADV-PG-HALO-APPLIED HALO-DROPPED sle_st_a_v2: 1 core(s): u_r1")
    assert out[-1].startswith("LIST ADV-PG-HALO-APPLIED HALO-DROPPED 1 core(s)")


def test_registered_in_plan_advisory():
    assert ("PG-HALO-APPLIED", "adv_pg_halo_applied") in PA.CHECKS
