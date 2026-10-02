import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import dsrom_I66_capture_join_ledger as L

def test_existing_added_and_transport_separate():
    m=L.ledger();assert m['core']['net_added_bits']==127140
    assert m['core']['inherited_core_state_bits']==571214
    assert m['transport']['full_state_bits']==476180
    assert m['selector_core_plus_transport_full_state_bits']==1174534
    assert m['selector_delta_plus_transport_state_bits']==603320
    assert m['transport']['repair_changes_state_bits']==0
    assert not m['complete_slot_clock_reset_PG_union']
def test_mutated_core_width_fails():
    s=(L.BASE/'selector_core.sv').read_text()
    s=s.replace('reg [CB-1:0] suffix_up_0','reg [CB:0] suffix_up_0')
    assert s!=(L.BASE/'selector_core.sv').read_text()
    with pytest.raises(ValueError):L.register_count(s)
