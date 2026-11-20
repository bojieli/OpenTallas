"""Small calendar mechanism check; no arithmetic or whole-HEAD claim."""
from lep_calendar import VF, STRESS, NF15F, NF15F_R13, Stages, require_matching_receipt

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

assert VF.state_bits()==14023
print('PASS vF logical stage storage 14023 bits (no clock/reset/placement overhead claim)')

# HEAD-PLAN-R4 11-17 NF15f: RXH is a priced provider leg; RXH 0 keeps the pre-R4 parameter set byte-identical.
assert 'RXH' not in VF.params() and NF15F.params()['RXH'] == 1
assert VF.legs()['rx_head.ri+mu_rt+ml_w'] == 0 and NF15F.legs()['rx_head.ri+mu_rt+ml_w'] == 1
f0 = Stages(ktx=0x1111, krx=0x2660, txi=0x2442, pin=6, pout=8, plw=3, col0=2)
assert NF15F.state_bits() - f0.state_bits() == 2208 + 44
assert f0.state_bits() - VF.state_bits() > 0
try:
    Stages(rxh=2)
except ValueError:
    print('CAUGHT RXH depth 2 (one rank only)')
else:
    raise AssertionError('RXH 2 accepted')
# FABLE-PLAN-HEAD-NF15F 1: credit depth covers the modelled K-link round trip on every lane (bench: 12 FAIL, 16 FAIL, 24 / 28 PASS)
assert 'KCRED' not in VF.params() and not VF.credit_ok()   # vF runs under full rate on RX lanes 1/2 (lane cap)
assert NF15F.params()['KCRED'] == 28 and NF15F.credit_ok()
assert [max(NF15F.credit_rtt(i).values()) for i in range(4)] == [17, 24, 24, 21]   # measured LEPK_RTT
assert not Stages(ktx=0x1111, krx=0x2660, txi=0x2442, pin=6, pout=8, plw=3, col0=2, rxh=1, kcred=16).credit_ok()
print(f'PASS NF15f tuple + RXH 1: {NF15F.state_bits()} logical stage bits, rx_head leg +1')

# The legacy provider and its receipt remain usable without an explicit KTR.
assert 'KTR' not in NF15F.params()
assert [NF15F.lane('ktr', i) for i in range(4)] == [1, 1, 1, 1]
assert [NF15F_R13.lane('ktr', i) for i in range(4)] == [2, 1, 1, 3]
assert [NF15F_R13.legs()[f'lane{i}.tx_k.forward.valid+data'] for i in range(4)] == [1]*4
assert [NF15F_R13.credit_rtt(i)['tx'] for i in range(4)] == [18, 17, 17, 19]
assert [NF15F_R13.credit_rtt(i)['rx'] for i in range(4)] == [14, 24, 24, 21]
assert NF15F_R13.credit_ok() and NF15F_R13.state_bits() == NF15F.state_bits() + 3
assert NF15F_R13.params()['KTR'] == "16'h3112"
split_receipt = dict(receipt, params=NF15F_R13.params())
assert require_matching_receipt(NF15F_R13, split_receipt, programme) == (106, 118, 217)
for stages, other in ((NF15F, NF15F_R13), (NF15F_R13, NF15F)):
    try:
        require_matching_receipt(stages, dict(receipt, params=other.params()), programme)
    except ValueError:
        pass
    else:
        raise AssertionError('incorrect KTR accepted in reservation receipt')
print('PASS r13 split TX return pricing; both wrong-KTR receipt directions CAUGHT')
