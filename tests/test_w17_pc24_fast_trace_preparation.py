import sys,subprocess
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import prepare_w17_existing_port_trace as prep
from w17_pc24_projection import projection,core_debug

def test_exact_original_source_inverse_and_only_existing_exports():
    original=subprocess.check_output(['git','show',prep.SOURCE+':'+prep.ORIGINAL],cwd=ROOT,text=True)
    copy=(ROOT/prep.COPY).read_text()
    assert prep.inverse(copy)==original and prep.transform(original)==copy
    assert 'sim_obs_packet' not in copy and 'owned_reads=UNAVAILABLE' in copy
    # Removing the trace restores identical watchdog, clocks, memory and payload handling.
    assert prep.inverse(copy).count('cyc - last_move > WD')==1

def test_exact_conditional_numbers_are_not_guaranteed_completion():
    p=projection(92600)
    assert p['conditional_PC_only_watchdog']['estimated_remaining_seconds']==[6272.64,6336.32]
    assert p['conditional_cold_refill']['estimated_remaining_seconds']==[14102.72,14574.72]
    assert p['guaranteed_completion_cycle'] is None and p['guaranteed_wall_bound'] is None
    assert p['reads_per_rank']==2176 and p['causal_service']=='BOUND_MISSING'

@pytest.mark.parametrize('value',[True,-1,1.5,'92600'])
def test_bad_cycle_envelopes(value):
    with pytest.raises(ValueError):projection(value)

def test_all_debug_units_states_idles_waited_bitmapping():
    for st in range(16):
        for unit in range(8):
            for idle in range(32):
                for waited in (0,1):
                    state=(st<<24)|(unit<<21)|(idle<<16)|(waited<<14)|(0xffffffff<<28)
                    assert core_debug(state)==dict(core_st=st,decoded_unit=unit,idles=idle,waited=waited)
