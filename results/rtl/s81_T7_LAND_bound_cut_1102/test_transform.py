#!/usr/bin/env python3
"""Guard controls for transform.py: the four approved preimages transform; each targeted corruption is refused."""
import hashlib, importlib.util, json, sys
from pathlib import Path
here = Path(__file__).parent
spec = importlib.util.spec_from_file_location('landcut', here / 'transform.py'); t = importlib.util.module_from_spec(spec); spec.loader.exec_module(t)
pre = Path(sys.argv[1])           # directory holding the four extracted preimages
P = t.P
names = {'original_T7': 's81_T7_pmem_bound_cut_0900_native_parent.sv', 'PMEM_data_cut': 's81_T7_pmem_bound_cut_0900_DISABLED_bound.sv',
         'PVQ_only_data_cut': 's81_T7_pvq_bound_cut_1040_PVQ_only_bound.sv', 'PMEM_PVQ_joint_data_cut': 's81_T7_pvq_bound_cut_1040_PMEM_PVQ_joint_bound.sv'}
res = {}
for k, n in names.items():
    new, removed, h = t.transform((pre / n).read_text())
    res[k] = dict(after_sha256=hashlib.sha256(new.encode()).hexdigest(), removed=len(removed))
base = (pre / names['original_T7']).read_text()
def corrupt(old, new):
    assert base.count(old) == 1, old
    return base.replace(old, new)
controls = {
    'lane1_wrong_RD_slice': corrupt('{1\'b0, ' + P + '622_Y[7:0], ' + P + 'land_RD_DATA[511:256]}', '{1\'b0, ' + P + '622_Y[7:0], ' + P + 'land_RD_DATA[767:512]}'),
    'RD_ADDR_lane1_offset': corrupt('assign ' + P + '542_Y = ' + P + '541_Y[31:0] + 32\'b00000000000000000000000000000001;', 'assign ' + P + '542_Y = ' + P + '541_Y[31:0] + 32\'b00000000000000000000000000000010;'),
    'extra_struct_reader': base.replace('endmodule', '    wire [10:0] tokds3_probe = ' + P + '711_Y[100:90];\nendmodule', 1),
    'lane2_win_on_tjob': corrupt('assign ' + P + '658_Y = ' + P + '635_Y[31:0] < {{24{1\'b0}}, ' + P + 'driver_wcount_Q[7:0]};', 'assign ' + P + '658_Y = ' + P + '635_Y[31:0] < {{22{1\'b0}}, ' + P + '60_Y[9:0]};'),
    'unapproved_hash': base + '\n',
}
caught = {}
for k, s in controls.items():
    h = hashlib.sha256(s.encode()).hexdigest()
    if k != 'unapproved_hash': t.ALLOWED[h] = 'control'
    try:
        t.transform(s); caught[k] = 'NOT_CAUGHT'
    except (ValueError, AssertionError) as e:
        caught[k] = 'REFUSED: ' + str(e)
    t.ALLOWED.pop(h, None)
ok = all(v.startswith('REFUSED') for v in caught.values())
print(json.dumps(dict(positive=res, controls=caught, ok=ok), indent=2))
sys.exit(0 if ok else 1)
