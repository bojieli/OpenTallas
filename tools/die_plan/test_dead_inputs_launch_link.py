"""LAUNCH-LINK-1122: dead-input proofs reached through a symlinked top-level dir (rt launch tree) stay repository-relative."""
import json
import os
from pathlib import Path

import pytest

import dead_inputs as D


def test_repo_rel_lexical():
    assert D._repo_rel("results/x/proof.json")
    assert not D._repo_rel("/abs/proof.json")
    assert not D._repo_rel("results/../../etc/passwd")
    assert not D._repo_rel("")


def test_proof_through_symlinked_results(tmp_path):
    src = tmp_path / "src"
    (src / "results").mkdir(parents=True)
    (src / "results" / "p.json").write_text(json.dumps({"schema": "bad"}))
    launch = tmp_path / "launch"
    launch.mkdir()
    os.symlink(src / "results", launch / "results")
    # the containment check passes; the proof content check then refuses the bad schema (not the path)
    with pytest.raises(ValueError, match="invalid dead-input proof"):
        D.ProvenDead({"dead_input_proofs": ["results/p.json"]}, launch, plan_types={})
    with pytest.raises(ValueError, match="repository-relative"):
        D.ProvenDead({"dead_input_proofs": [str(src / "results" / "p.json")]}, launch, plan_types={})
