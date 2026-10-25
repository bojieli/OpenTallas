"""Source hierarchy identity with a consumed mapped parent; never pick a sibling."""
from types import SimpleNamespace
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import bind

MASTER = 'ot_v41_rom_elem_q_qxpq_w10'
TARGET = {'inst': 'u_r0.u_e0', 'pin': 'rst_n'}

def cell(path, module=MASTER, pin='rst_n'):
    return SimpleNamespace(path=path, module=module, ports={pin: [1]})

def test_actual_s81_four_same_master_siblings():
    # bind_names.json + asbuilt.json, frozen VP cohort 2026-10-25 13:09.
    cells = [cell('u_f_0L01.u_r0.u_e' + n) for n in ('0', '2', '3', '4')]
    assert bind.core_reset_hierarchy_candidates(cells, range(4), TARGET, {MASTER}) == [0]
    # Removing the source-parent match reproduces the four-way module ambiguity.
    assert sum(c.module == MASTER for c in cells) == 4

def test_suffix_is_anchored_to_hierarchy_boundary():
    cells = [cell('u_f_0L01.xu_r0.u_e0'), cell('u_f_0L01.u_r0.u_e00'),
             cell('u_f_0L01.u_r0.u_e0.child'), cell('u_f_0L01.u_r1.u_e0')]
    assert bind.core_reset_hierarchy_candidates(cells, range(4), TARGET, {MASTER}) == []

def test_master_pin_and_partition_membership_required():
    cells = [cell('u_f.u_r0.u_e0', module='other'),
             cell('u_f.u_r0.u_e0', pin='arst_n'), cell('u_other.u_r0.u_e0')]
    assert bind.core_reset_hierarchy_candidates(cells, [0, 1], TARGET, {MASTER}) == []

def test_duplicate_source_suffix_remains_ambiguous():
    cells = [cell('u_f.u_r0.u_e0'), cell('u_g.u_r0.u_e0')]
    assert bind.core_reset_hierarchy_candidates(cells, [0, 1], TARGET, {MASTER}) == [0, 1]

def test_unprefixed_exact_source_path():
    assert bind.core_reset_hierarchy_candidates([cell('u_r0.u_e0')], [0], TARGET, {MASTER}) == [0]
