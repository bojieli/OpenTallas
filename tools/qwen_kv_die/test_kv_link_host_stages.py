"""TOK-KV-4 10-29: target 11 (the link-end calendar) is rebuilt with the HOST record relay of the bound pair image.

The pair image compiled with D2D_HOST_STAGES = H (d2d_cal_image_production.sh, run_mu833.sh HRT) records TXDP_K byte 1 =
2 + H + PR 2; kv_static_programme reads H back so link_image_check compares like with like (with --host-stages 0 the
H = 153 image of bind5 failed 'target 11 differs ... at word(s) [13, 15, 23]')."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kv_static_programme as C  # noqa: E402


def _img(word):
    txt = (C.ROOT / C.LINK_IMAGE).read_text()
    import re
    txt = re.sub(r"D2D_TXDP_K = 32'h[0-9a-fA-F]+;", f"D2D_TXDP_K = 32'h{word};", txt)
    d = tempfile.mkdtemp()
    p = Path(d, 'img.svh')
    p.write_text(txt)
    return p


class LinkHostStages(unittest.TestCase):
    def test_committed_image_has_no_relay(self):
        self.assertEqual(C.image_host_stages(), 0)
        self.assertIn('--host-stages', C.LINK_ARGS)
        self.assertEqual(C.LINK_ARGS[C.LINK_ARGS.index('--host-stages') + 1], str(C.LINK_HOST_STAGES))

    def test_relay_image_reads_back_h(self):
        self.assertEqual(C.image_host_stages(_img('03039daa'), root=Path('/')), 153)

    def test_short_port1_fails_closed(self):
        with self.assertRaises(SystemExit):
            C.image_host_stages(_img('030302aa'), root=Path('/'))


if __name__ == '__main__':
    unittest.main()
