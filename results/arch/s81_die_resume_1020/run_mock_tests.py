# Direct runner for existing pure-Tcl tests on fleet hosts without pytest.
import importlib.util, sys, tempfile, types
from pathlib import Path
class Mark:
    def __getattr__(self, name):
        return lambda *a, **k: lambda f: f
sys.modules['pytest'] = types.SimpleNamespace(mark=Mark())
spec=importlib.util.spec_from_file_location('pairing', Path(__file__).parent/'tests/test_fclk_pairing.py')
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
rows=[(False,False,False,0,'FAIL',3,0,0),(True,False,False,0,'PASS',2,0,0),(True,True,False,0,'FAIL',2,0,0),(True,False,True,0,'FAIL',1,1,0),(True,False,False,1,'PASS',1,0,1),(True,False,False,2,'PASS',1,0,1),(True,False,False,3,'FAIL',2,0,0)]
for row in rows:
    with tempfile.TemporaryDirectory() as d: m.test_complete_payload_contract(Path(d),*row)
with tempfile.TemporaryDirectory() as d: m.test_shallow_payload_buffer_plan(Path(d))
print('PASS 8 cases: complete payload, real shallow fault, missing bit, tie semantics, data buffer plan')
