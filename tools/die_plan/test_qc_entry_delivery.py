import qc_entry_delivery as Q

class Plan:
    parts={'a':{},'b':{}}
    def ptype(self,p):return {'clock':dict(tap_um=[5.,3.] if p=='a' else [5.,500.],layer='M9' if p=='a' else 'M5')}
    def to_die(self,p,xy):return xy

def test_direct_entry_keeps_actual_pin_and_marks_long_branch_pending():
    m=dict(M8=[dict(y=0.,x0=0.,x1=10.)],M9=[dict(x=0.,y0=0.,y1=10.)])
    r=Q.direct_delivery(Plan(),m)
    assert r['complete'] is False and r['partitions']==2
    assert r['taps'][0]['xy']==[5.,3.] and r['taps'][0]['terminal_layer']=='M9'
    assert r['taps'][0]['mesh_anchor']==['M8',5.,0.]
    assert r['pending_staged_branches'][0]['wire_um']==500.
    assert r['pending_staged_branches'][0]['terminal_layer']=='M5'
