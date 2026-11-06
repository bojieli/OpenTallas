"""FLOW-KITFAIL-1: HBM and KV core-kit generators stage their die's proven reset contract (S81 legacy already did),
so kit LEC uses the proven window instead of silently falling back to 4 edges.  Unlisted modules stay byte-identical."""
import hashlib
import json
import re
import sys
from pathlib import Path

import pytest

TOOL = Path(__file__).resolve().parent
REPO = TOOL.parents[1]
sys.path.insert(0, str(TOOL))
import kit_reset_contract as K  # noqa: E402
import lec  # noqa: E402

GENERATORS = {"hbm": REPO / "physical/die_plan/hbm_arch_cores/gen_core_kit_hbm.py",
              "qwen_kvsys": REPO / "physical/die_plan/qwen_kvsys/cores/harden/gen_core_kit_kv.py",
              "qwen_compute": REPO / "physical/die_plan/qwen_compute/cores/legacy/gen_core_kit_qc.py"}


def contract(tmp_path, modules=("listed_core",)):
    src = tmp_path / "source"
    (src / "reset_contract").mkdir(parents=True)
    receipt = b"HOLD64 PASS assert 66; HOLD8 mutant CAUGHT\n"
    (src / "reset_contract/receipt.txt").write_bytes(receipt)
    data = dict(schema="opentallas.reset_contract.v1", die="hbm", edges=64, modules=list(modules),
                proof=dict(verdict="PASS", assert_edges=66, mutant="CAUGHT", receipt="reset_contract/receipt.txt",
                           receipt_sha256=hashlib.sha256(receipt).hexdigest()))
    (src / "reset_contract.json").write_text(json.dumps(data))
    return src / "reset_contract.json"


def test_listed_module_gets_the_proven_window_in_kit_lec(tmp_path):
    src, kd = contract(tmp_path), tmp_path / "kit"
    kd.mkdir()
    assert lec.reset_contract_gate(kd, "listed_core", environ={})["used"] == 4      # main: unstaged kit = 4 edges
    st = K.stage(kd, "listed_core", src)
    assert st["edges"] == 64 and st["die"] == "hbm"
    rep = lec.reset_contract_gate(kd, "listed_core", environ={})
    assert rep["used"] == 64 and "refused" not in rep


def test_unlisted_or_missing_contract_leaves_kit_untouched(tmp_path):
    src, kd = contract(tmp_path), tmp_path / "kit"
    kd.mkdir()
    assert K.stage(kd, "other_core", src) is None
    assert K.stage(kd, "listed_core", tmp_path / "missing.json") is None
    assert not list(kd.iterdir())


def test_bad_proof_fails_generation_and_stages_nothing(tmp_path):
    src, kd = contract(tmp_path), tmp_path / "kit"
    kd.mkdir()
    (src.parent / "reset_contract/receipt.txt").write_text("edited")
    with pytest.raises(SystemExit, match="sha256 mismatch"):
        K.stage(kd, "listed_core", src)
    assert not list(kd.iterdir())


@pytest.mark.parametrize("die", ["hbm", "qwen_kvsys", "qwen_compute"])
def test_die_contracts_on_main_pass_the_lec_consumer(die, tmp_path):
    src = K.DIE_CONTRACT[die]
    mods = json.loads(src.read_text())["modules"]
    kd = tmp_path / "kit"
    kd.mkdir()
    st = K.stage(kd, mods[0], src)
    assert st and st["edges"] == json.loads(src.read_text())["edges"]


@pytest.mark.parametrize("die", sorted(GENERATORS))
def test_generator_stages_contract_before_kit_hash(die):
    """Fails on main (no generator outside S81 legacy staged the contract): the call must precede kit_hash(kd), so the
    kit hash covers the staged files, and its record must land in freeze.json."""
    txt = GENERATORS[die].read_text()
    m = re.search(r"kit_reset_contract\.stage\(kd, (\w+), kit_reset_contract\.DIE_CONTRACT\[\"" + die + r"\"\](?:, required_source=True)?\)", txt)
    assert m, f"{GENERATORS[die].name} does not stage the {die} reset contract"
    assert txt.index(m.group(0)) < txt.index("kit_hash=kit_hash(kd)")
    assert 'fz["reset_contract"]' in txt


