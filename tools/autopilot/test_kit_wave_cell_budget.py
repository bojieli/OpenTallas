"""R-CAP stops retain PLAN class through preflight and real-cell census."""
import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave as KW

PREFLOOR = ('OT_CELL_BUDGET projected movable cells after place resize 510000 above the R-CAP place budget 400000: '
            'split into 3 parts of <= 250000 movable cells at lane-group boundaries with registered boundary buses, '
            'or harden logic into cores')
PLACE = ('OT_CELL_BUDGET stage=place movable=510000 above the R-CAP place budget 400000 '
         '(tap/endcap 150000 not counted): split into 3 parts of <= 250000 movable cells at lane-group boundaries '
         'with registered boundary buses, or harden logic into cores')
PREFLIGHT = ('q: R-CAP OVER projected movable cells after resize 510000 (synth 400000 + 10000 port buffers + '
             '100000 wire buffers; +-25 %) against 400000; cts 520710, grt 550911')

@pytest.mark.parametrize('stage,text', [('preflight', PREFLIGHT), ('place', PREFLOOR), ('place', PLACE), ('gen', PREFLIGHT)])
def test_budget_verdict_precedes_infra_chatter(stage, text):
    cls, why = KW.classify(stage, text + '\nOOMKilled\not-run: RAN on epyc7: exit 143\n')
    assert cls == 'PLAN' and 'split or harden' in why

@pytest.mark.parametrize('text', [
    'OT_CELL_BUDGET stage=pre_floorplan synth=280000 pins=100 macros=0 projected_place=290000 budget=400000 (+-25 %)',
    PLACE + ' (OT_CELL_BUDGET_GATE=0: capacity probe, not stopped)',
    'q: R-CAP NEAR projected movable cells after resize 350000',
])
def test_nonfailure_budget_record_does_not_hide_real_failure(text):
    cls, _ = KW.classify('place', text + '\nOOMKilled\n')
    assert cls == 'INFRA'
