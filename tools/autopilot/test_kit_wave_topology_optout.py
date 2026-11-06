"""DIE-HEAD-76 11-06: per-die opt-out of the canonical bind-topology preparation (HEAD plan-generated kit RTL)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave as K


def cfg(**d):
    base = {"gen_host": "intel1", "event": "e1", "plan": "/p", "src": "/s"}
    base.update(d)
    return {"dies": {"s81_head": base}}


def test_default_on():
    assert K.spec_for(cfg(), "s81_head", "hd_x", "intel2")["canonical_topology_prepare"] is True


def test_explicit_true_on():
    assert K.spec_for(cfg(canonical_topology_prepare=True), "s81_head", "hd_x", "intel2")["canonical_topology_prepare"] is True


def test_die_opt_out():
    assert K.spec_for(cfg(canonical_topology_prepare=False), "s81_head", "hd_x", "intel2")["canonical_topology_prepare"] is False


def test_only_literal_false_opts_out():
    # a typo or a string never silently disables the preparation
    assert K.spec_for(cfg(canonical_topology_prepare="false"), "s81_head", "hd_x", "intel2")["canonical_topology_prepare"] is True
    assert K.spec_for(cfg(canonical_topology_prepare=None), "s81_head", "hd_x", "intel2")["canonical_topology_prepare"] is True