def test_qc_contract_covers_the_su_lane_w_cores_with_64_edges(tmp_path):
    """DIE-QC-58: the su_lane_w l1 pilot LEC failed at the 4-edge default (reset-less delay-line constants reloaded at
    edges 5..7); the QC die contract must list the su_lane_w cut cores and grant 64 edges through the same lec gate."""
    src = K.DIE_CONTRACT["qwen_compute"]
    mods = json.loads(src.read_text())["modules"]
    assert {f"qfd_qc_su_lane_w_l{k}" for k in range(8)} <= set(mods)
    kd = tmp_path / "kit"
    kd.mkdir()
    st = K.stage(kd, "qfd_qc_su_lane_w_l1", src)
    assert st["edges"] == 64 and st["die"] == "qwen_compute"
    assert lec.reset_contract_gate(kd, "qfd_qc_su_lane_w_l1", environ={})["used"] == 64


def test_qc_generator_writes_recipe_lec_hints_before_kit_hash():
    """DIE-QC-58: QC core recipes carry lec_hints like HBM's; written into the kit before kit_hash covers it."""
    txt = GENERATORS["qwen_compute"].read_text()
    w = txt.index('(kd / "lec_hints.json").write_text(json.dumps(rec["lec_hints"]')
    assert w < txt.index("kit_hash=kit_hash(kd)")


def test_type_kit_stages_qc_contract_and_lec_consumes_it(tmp_path):
    """The failed type-kit class must get the same proven reset window as core kits."""
    from types import SimpleNamespace
    import gen_phys
    src = K.DIE_CONTRACT["qwen_compute"]
    contract = json.loads(src.read_text())
    plan = json.loads((REPO / "physical/die_plan/qwen_compute/plan_of_record/plan_qc52.json").read_text())
    tops = {t["module"] for n, t in plan["partition_types"].items() if n.startswith("sle_st_b")}
    assert len(tops) >= 2
    for i, top in enumerate(sorted(tops)):
        kd = tmp_path / str(i)
        kd.mkdir()
        (kd / "io.tcl").write_text("")
        p = SimpleNamespace(name="qwen_compute", types={"sample": dict(outline_um=[10, 10], module=top)})
        fz = gen_phys.write_partition_freeze(p, "sample", kd, [])
        assert top in contract["modules"]
        assert fz["reset_contract"]["edges"] == 64
        assert lec.reset_contract_gate(kd, top, environ={})["used"] == 64
        assert (kd / "reset_contract/receipt.txt").is_file()


def test_type_kit_unlisted_top_keeps_default(tmp_path):
    from types import SimpleNamespace
    import gen_phys
    (tmp_path / "io.tcl").write_text("")
    p = SimpleNamespace(name="qwen_compute", types={"sample": dict(outline_um=[10, 10], module="not_a_qc_top")})
    fz = gen_phys.write_partition_freeze(p, "sample", tmp_path, [])
    assert "reset_contract" not in fz
    assert not (tmp_path / "reset_contract.json").exists()


def test_type_kit_stages_untrusted_lec_hints_in_freeze(tmp_path):
    from types import SimpleNamespace
    import gen_phys
    import hashlib
    hints = [["gold", "ff:replica.q", ["eq", "gold", "ff:original.q", 0]]]
    p = SimpleNamespace(name="no_contract", types={"sample": dict(outline_um=[10, 10], module="top", lec_hints=hints)})
    (tmp_path / "io.tcl").write_text("")
    fz = gen_phys.write_partition_freeze(p, "sample", tmp_path, [])
    out = tmp_path / "lec_hints.json"
    assert json.loads(out.read_text()) == hints
    assert fz["lec_hints"] == dict(file="lec_hints.json", count=1, sha256=hashlib.sha256(out.read_bytes()).hexdigest())
