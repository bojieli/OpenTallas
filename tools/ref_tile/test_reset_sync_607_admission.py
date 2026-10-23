"""ot_reset_sync 607e5cbb admission (coordinator 2026-10-22, ba140fd98 seq-b1 OUTPUT_COPIES/TREE).

The new source is admitted next to 489e493c only when every ot_reset_sync instance elaborates the reviewed g_original
form (OUTPUT_COPIES=1, TREE=0).  An old-hash kit and a new-hash kit pass; a TREE=1 / OUTPUT_COPIES>1 instance inside a
reviewed FIFO (set from the parent with a hierarchical defparam, the FIFO source unchanged) is refused by both tools.
"""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import async_gray_fifo_constraints as A
import gray_fifo_cdc_constraints as G
from test_async_fifo_parent_constraints import PARENT, parent_spec
from test_async_gray_fifo_constraints import ROOT, YOSYS

OLD, NEW = ('489e493c19aa1260853031fee35c14ea3394ae62ff6853cf7ea407cb8fb78bbd',
            '607e5cbb71e4912c3ac966fa555b1be83bf5f0346b41b69411e46a641c4e326a')
RS = 'rtl/lib/ot_reset_sync.sv'


def old_source():
    """the 489e493c ot_reset_sync (before ba140fd98), from git"""
    p = subprocess.run(['git', '-C', str(ROOT), 'show', 'ba140fd98^:' + RS], capture_output=True)
    if p.returncode:
        raise unittest.SkipTest('ba140fd98^ not in this clone')
    return p.stdout


def tree(root, files, rs_bytes=None):
    for f in files:
        p = Path(root) / f
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(rs_bytes if (f == RS and rs_bytes is not None) else (ROOT / f).read_bytes())


DEFPARAM = {
    'tree1': 'defparam u_fifo.u_wr_reset.TREE = 1; defparam u_fifo.u_wr_reset.OUTPUT_COPIES = 4;',
    'copies4': 'defparam u_fifo.u_rd_reset.OUTPUT_COPIES = 4;',
}


@unittest.skipUnless(Path(YOSYS).exists(), 'Yosys 0.68 required')
class AsyncGray(unittest.TestCase):
    def load(self, rs_bytes=None, extra=''):
        with tempfile.TemporaryDirectory() as tmp:
            tree(tmp, A.SOURCES, rs_bytes)
            (Path(tmp) / 'parent.sv').write_text(PARENT.replace('endmodule', extra + '\nendmodule'))
            A.elaborate.cache_clear()
            return A.load(parent_spec(), tmp)

    def test_old_and_new_hash_kits_pass(self):
        import hashlib
        old = old_source()
        self.assertEqual(hashlib.sha256(old).hexdigest(), OLD)
        self.assertEqual(hashlib.sha256((ROOT / RS).read_bytes()).hexdigest(), NEW)
        for name, rs in (('old', old), ('new', None)):
            with self.subTest(kit=name):
                r = self.load(rs)
                self.assertEqual(r['source_sha256'][RS], OLD if name == 'old' else NEW)
                self.assertIn('u_fifo.u_wr_reset', r['reset_syncs'])

    def test_tree_or_copies_inside_fifo_refused(self):
        for name, dp in DEFPARAM.items():
            with self.subTest(mutant=name):
                with self.assertRaisesRegex(ValueError, 'only the reviewed g_original form'):
                    self.load(None, dp)

    def test_unknown_hash_still_refused(self):
        with self.assertRaisesRegex(ValueError, 'reviewed source changed'):
            self.load((ROOT / RS).read_bytes() + b'\n// edit\n')

    def test_parameter_check_unit(self):
        A.reset_sync_original({}, 'x')                                              # 489e493c: no such parameters
        A.reset_sync_original({'OUTPUT_COPIES': '0' * 31 + '1', 'TREE': '0' * 32}, 'x')
        for bad in ({'TREE': '0' * 31 + '1'}, {'OUTPUT_COPIES': '0' * 29 + '100'}, {'TREE': 'x'}):
            with self.assertRaisesRegex(ValueError, 'g_original'):
                A.reset_sync_original(bad, 'x')


