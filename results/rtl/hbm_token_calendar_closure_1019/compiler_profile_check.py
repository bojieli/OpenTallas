import hashlib,importlib.util,sys
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
from native_su_calendar import compile_calendar
commands=[int(x,16)for x in Path('readback_expected.mem').read_text().split()]
kw=dict(first_serial=2675,bridge_serial=2675,bridge_stream=3567,host_launch=3500,rows=160)
words,_=compile_calendar(commands,**kw,request_lane_edges=4)
assert ''.join(f'{v:064x}\n'for v in words)==Path('calendar.mem').read_text()
spec=importlib.util.spec_from_file_location('old_calendar','old_native_su_calendar.py');old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
assert compile_calendar(commands,**kw)[0]==old.compile_calendar(commands,**kw)[0]
for depth in (-1,1.5):
 try:compile_calendar(commands,**kw,request_lane_edges=depth)
 except ValueError:pass
 else:raise AssertionError(depth)
try:compile_calendar(commands,**kw,request_lane_edges=200)
except ValueError:pass
else:raise AssertionError('capacity overflow accepted')
print('PROFILE_COMPILER PASS default programme unchanged;18/15 byte match; negative/noninteger/capacity guards reject')
print('compiler_sha256',hashlib.sha256(Path('native_su_calendar.py').read_bytes()).hexdigest())
