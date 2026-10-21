import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

root = Path(sys.argv[1]).resolve()
out = Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
inputs = Path(sys.argv[3]).resolve()
sys.path[:0] = [str(root/'tools/die_clock'),str(root/'tools/qwen_tp8'),str(root/'tools')]
import regtree as rt
import die_sta_libs as D
from qwen_compute_dieclk_prep import read_clocks

results = dict(physical_qualification_eligible=False)
trees = []
for obstacles in [[],[(2000.,2000.,4000.,4000.)]]:
    g = rt.dct.Grid(6000.,6000.,obstacles)
    b = rt.Builder(g,'t',pads=False)
    leaves = [[(f'p{i}/A',rt.BUF,300.+1300.*(i%4),300.+1700.*(i//4),f'r{i}')] for i in range(8)]
    model = b.build('root',(100.,5900.),leaves)
    trees.append(dict(model=model,buffers=b.bufs,nets=b.nets,parent=b.parent))
results['legacy_tree_sha256'] = hashlib.sha256(json.dumps(trees,sort_keys=True).encode()).hexdigest()

die = inputs/'die.v'
dirs = json.loads((inputs/'port_dirs.json').read_text())
contract = json.loads((inputs/'clock_contract.json').read_text())
n,_,_,instances = D.parse_die(die)
masters = {i:m for m,i,_,_ in instances}
lat,_,_ = read_clocks(inputs/'clocks_tt.tcl')
leaves = {}
for pin,(_,insertion) in lat.items():
    i,p = pin.split('/',1)
    if i in masters: leaves.setdefault(masters[i],{}).setdefault('tt',{})[p] = insertion
try:
    drivers,sinks,pins = D.clock_connections(die,dirs,leaves,contract.get('clock_ports'))
    missing = sorted(net for net in sinks if len(drivers.get(net,[])) != 1)
    results['actual_g5_sta_roots'] = dict(verdict='FAIL' if missing else 'PASS',missing_or_multi=missing,
                                         sinks=len(sinks),drivers=len(drivers),source_die_sha256=hashlib.sha256(die.read_bytes()).hexdigest(),
                                         physical_qualification_eligible=False)
except Exception as error:
    results['actual_g5_sta_roots'] = dict(verdict='FAIL',failure_id=type(error).__name__,message=str(error))

variant = root/'physical/qwen_missing_phy/nface_tall_g5_lclk_1020/ot_qfd_ucie_x64_phy'
if variant.exists():
    sheet = json.loads((variant/'ot_qfd_ucie_x64_phy.json').read_text())
    assert sheet['physical_qualification_eligible'] is False
    for name,sha in sheet['views'].items(): assert hashlib.sha256((variant/name).read_bytes()).hexdigest() == sha
    for corner in ['tt','ff','ss']:
        lib = D.parse_lib(variant/f'ot_qfd_ucie_x64_phy_{corner}.lib')
        assert lib['pins']['lclk']['dir'] == 'output',lib['pins']['lclk']
    results['phy_variant'] = dict(verdict='PASS',physical_qualification_eligible=False)
else: results['phy_variant'] = dict(verdict='UNAVAILABLE')

(out/'results.json').write_text(json.dumps(results,indent=2)+'\n')
print('COHORT',json.dumps(results))