CH_SOURCES = [RS, 'rtl/physical/ot_qwen_async_fifo_w.sv', 'rtl/lib/ot_async_fifo.sv', 'rtl/physical/ot_qwen_die_cdc_ch.sv']
WRAP = '''module ch_wrap #(parameter integer W = 16, parameter integer PIPE = 2) (
  input wire wclk, wrst_n, i_v, input wire [W-1:0] i_d, output wire i_cr, w_fault,
  input wire rclk, rrst_n, output wire o_v, output wire [W-1:0] o_d, input wire o_cr, output wire r_fault);
  ot_qwen_die_cdc_ch #(.W(W), .PIPE(PIPE)) u_ch(.wclk(wclk), .wrst_n(wrst_n), .i_v(i_v), .i_d(i_d), .i_cr(i_cr),
    .w_fault(w_fault), .rclk(rclk), .rrst_n(rrst_n), .o_v(o_v), .o_d(o_d), .o_cr(o_cr), .r_fault(r_fault));
  DEFP
endmodule
'''


def ch_spec():
    doms = dict(phy=dict(ratio=G.family_ratio('phy'), ports=['wclk'], inputs=['wrst_n', 'i_v', 'i_d'],
                         outputs=['i_cr', 'w_fault']),
                core=dict(ratio=[1, 1], ports=['rclk'], inputs=['rrst_n', 'o_cr'], outputs=['o_v', 'o_d', 'r_fault']))
    return dict(top='ch_wrap', kind='tile', clock='multiple_cts_roots', clock_port='rclk', clock_ports=['wclk', 'rclk'],
                params=dict(W=16, PIPE=2), clock_data_paths='reviewed_gray_fifos', sources=CH_SOURCES + ['ch_wrap.sv'],
                clock_relationship=dict(kind='independent_clock_families', periods_ps=dict(phy=1043.0, core=833.333)),
                clock_entry_domains=doms)


@unittest.skipUnless(Path(YOSYS).exists(), 'Yosys 0.68 required')
class GrayFifo(unittest.TestCase):
    def lint(self, rs_bytes=None, defp=''):
        with tempfile.TemporaryDirectory() as tmp:
            tree(tmp, CH_SOURCES, rs_bytes)
            (Path(tmp) / 'ch_wrap.sv').write_text(WRAP.replace('DEFP', defp))
            return G.lint(ch_spec(), tmp)

    def test_old_and_new_hash_kits_pass(self):
        for name, rs in (('old', old_source()), ('new', None)):
            with self.subTest(kit=name):
                self.assertEqual(self.lint(rs)['counts']['rstage'], 32)

    def test_tree_inside_fifo_refused(self):
        inst = 'u_ch.g_afw.u_af.wr_reset_conditioner'
        # TREE=1: refused by the g_original check or, when the copy tree leaves reset_pipe unused, already by the
        # stage-count check (ROOT-MERGE-1022: either refusal is accepted); OUTPUT_COPIES=4 (g_regions) is already refused by the pipe-structure checks
        # (its last reset_pipe stage is not a flop any more), before the g_original check is reached
        for name, dp, why in (('tree1', f'defparam {inst}.TREE = 1; defparam {inst}.OUTPUT_COPIES = 4;', 'g_original|fewer than 2 stages'),
                              ('copies4', f'defparam {inst}.OUTPUT_COPIES = 4;', 'wr_reset_conditioner')):
            with self.subTest(mutant=name):
                with self.assertRaisesRegex(G.GrayFifoError, why):
                    self.lint(None, dp)

    def test_unknown_hash_still_refused(self):
        with self.assertRaisesRegex(G.GrayFifoError, 'reviewed source changed'):
            self.lint((ROOT / RS).read_bytes() + b'\n// edit\n')


if __name__ == '__main__':
    unittest.main()
