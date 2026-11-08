"""Exact native composition variants expose source defaults before param_regen."""
import tempfile
import unittest
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bind
import hbm_sfu_bridge_contract as C


class ComposedVariantTest(unittest.TestCase):
    def run_variant(self, *, width=4, direction='input', master='old_cut', new_port=False):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'variant.sv'
            extra=', input wire extra' if new_port else ''
            p.write_text(f'module variant #(parameter integer SFU_READ_RETURN=145, SFU_WRITE_RETURN=142)({direction} wire [{width-1}:0] a, output wire z{extra}); assign z=a[0]; endmodule\n')
            cell=SimpleNamespace(path='sfucore_NW.__cut_ctl', module='old_cut', kind='leaf', params={},
                                 ports={'a':[1,2,3,4], 'z':[5]}, dirs={'a':'input','z':'output'}, ytype='old_cut')
            b=object.__new__(bind.Binder)
            b.ab={'rtl_roots':[t], 'files':[], 'prefer':[]}
            b.F=SimpleNamespace(cells=[cell])
            b.errors=[];b.extra_lib=[];b.variants=[];b.param_defaults={}
            b.plan={'partitions':[]};b.R=SimpleNamespace(part_of=lambda _:None)
            b.variant_removed={'prior.input':3};b.variant_required_constants=[('prior','a',0,1,'0')]
            b.substitute_inst(t,[{'inst':r'sfucore_NW\.__cut_ctl','module':'variant','master':master}],full_abi=True)
            return b,cell

    def test_exact_abi_seeds_actual_new_parameters(self):
        b,c=self.run_variant()
        self.assertEqual(b.errors,[]);self.assertEqual(c.module,'variant')
        self.assertEqual(b.param_defaults[('old_cut','variant')],{'SFU_READ_RETURN':'145','SFU_WRITE_RETURN':'142'})
        self.assertEqual(c.ports,{'a':[1,2,3,4],'z':[5]})
        self.assertEqual(b.variant_removed,{'prior.input':3})
        self.assertEqual(len(b.variant_required_constants),1)

    def test_native_all_bit_boundary_contract(self):
        source=Path(__file__).resolve().parents[2]/'results/hbm_ctl_native_intake_0440/closure_ot_hgi_sfu_core_split3__ctl.sv'
        text=source.read_text()
        self.assertEqual((C.contract(text)['read_k'],C.contract(text)['write_k']),(2,2))
        variant=C.parameterize(text)
        self.assertIn('parameter integer SFU_READ_RETURN=145, SFU_WRITE_RETURN=142',variant)
        self.assertIn('.READ_RETURN(SFU_READ_RETURN), .WRITE_RETURN(SFU_WRITE_RETURN)',variant)

    def test_native_rotated_request_bit_mutant_rejected(self):
        source=Path(__file__).resolve().parents[2]/'results/hbm_ctl_native_intake_0440/closure_ot_hgi_sfu_core_split3__ctl.sv'
        text=source.read_text().replace('assign u_core_procdff_66916__Q[0] = n686;', 'assign u_core_procdff_66916__Q[0] = n687;')
        with self.assertRaises(ValueError): C.contract(text)

    def test_wrong_master_rejected(self):
        b,c=self.run_variant(master='unrelated');self.assertIn('VARIANT_COMPOSE_MASTER',b.errors[0]);self.assertEqual(c.module,'old_cut')

    def test_width_mutant_rejected(self):
        b,c=self.run_variant(width=3);self.assertIn('VARIANT_COMPOSE_ABI',b.errors[0]);self.assertEqual(c.module,'old_cut')

    def test_direction_mutant_rejected(self):
        b,c=self.run_variant(direction='output');self.assertIn('VARIANT_COMPOSE_ABI',b.errors[0]);self.assertEqual(c.module,'old_cut')

    def test_new_input_rejected(self):
        b,c=self.run_variant(new_port=True);self.assertIn('VARIANT_COMPOSE_ABI',b.errors[0]);self.assertEqual(c.module,'old_cut')


if __name__=='__main__':unittest.main()
