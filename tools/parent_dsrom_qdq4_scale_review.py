"""Static scale screen; no RTL, checkpoint, or hardware admission."""
import json, subprocess, sys, types
from pathlib import Path
import numpy as np

PIN = '4e38326d6f361bc85e660f48c59c355e2bb95274'
for name, path in [('hdc_golden', 'tools/hdc_golden.py'), ('parent_scale_golden', 'tools/hdc_golden_v41.py')]:
    data = subprocess.check_output(['git', 'show', PIN + ':' + path])
    module = types.ModuleType(name)
    module.__file__ = str(Path.cwd() / path)
    sys.modules[name] = module
    exec(compile(data, module.__file__, 'exec'), module.__dict__)
g = sys.modules['parent_scale_golden']
u = np.arange(0x7f80, dtype=np.uint32) << 16
x = u.view(np.float32)
amax = np.maximum(x, g.FP4_AMAX_FLOOR_E4M3)
expected = np.minimum(g._e4m3_round(amax.astype(np.float64) / 6), 448)
sub = [0x3c900000, 0x3cf00000, 0x3d280000, 0x3d580000, 0x3d840000, 0x3d9c0000, 0x3db40000]
actual = []
for v in amax.view(np.uint32):
    v = int(v)
    ma = (1 << 23) | (v & 0x7fffff)
    ea = ((v >> 23) & 255) - 127
    if v < 0x3dc00000:
        n = 1 + sum(v > t or (v == t and j % 2 == 1) for j, t in enumerate(sub, 1))
        qs = -9
    elif v & (1 << 22):
        n = 8 + sum(ma > 3*(17+2*j)*(1 << 18) or (ma == 3*(17+2*j)*(1 << 18) and j % 2 == 1) for j in range(3))
        qs = ea - 5
    else:
        n = 11 + sum(ma > 3*(17+2*j)*(1 << 17) or (ma == 3*(17+2*j)*(1 << 17) and j % 2 == 1) for j in range(3, 8))
        qs = ea - 6
    actual.append(n * 2.0**qs)
actual = np.array(actual)
bad = np.where(actual != expected)[0]
fixed = np.minimum(actual, 448)
assert np.array_equal(fixed, expected)
record = dict(schema='opentallas.parent.qdq4-scale-static-screen.v1', source_pin=PIN,
    scope='Integer transcription of retained S3 against actual pinned golden scale for every nonnegative finite BF16 amax; not RTL execution or proof for all FP32 inputs',
    finite_BF16_amax_encodings=len(u), retained_scale_mismatches=len(bad),
    first_mismatch_BF16_bits=hex(int(u[bad[0]] >> 16)), first_mismatch_amax=float(x[bad[0]]),
    retained_scale_first=float(actual[bad[0]]), golden_scale_first=float(expected[bad[0]]),
    static_min448_scale_mismatches=int(np.count_nonzero(fixed != expected)),
    interpretation='Apply existing golden saturation before thresholds/codes/dequant and raw sideband. Independently execute full pipeline boundaries/nonfinite before admission.',
    checkpoint_reads=False, RTL_executed=False, hardware_admission=False)
out = Path('results/rtl/parent_dsrom_prerequisite_review_20261002/qdq4_scale_static_screen.json')
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps(record))
