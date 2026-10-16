"""Exact source-contract counterexample; not a model of qualified PLL IP."""
from fractions import Fraction as Q
import json

def first_active(period, phase, release, reset_age):
    # x43 header: first stream index0 is fifth edge after release; serial
    # index0 is fourth. Their offsets are 4*3=3*4=12 VCO ticks.
    # Strictly after request avoids assuming setup on a coincident ref edge.
    n = max(0, (release-phase)//period + 1)
    return phase + (n+reset_age)*period

rows=[]
# Generously assume both PLL outputs already have aligned rising phase0.
# VCO tick = 1/3.6GHz; refclk=10ns=36 ticks. GAP8 => 288 ticks.
for offset in range(12):
    r=Q(64*36+offset,1)+Q(1,10)
    a=first_active(Q(3),Q(0),r,4)
    b=first_active(Q(4),Q(0),r+8*36,3)
    assert a != b
    rows.append(dict(ref_release_phase=str(r%12),stream_first=str(a),serial_first=str(b)))
# Related /3 and /4 rising edges on ONE VCO grid need not have equal phase:
# choose stream=3n and serial=1+4m. Common rising events exist at9+12k,
# but the phase/epoch differs from0+12k. Frequency and grid alone do not fix it.
profiles=[dict(serial_divider_phase=p,common_tick_mod12=next(t for t in range(12) if t%3==0 and (t-p)%4==0)) for p in range(4)]
print(json.dumps(dict(status='EXISTING_RESET_BINDING_FAIL',aligned_pll_counterexamples=rows,legal_grid_phase_profiles=profiles,source_phase_unbound=True),indent=2))
