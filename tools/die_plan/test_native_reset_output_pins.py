"""Actual SU native output ABI survives generation without a global reset solve."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import reset_tree as R
import schema as S


def fixture(y=167.392, start=True):
    tree=dict(root=[612.96,1330.592],outs=[[156.0,8.608],[8.16,y]],start=start,
              start_in=[610.784,1330.592])
    return SimpleNamespace(types={'t':dict(outline_um=[622.08,1339.2])}, reset={},
        layers={n:dict(name=n,dir=d,pitch_um=.064,offset_um=.032) for n,d in [('M6','H'),('M7','V')]},
        layer_budget=dict(partition_signal_max='M7'),
        _bound_native_reset_contracts={'t':dict(tree=tree)})


class NativeResetOutputPins(unittest.TestCase):
    def test_actual_two_su_abis_with_global_solver_forbidden(self):
        # The right entry neighbour is an existing clock tap, as in these SU types.
        for y in (167.392,502.176):
            p=fixture(y)
            with patch.object(R,'wf_solve',side_effect=AssertionError('global solve forbidden')), \
                 patch.object(R,'_plan_taps',return_value=[('clk',615.136,1330.592)]), \
                 patch.object(S,'core_taps',return_value=[]):
                self.assertEqual(R.out_pins(p,'t'),[('rst_o_0',156.0,8.608),('rst_o_1',8.16,y)])
                self.assertEqual(R.start_out_pins(p,'t'),[('start_o_0',158.176,8.608),('start_o_1',10.336,y)])

    def test_no_start_does_not_invent_start_ports(self):
        p=fixture(start=False)
        with patch.object(R,'_start_sites',side_effect=AssertionError('no START siting')):
            self.assertEqual(len(R.out_pins(p,'t')),2)
            self.assertEqual(R.start_out_pins(p,'t'),[])

    def test_changed_entry_site_is_rejected(self):
        p=fixture();p._bound_native_reset_contracts['t']['tree']['start_in']=[600,1300]
        with patch.object(R,'_plan_taps',return_value=[('clk',615.136,1330.592)]), \
             patch.object(S,'core_taps',return_value=[]):
            with self.assertRaisesRegex(R.ResetError,'captured entry site'):
                R.start_out_pins(p,'t')

    def test_nonnative_nonwavefront_stays_empty(self):
        p=fixture();p._bound_native_reset_contracts={}
        with patch.object(R,'wavefront',return_value=False):
            self.assertEqual(R.out_pins(p,'t'),[])
            self.assertEqual(R.start_out_pins(p,'t'),[])

if __name__=='__main__':unittest.main()
