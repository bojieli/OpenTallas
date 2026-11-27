import hashlib
import pytest

import placement_inputs as inputs


class StageModel:
    def __init__(self, physical="same", after_place="after", image="sha256:" + "9" * 64):
        self.physical = hashlib.sha256(physical.encode()).hexdigest()
        self.after_place = after_place
        self.image = image

    def manifest(self, kit, **kwargs):
        assert not kwargs["with_checkpoint"]
        return {
            "image": {"id": self.image},
            "runner": {"sha256": "normalized-runner"},
            "files": {"config.mk": {"stage": "synth", "sha256": "a" * 64}},
            "fingerprints": {"synth": "1" * 64, "floorplan": "2" * 64,
                             "place": self.physical, "cts": self.after_place},
        }


@pytest.fixture
def kit(tmp_path):
    k = tmp_path / "tile"
    k.mkdir()
    (k / "config.mk").write_text("export RTL = /work/rtl.sv\n")
    (k / "kit_resume.py").write_text("# stock fixture\n")
    (tmp_path / "run_kit.sh").write_text("test \"${OT_ORFS_IMAGE:-orfs}\" = orfs\n")
    return k


def capture(kit, **model):
    return inputs.capture(kit, {"die": "s81", "item": "tile", "top": "top", "flow": "type", "mem_gb": 12},
                          inputs.DEFAULT_IMAGE, model=StageModel(**model))


def test_only_effective_placement_and_immutable_image_must_match(kit):
    previous = capture(kit)
    equivalent = capture(kit, after_place="post-placement-only edit")
    assert inputs.same_placement_inputs(equivalent, previous)
    assert inputs.digest(equivalent) == inputs.digest(previous)
    assert not inputs.same_placement_inputs(capture(kit, physical="new placement hook"), previous)
    assert not inputs.same_placement_inputs(capture(kit, image="sha256:" + "8" * 64), previous)


def test_unknown_input_and_external_file_refuse_reuse(kit):
    assert not inputs.same_placement_inputs(None, capture(kit))
    (kit / "config.mk").write_text("export RTL = /srv/other-lane/rtl.sv\n")
    with pytest.raises(ValueError, match="host path"):
        capture(kit)


def test_symlink_and_unknown_image_fail_closed(kit):
    with pytest.raises(ValueError, match="image identity"):
        capture(kit, image=None)
    (kit / "link.v").symlink_to(kit / "config.mk")
    with pytest.raises(ValueError, match="symbolic link"):
        capture(kit)


def test_worker_image_override_has_to_match_review(kit, monkeypatch):
    monkeypatch.setenv("OT_ORFS_IMAGE", "other-tag")
    with pytest.raises(ValueError, match="reviewed image differ"):
        capture(kit)



def previous_and_candidate(tmp_path, certificate):
    import placement_review as review
    old = tmp_path / "s81_old"
    new = tmp_path / "s81_new"
    spec = {"die": "s81", "item": "tile", "top": "top", "flow": "type", "mem_gb": 12}
    old_kit = old / "gen/tile"
    counter = old_kit / "run/results/asap7/top/base/3_place.odb"
    counter.parent.mkdir(parents=True)
    counter.write_bytes(b"retained ODB")
    (old / "gen/run_kit.sh").write_text("# retained runner\n")
    (old / ".keep").write_text(review.keep_text(old))
    for i, run in enumerate((old, new)):
        inputs.write_json(run / "canary_meta.json",
                          {"spec": spec, "kit": str(run / "gen/tile"), "review_before_route": True,
                           "src_commit": ("0" if i == 0 else "1") * 12, "submitted_at": i})
        inputs.write_json(run / inputs.CERTIFICATE, certificate)
    receipt = review.receipt_path(old)
    receipt.parent.mkdir(parents=True)
    images = {}
    for name in review.IMAGES:
        (receipt.parent / name).write_bytes(name.encode())
        images[name] = review.digest(receipt.parent / name)
    inputs.write_json(receipt, {"kit": str(old_kit), "odb": str(counter), "odb_sha256": review.digest(counter),
                                "runner_sha256": review.digest(old / "gen/run_kit.sh"), "images": images,
                                "src_commit": "0" * 12,
                                "placement_inputs_file_sha256": review.digest(old / inputs.CERTIFICATE)})
    inputs.write_json(new / "lint.json", {"verdict": "PASS"})
    inputs.write_json(new / inputs.PREFLIGHT, {"verdict": "PASS", "kit": str(new / "gen/tile")})
    inputs.prepare_prior(new, spec, review)
    return old, new, counter, review


def test_reuse_joins_exact_cached_inputs_to_validated_previous_checkpoint(kit):
    old, new, _, review = previous_and_candidate(kit.parent, capture(kit))
    proposal = inputs.proposed_reuse(new)
    assert proposal["prior_run"] == old.name
    inputs.write_json(new / inputs.PROPOSAL, proposal)
    assert inputs.accepted_reuse(new) is None
    assert inputs.accept_reuse(new, review) == proposal
    assert inputs.accepted_reuse(new) == proposal
    assert not review.receipt_path(new).exists()
    assert not (new / "harness/route_approval.json").exists()


def test_checkpoint_mutation_and_changed_physical_input_never_install_reuse(kit):
    _, new, counter, review = previous_and_candidate(kit.parent, capture(kit))
    proposal = inputs.proposed_reuse(new)
    inputs.write_json(new / inputs.PROPOSAL, proposal)
    counter.write_bytes(b"modified after staging")
    with pytest.raises(ValueError, match="checkpoint bytes changed"):
        inputs.accept_reuse(new, review)
    assert inputs.accepted_reuse(new) is None
    inputs.write_json(new / inputs.CERTIFICATE, capture(kit, physical="new physical input"))
    assert inputs.proposed_reuse(new) is None



def test_reset_contract_provenance_path_is_normalized_only_with_exact_bytes(tmp_path):
    stock = {"files": {"freeze.json": {}, "reset_contract.json": {"sha256": hashlib.sha256(b"contract").hexdigest()},
                       "reset_contract/receipt.txt": {"sha256": hashlib.sha256(b"receipt").hexdigest()}}}
    kit = tmp_path / "kit"
    kit.mkdir()
    roots = [tmp_path / "source-a", tmp_path / "source-b"]
    for source in roots:
        source.mkdir()
        (source / "reset.json").write_bytes(b"contract")

    def freeze(source):
        inputs.write_json(kit / "freeze.json", {"schema": "opentallas.partition_freeze.v1",
                                                "reset_contract": {"contract": str(source / "reset.json"),
                                                                   "contract_sha256": stock["files"]["reset_contract.json"]["sha256"],
                                                                   "receipt_sha256": stock["files"]["reset_contract/receipt.txt"]["sha256"]}})

    freeze(roots[0])
    old = inputs.freeze_identity(kit, stock, roots[0])
    freeze(roots[1])
    assert inputs.freeze_identity(kit, stock, roots[1]) == old
    with pytest.raises(ValueError, match="outside the pinned source"):
        inputs.freeze_identity(kit, stock, roots[0])
    (roots[1] / "reset.json").write_bytes(b"different contract")
    with pytest.raises(ValueError, match="contract evidence differ"):
        inputs.freeze_identity(kit, stock, roots[1])
