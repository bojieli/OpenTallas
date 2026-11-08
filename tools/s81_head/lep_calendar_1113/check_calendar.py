"""Small calendar mechanism check; no arithmetic or whole-HEAD claim."""
from lep_calendar import VF, STRESS, require_matching_receipt

rows = [dict(id=n, leg=leg, cycle=100+n) for n, leg in enumerate(VF.legs())]
a = VF.shift_events(rows)
assert all(x['cycle']-x['source_cycle'] == VF.legs()[x['leg']] for x in a)
assert [VF.lane('krx',i) for i in range(4)] == [0,2,2,1]
assert [VF.lane('txi',i) for i in range(4)] == [1,2,2,1]
assert a[0]['added_cycles']==2 and a[1]['added_cycles']==3
assert a[5]['added_cycles']==1 and a[6]['added_cycles']==0
programme = 'a'*64
receipt = dict(params=STRESS.params(), programme_sha256=programme, static_replay='PASS',
               removed_reservation_mutant='CAUGHT', handoff_idle_cycles=[106,118,217])
assert require_matching_receipt(STRESS,receipt,programme)==(106,118,217)
try:
    require_matching_receipt(VF,receipt,programme)
except ValueError:
    print('CAUGHT stress reservation reused for vF')
else:
    raise AssertionError('mismatched stage tuple accepted')
# A blanket +3 changes command input, zero-depth credits and collective0.
assert any(x['cycle'] != rows[i]['cycle']+3 for i,x in enumerate(a))
print('CAUGHT blanket whole-transaction +3 shift')
print(f'PASS {len(rows)} explicit register-leg calendars; vF production handoff remains OPEN')

try:
    require_matching_receipt(STRESS,receipt,'b'*64)
except ValueError:
    print('CAUGHT same-depth reservation imported from a different programme')
else:
    raise AssertionError('wrong programme accepted')
