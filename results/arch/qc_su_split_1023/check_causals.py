"""Four actual-SV causal mutations of the directed SU source extraction."""
from pathlib import Path
import json
import shutil
import subprocess
import sys
import tempfile
ROOT = Path(__file__).resolve().parents[3]
D = Path(__file__).resolve().parent
packet = json.loads((ROOT/'physical/die_plan/qwen_compute/inputs/su_directed.json').read_text())
files = list(packet['sources']) + ['physical/die_plan/qwen_compute/inputs/s8_lp_record.json', 'tools/landed_parent/lp.py']
mutants = [
    ('remove_core_gb_driver', 'rtl/qwen_dv/s5/s8/qfd_dv_s8_suvm_rp1.sv', 'output wire [499:0]   gb', 'input wire [499:0]   gb'),
    ('make_lrly_gb_driver', 'rtl/qwen_dv/s5/qfd_dv_s5_leaves.sv', 'input  wire [499:0]   gb', 'output wire [499:0]   gb'),
    ('lane4_pd_overlap', 'rtl/qwen_dv/s5/s8/qfd_dv_s8_flat.sv', '.pd1(pd1[479:384])', '.pd1(pd1[383:288])'),
    ('wrong_sc_window_source', 'rtl/qwen_dv/s5/s8/qfd_dv_s8_flat.sv', 'assign sc_win0 = L_vm_waddr[23:22]', 'assign sc_win0 = L_vm_waddr[119:118]'),
]
results = []
with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    for f in files:
        dst = root/f
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/f, dst)
    def run():
        return subprocess.run([sys.executable,str(D/'inspect_su.py'),str(root)],capture_output=True,text=True)
    positive = run()
    assert positive.returncode == 0, positive.stderr
    results.append(dict(case='positive_exact_sources',exit=0,verdict='PASS'))
    for name,f,old,new in mutants:
        p=root/f
        text=p.read_text()
        assert old in text,(name,old)
        # Only the exact matching SU header/site, not similarly named other modules.
        p.write_text(text.replace(old,new,1))
        r=run()
        assert r.returncode != 0,(name,'mutation escaped')
        results.append(dict(case=name,exit=r.returncode,verdict='CAUGHT',reason=r.stderr.splitlines()[-1]))
        p.write_text(text)
print(json.dumps(dict(scope='actual source connectivity only',results=results),indent=2))
