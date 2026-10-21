"""Run only the explicitly enabled same-source reconstruction, then stop at reset."""
from pathlib import Path
import hashlib
import os
import sys

B = Path(__file__).resolve().parent
sys.path[:0] = [str(B), 'tools', 'results/arch/qwen_tp8_1012']
from actual_geometry_snapshot import enabled_snapshot, SnapshotComplete, SOURCE_SHA256
snapshot = enabled_snapshot()
if snapshot is None:
    raise SystemExit('Diagnostic OFF: set OT_Q_ACTUAL_SNAPSHOT to a NEW output directory')
root = Path.cwd().resolve()
G = snapshot.load_generator(root / 'tools/qwen_rom_fulldie_b3r2.py')
import die_top_lint as D
D.QWEN_RECIPE = 'tp8b'
D._QW.clear()
D.QSRC = None
source = D.qwen_src()
assert Path(source['root']).resolve() == root
assert sys.modules['qwen_rom_fulldie_b3r2'] is G and G._actual_snapshot_wrapped
fault_sha = hashlib.sha256((root / 'tools/qwen_split/fault_emit.py').read_bytes()).hexdigest()
assert fault_sha == '9fd4fb9a0ee3f54fa5a4942337fb1739b5d103550874f7081bfeb59cec1cf49e'
snapshot.save('run_contract.pkl', dict(root=str(root), source_sha256=SOURCE_SHA256, fault_sha256=fault_sha,
                                     env={k:v for k,v in os.environ.items() if k.startswith(('OT_', 'LAND_', 'RESET_', 'CORE_'))}))
recipe = dict(D.QWEN_RECIPES['tp8b'])
cdc = recipe.pop('cdc')
print('ACTUAL_SNAPSHOT_DIRECT_SELECTED', root, 'hooks verified; algorithms unchanged', flush=True)
try:
    G.selected(True, cdc=G._cdc_arg(cdc), **recipe)
except SnapshotComplete as done:
    print(done, flush=True)
    sys.exit(0)
raise SystemExit('Diagnostic reset interception was not reached')
