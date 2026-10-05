"""DSpark multi-token prediction on the V4.1 hardwired decode core (tools/hdc_program_v41.py build_mtp,
tools/rtl_hdc_v41_mtp_campaign.py)."""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_isa_v41 as I  # noqa: E402
import hdc_program_v41 as P  # noqa: E402

RECORD = ROOT / "results/rtl/hdc_v41_mtp_campaign.json"


class _Lay:
    mtp = {"slots": 6}
    m = None


def _machine():
    mach = P.Machine.__new__(P.Machine)
    mach.mtp = True
    mach.stok = [0] * I.NSLOT
    mach.ttok = [0] * I.NSLOT
    mach.tokens = []
    mach.pos = 10
    mach.drafts = []
    return mach


@pytest.mark.parametrize("drafts,targets,a", [
    ([5, 6, 7], [5, 6, 7, 8], 3),        # every draft accepted: the bonus is the 4th target
    ([5, 9, 7], [5, 6, 7, 8], 1),        # the first mismatch ends the prefix
    ([4, 6, 7], [5, 6, 7, 8], 0),        # nothing accepted: the bonus is target 0
])
def test_accept_is_the_longest_matching_prefix(drafts, targets, a):
    mach = _machine()
    mach.stok[0] = 42
    mach.stok[1:1 + len(drafts)] = drafts
    mach.ttok[:len(targets)] = targets
    mach.control({"ctl": I.CTL_ACCEPT, "ctl_slot": len(drafts), "ctl_lane": 0})
    assert mach.accepted == a
    assert mach.emitted == targets[:a + 1]
    assert mach.argmax == targets[a]
    # the Engram history takes the committed positions' tokens only
    assert mach.tokens == [42] + drafts[:a]


def test_isa_package_carries_the_mtp_fields():
    svh = (ROOT / "rtl/hdc/v41/ot_hdc_isa_v41.svh").read_text()
    for name in ("DSLOT", "MX_M", "MX_XPS", "MX_OPS", "CTL", "CTL_SLOT", "CTL_LANE"):
        assert f"O_{name} " in svh
    assert sum(w for _, w in I.FIELDS) <= I.INSTR_BITS
    assert I.POS_RING >= I.NSLOT       # a rejected slot's ring write can never alias a live entry


def test_dyn_ring_values():
    for pos in range(40):
        v = I.dyn_values(7, pos)
        assert v[I.DYN["SLOTW8"]] == (pos % I.POS_RING) * 4
        assert v[I.DYN["SLOTP8"]] == ((pos >> 1) % (I.POS_RING // 2)) * 128
        assert v[I.DYN["TOK32"]] == 7 * 32


def test_batchable_weight_ops():
    assert P.mx_batchable({"unit": I.UNIT_HE})
    assert P.mx_batchable({"unit": I.UNIT_QE, "qe_mode": I.QE_LINQ})
    assert not P.mx_batchable({"unit": I.UNIT_QE, "qe_mode": I.QE_LINQ, "qe_ind": 1})       # routed expert
    assert not P.mx_batchable({"unit": I.UNIT_ME, "me_wsrc": 1})                            # KV-sourced
    assert not P.mx_batchable({"unit": I.UNIT_ME, "me_d_obase": 3})                         # a DYN address
    assert not P.mx_batchable({"unit": I.UNIT_ME, "me_amax": 1})                            # a head argmax
    assert not P.mx_batchable({"unit": I.UNIT_HE, "pred": I.PRED_ODD})


def test_committed_record_passes_and_is_current():
    if not RECORD.exists():
        pytest.skip("no MTP campaign record yet")
    rec = json.loads(RECORD.read_text())
    assert rec["status"] == "pass"
    for part in rec["parts"].values():
        assert part["pass"], part["part"]
        for run in part["runs"]:
            assert run["isa"]["equal_golden_tokens"] and run["isa"]["committed_logits_bit_exact_with_golden"]
            assert run["rtl"]["token_mismatches"] == 0 and run["rtl"]["head_mismatches"] == 0
        for name, digest in part["input_sha256"].items():
            assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
