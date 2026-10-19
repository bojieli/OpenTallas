#!/usr/bin/env python3
"""tests for hr_contract.py (QW-DIEFIX 10-19): the generated pack equals the file, the tree passes, the as-built
tt_ctlm hr layout fails, and the pack maps the four real L0 ROM commands (unit_c4 stage-1 log, QW-XHEAD XT1) onto
the slice layout {go, ib (me_array order)} that XT1 measured bit-exact."""
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import hr_contract as H  # noqa: E402

LOG_ROM = dict(
    qkv='00000020000010000080003008000004800000800000000000100100000000100000800004000000000010000080601',
    o='00000020000010000080000008000184000000200000000000100c5f000000100000800001000004000004000182001',
    gu='0000002000001000008000b9f8000a83800002000000000000100100000000100000800010000007000040000081801',
    down='00000020000010000080000008001084000000600000000000100d7f00000010000080000300001700000c000182001')
OPS = dict(qkv=dict(nout=768, tiles=1, k=8, wbase=0, xbase=4096), o=dict(nout=4096, tiles=3, k=2, wbase=64, xbase=50672),
           gu=dict(nout=3072, tiles=1, k=32, wbase=112, xbase=4096), down=dict(nout=4096, tiles=3, k=6, wbase=368, xbase=55280))
SRC = [H.PACK, H.RK, H.ME, H.SLICE, H.HEADS] + H.CTLM


def pack_eval(v):
    p = 0
    for ph, pl, ch, cl in re.findall(r'assign p\[(\d+):(\d+)\] = cmd\[(\d+):(\d+)\]', H.gen_pack()):
        ph, pl, cl = int(ph), int(pl), int(cl)
        p |= ((v >> cl) & ((1 << (ph - pl + 1)) - 1)) << pl
    return p


def slice_decode(gi_hr):
    """what the slice / tiles read from hr[452:73]: go = top bit, ib fields MSB first in me_array order"""
    out, pos = {'go': gi_hr >> H.IBW}, H.IBW
    for n, w in H.FIELDS:
        pos -= w
        out[n] = (gi_hr >> pos) & ((1 << w) - 1)
    return out


class T(unittest.TestCase):
    def test_pack_file_is_generated(self):
        self.assertEqual((ROOT / H.PACK).read_text(), H.gen_pack())

    def test_tree_passes(self):
        errs, info = H.check(ROOT, H.CTLM)
        self.assertEqual(errs, [])
        self.assertTrue(all(v['packed'] for v in info['ctlm'].values()))

    def test_real_commands_decode(self):
        for name, h in LOG_ROM.items():
            d = slice_decode(pack_eval(int(h, 16)))
            self.assertEqual(d['go'], 1, name)
            for k, v in OPS[name].items():
                self.assertEqual(d[k], v, (name, k))
            raw = slice_decode(int(h, 16))          # as built: hr[452:73] = cmd380
            self.assertEqual(raw['go'], 0, name)    # no go on the die

    def test_asbuilt_fails(self):
        with tempfile.TemporaryDirectory() as td:
            r = Path(td)
            for s in SRC:
                if (ROOT / s).exists():
                    (r / s).parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy(ROOT / s, r / s)
            c = r / H.CTLM[0]
            t = c.read_text()
            t = re.sub(r'hr <= \{ib_hr,', 'hr <= {ib,', t)
            t = re.sub(r'assign hr = \{ib_hr,', 'assign hr = {ib_q,', t)
            c.write_text(t)
            errs, info = H.check(r, H.CTLM)
            self.assertTrue(any('raw cmd380' in e for e in errs), errs)
            (r / H.PACK).write_text(H.gen_pack().replace('cmd[18:1]', 'cmd[19:2]'))
            errs, _ = H.check(r, H.CTLM)
            self.assertTrue(any('differs from the generated' in e for e in errs), errs)

    def test_lpf_child_pack(self):
        # MU-QW-DIE 10-19: the landed re-cut packs in its wires-only child u_thru; an as-built child must fail
        with tempfile.TemporaryDirectory() as td:
            r = Path(td)
            for s in SRC + H.PARTS:
                if (ROOT / s).exists():
                    (r / s).parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy(ROOT / s, r / s)
            errs, info = H.check(r, H.CTLM)
            self.assertTrue(info['ctlm'][H.CTLM[1]]['packed'], errs)
            pp = r / H.PARTS[0]
            pp.write_text(pp.read_text().replace('qfd_dv_hr_pack #(.ASBUILT(0))', 'qfd_dv_hr_pack #(.ASBUILT(1))'))
            errs, _ = H.check(r, H.CTLM)
            self.assertTrue(any(H.CTLM[1] in e and 'raw cmd380' in e for e in errs), errs)

    def test_die_trace(self):
        dv = """  wire [452:0] h0;
  wire [452:0] h1;
  wire [452:0] h2;
  wire [452:0] h3;
  qfd_tt_ctlm_dv tt_ctlm (.hr(h0), .cmd(c0));
  qfd_rlyh0_453_WE_80x30 rly0 (.a(h0), .b(h1), .ck(k));
  qfd_dv_slice2_w dvs_W5 (.hr_wi(h1), .hr_eo(h2));
  qfd_dv_slice2_w dvs_W4 (.hr_wi(h2), .hr_eo(h3));
"""
        info = {}
        self.assertEqual(H.die_check(dv, ROOT, info), [])
        self.assertEqual(info['die_hr_path'], dict(relay_hops=1, slices=['dvs_W5', 'dvs_W4']))
        bad = dv.replace('.hr_wi(h2)', '.hr_wi({h2[0], h2[452:1]})')
        self.assertTrue(H.die_check(bad, ROOT, {}))


if __name__ == '__main__':
    unittest.main()
