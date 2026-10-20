"""MU-DQ-SLICEKC 10-19 (coordinator constraint): the compiler passes kc on EVERY matvec STN.

qfd_dv_redstn2 (QW-DIEFIX last-k) keeps only the k = kc - 1 block of every tile-pair stream, from STN cmd[66:59] = kc - 1.
A matvec STN that leaves the field 0 while its op has kc > 1 passes every partial sum as a result (the MUT 14 failure:
dv_bench2 k FAIL 128/512).  This file fails when any STN emitter under tools/qwen_layerbench or tools/qwen_static_schedule
(or the bench encoder rtl/test/qwen_dv/dv_bench.cmd_stn the RTL benches drive) drops or misplaces kc.

  python3 -m pytest -q tools/qwen_static_schedule/test_stn_kc.py      (repository root)
"""
import ast
import sys
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(TOOLS / "qwen_layerbench"))
sys.path.insert(0, str(ROOT / "rtl/test/qwen_dv"))
from qwen_static_schedule import mu_calendar as M     # noqa: E402
from qwen_static_schedule import mu_opcal as O        # noqa: E402
from qwen_static_schedule import mu_tok_cases as C    # noqa: E402
import dv_lower as DL                                 # noqa: E402

MATVEC_OPS = [op for op, unit, _, _ in M.LAYER_WINDOWS if unit == "me"]
STN_EMITTERS = {"stn", "cmd_stn"}


def kind(c):
    return (c >> 1) & 7


def dst(c):
    return (c >> 112) & 15


def kcm1(c):
    return (c >> 59) & 0xFF


def is_slice_stn(c):
    """a station command to the slices (kind 2, not the dst-14 LOCAL SEG pulse)"""
    return (c & 1) and kind(c) == 2 and dst(c) != 14


class TestStnKc(unittest.TestCase):
    def test_kc_table_covers_every_matvec(self):
        self.assertEqual(sorted(MATVEC_OPS), sorted(k for k in C.MATVEC_KC if k != "lm_head"))
        self.assertIn("lm_head", C.MATVEC_KC)
        self.assertTrue(all(1 <= v <= 256 for v in C.MATVEC_KC.values()))
        self.assertTrue(any(v > 1 for v in C.MATVEC_KC.values()))

    def test_layer_segment_stn_carry_kc(self):
        segs = C.segments()
        stns = [c for _, c in segs[1] if is_slice_stn(c)]
        self.assertEqual(len(stns), len(MATVEC_OPS))
        for op, c in zip(MATVEC_OPS, stns):        # one STN per me op, in LAYER_WINDOWS order (entries sorted by time)
            kc = C.MATVEC_KC[op]
            self.assertEqual(kcm1(c), kc - 1, op)
            if kc > 1:
                self.assertNotEqual(kcm1(c), 0, f"{op}: matvec STN leaves kc 0 with kc {kc}")
        head = [c for _, c in segs[2] if is_slice_stn(c)]
        self.assertEqual(len(head), 1)
        self.assertEqual(kcm1(head[0]), C.MATVEC_KC["lm_head"] - 1)

    def test_opcal_entries_and_user_words_keep_kc(self):
        ent = [(t, c, op) for t, c, op in O.layer_entries() if is_slice_stn(c)]
        self.assertEqual(sorted(op for _, _, op in ent), sorted(MATVEC_OPS))
        for _, c, op in ent:
            for u in range(4):                     # qfd_dv_cmd_cal_mu user words: user [52:51] must not touch kc
                w = O.reloc(c, u)
                self.assertEqual(kcm1(w), C.MATVEC_KC[op] - 1, (op, u))
                self.assertEqual((w >> 51) & 3, u, (op, u))

    def test_every_image_stn_has_kc(self):
        """every slice STN anywhere in the MU calendar images (all segments) carries kc - 1 != 0 when the op has kc > 1"""
        segs = C.segments()
        for s, ents in segs.items():
            for _, c in ents:
                if is_slice_stn(c):
                    self.assertNotEqual(kcm1(c), 0, f"segment {s}: STN {c:029x} leaves kc 0")

    def test_dv_lower_cmd_stn_needs_kc(self):
        with self.assertRaises(TypeError):
            DL.cmd_stn(15, 0, 0, 8, 0, 1, 0x100)    # kc has no default
        c = DL.cmd_stn(15, 0, 0, 8, 0, 1, 0x100, kc=32, amax=1)
        d = DL.decode_cmd(c)
        self.assertEqual((d["kc"], d["user"], d["amax"], d["nwords"]), (32, 0, 1, 8))
        self.assertEqual(kcm1(c), 31)

    def test_encoders_agree(self):
        """dv_lower.cmd_stn, mu_tok_cases.stn and the bench encoder dv_bench.cmd_stn place kc in the same bits"""
        import dv_bench as B
        for kc in (1, 2, 6, 8, 32, 256):
            self.assertEqual(kcm1(B.cmd_stn(0, 0, 16, 0, 1, 0x100, kcm1=kc - 1)), kc - 1)
            self.assertEqual(kcm1(C.stn(0x100, kc=kc)), kc - 1)
            self.assertEqual(kcm1(DL.cmd_stn(15, 0, 0, 16, 0, 1, 0x100, kc=kc)), kc - 1)
            self.assertEqual((C.stn(0x100, kc=kc, amax=1) >> 51) & 3, 0)     # the MU user field stays free

    def test_no_emitter_call_without_kc(self):
        """static: every call of an STN emitter in the compiler trees passes kc (keyword); a new emitter call that
        forgets it fails here even before an image is built"""
        bad = []
        for tree in ("tools/qwen_layerbench", "tools/qwen_static_schedule"):
            for p in sorted(q for q in (ROOT / tree).glob("*.py") if not q.name.startswith("test_")):
                for node in ast.walk(ast.parse(p.read_text(), str(p))):
                    if isinstance(node, ast.Call):
                        f = node.func
                        name = f.id if isinstance(f, ast.Name) else f.attr if isinstance(f, ast.Attribute) else None
                        if name in STN_EMITTERS and not any(k.arg == "kc" for k in node.keywords):
                            bad.append(f"{p.relative_to(ROOT)}:{node.lineno}")
        self.assertEqual(bad, [], "STN emitter calls without kc")


if __name__ == "__main__":
    unittest.main()
