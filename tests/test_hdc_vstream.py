"""The vector stream unit's arithmetic contract (R-ARITH) and its generated lane.

The reducer (rtl/hdc/ot_hdc_vreduce.sv) sums a segment as SW/8 chunk chains a
vector, a pairwise tree inside the vector and pairing of the segment's
vectors in time (a held left operand, a LAST item that passes when nothing is
held).  `hardware_order` below is that structure, written out; the test
checks that it equals the golden's width-free reduce_chunked for every width,
which is the claim that makes one golden serve every SW."""
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import hdc_golden as G  # noqa: E402

F = np.float32


def hardware_order(v, sw):
    v = np.asarray(v, dtype=F)
    nvec = -(-len(v) // sw)
    pad = np.zeros(nvec * sw, dtype=F)
    pad[:len(v)] = v
    items = []
    for k in range(nvec):
        x = pad[k * sw:(k + 1) * sw]
        chunks = []
        for c in range(sw // 8):
            acc = x[8 * c]
            for j in range(1, 8):
                acc = G.add(acc, x[8 * c + j])
            chunks.append(F(acc))
        while len(chunks) > 1:
            chunks = [G.add(chunks[i], chunks[i + 1]) for i in range(0, len(chunks), 2)]
        items.append((F(chunks[0]), k == nvec - 1))
    # time levels: until one LAST item remains
    while not (len(items) == 1 and items[0][1]):
        out, held = [], None
        for val, last in items:
            if held is not None:
                out.append((F(G.add(held, val)), last))
                held = None
            elif last:
                out.append((val, last))
            else:
                held = val
        items = out
    return items[0][0]


@pytest.mark.parametrize("sw", [8, 16, 64, 256])
def test_reducer_structure_is_the_golden_order(sw):
    rng = np.random.default_rng(sw)
    for n in (1, 7, 8, 9, 63, 64, 65, 200, 1000, 4096):
        v = (rng.standard_normal(n) * rng.choice([1e-3, 1, 1e3], n)).astype(F)
        assert G.bits(hardware_order(v, sw)) == G.bits(G.reduce_chunked(v)), (sw, n)


def test_lane_is_generated_from_the_scalar_datapath():
    r = subprocess.run([sys.executable, str(ROOT / "tools/gen_hdc_vstream_lane.py"), "--check"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout
