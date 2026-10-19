import json, hashlib
from pathlib import Path
p=Path(__file__).resolve().parent
a=json.loads((p/'original_typed_terminal_contract.json').read_text())
b=json.loads((p/'typed_terminal_contract.json').read_text())
r=json.loads((p/'geometry_distinction.json').read_text())
assert hashlib.sha256((p/'original_typed_terminal_contract.json').read_bytes()).hexdigest()==r['original_typed_contract_sha256']
assert len(a['rows'])==len(b['rows'])==647
for old,new in zip(a['rows'],b['rows']):
    g=r['actual_master_and_fixture_geometry'][old['family']]
    annotated=dict(new)
    assert annotated.pop('macro_outline_nm')==g['master_outline_nm']
    assert annotated.pop('fixture_envelope_nm')==g['fixture_envelope_nm']
    assert annotated==old
    w,h=g['master_outline_nm']
    assert g['fixture_envelope_nm']==[w+86400,h+86400]
    assert abs(g['master_area_um2']-w*h/1e6)<1e-9
    for port in old['ports']:
        x,y,X,Y=port['rect_nm'];assert 0<=x<X<=w and 0<=y<Y<=h
    if old.get('candidate_external_corridor_nm') is not None:
        want=([0,43200,43200,43200+h] if old['face']=='W' else [43200+w,43200,86400+w,43200+h])
        assert old['candidate_external_corridor_nm']==want
for k,v in a.items():
    if k!='rows':assert b[k]==v
assert abs(r['five_SC2_macro_area_um2']-47487.96)<1e-8
assert abs(r['five_independent_fixture_envelope_area_um2']-197409.24)<1e-8
print('PASS: all647 original rows unchanged; localports/corridors match actual masters; fixture envelopes separately identified')
