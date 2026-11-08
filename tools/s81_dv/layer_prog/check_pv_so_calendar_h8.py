import importlib.util
from pathlib import Path
p=Path(__file__).with_name('pv_so_calendar_h8.py')
s=importlib.util.spec_from_file_location('h8',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
ages=dict(E_E=2,E_W=5,W_E=7,W_W=3)
r=m.plan_halves_h8([20,900],[20,900],ages,0,100)
w=[p[k] for p in r['passes'] for k in ('east_arrival','west_arrival')]
assert all(w[i]+320<=w[i+1] for i in range(3))
assert r['last_generated_q']-r['first_generated_q']==1083 and r['joined_records']==1280
f=m.control_frames_h8(0x92345,777,0x31,0x67,**r['entry_E'],parameters=list(range(5)))
h=f['CFG'][0]
assert [h>>sh&65535 for sh in (36,52,68,84)]==[r['entry_E'][k] for k in ('local_first','peer_first','local_first1','peer_first1')]
assert h>>508==15 and len(f['PARAM'])==6
try:m.control_frames_h8(0x92345,777,0x31,0x67,20,21,700,1040,list(range(5)))
except ValueError:pass
else:raise AssertionError('overlap mutant escaped')
try:m.plan_halves_h8([70000,80000],[70000,80000],ages,0,100)
except ValueError:pass
else:raise AssertionError('field overflow escaped')
print('H8_SOURCE_CALENDAR_PASS four checks, overlap/field-overflow controls caught')
