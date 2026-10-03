import importlib.util
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('held_model', ROOT/'tools/hbm_held_return_model.py')
model = importlib.util.module_from_spec(spec)
spec.loader.exec_module(model)

class HeldReturn(unittest.TestCase):
    def test_sizing_replaces_mux_and_pointer_once(self):
        p=model.partition()
        self.assertEqual(p['additional_raw_ff_bits'],10)
        self.assertEqual(p['pc']['raw_ff_bits'],15)
        self.assertEqual(p['pc']['payload_mux_2to1_bits'],127*291)
        self.assertEqual(p['client']['raw_ff_bits'],3)
        for x in (p['pc'],p['client']):
            self.assertEqual(x['payload_ff_bits'],0)
            self.assertEqual(x['added_unstalled_cycles'],0)
            self.assertIsNone(x['backpressure_latency_bound'])
            self.assertFalse(x['clock_ss_ff_admitted'])

    def test_invalid_geometry(self):
        for n,w in ((0,291),(2,0),(-1,1)):
            with self.assertRaises(ValueError): model.size(n,w)

    @unittest.skipUnless(shutil.which('iverilog') and shutil.which('vvp'),'Icarus unavailable')
    def test_actual_rtl_full_bundle(self):
        with tempfile.TemporaryDirectory(prefix='hbm-held-return-') as d:
            binary=Path(d)/'tb'
            subprocess.run(['iverilog','-g2012','-s','tb','-o',str(binary),
                str(ROOT/'rtl/experimental/hbm_held_return_20261003/ot_gpu_held_return_merge.sv'),
                str(ROOT/'rtl/test/hbm_held_return_20261003/tb.sv')],check=True,capture_output=True,text=True)
            run=subprocess.run(['vvp',str(binary)],check=True,capture_output=True,text=True)
            self.assertIn('PASS held full-width merge',run.stdout)

    @unittest.skipUnless(shutil.which('iverilog') and shutil.which('vvp'),'Icarus unavailable')
    def test_full_128pc_owner46(self):
        with tempfile.TemporaryDirectory(prefix='hbm-owner128-') as d:
            binary=Path(d)/'tb'
            subprocess.run(['iverilog','-g2012','-s','tb_owner128','-o',str(binary),
                str(ROOT/'rtl/experimental/hbm_held_return_20261003/ot_gpu_held_return_merge.sv'),
                str(ROOT/'rtl/test/hbm_held_return_20261003/tb_owner128.sv')],check=True,capture_output=True,text=True)
            r=subprocess.run(['vvp',str(binary)],check=True,capture_output=True,text=True)
            self.assertIn('PASS 128PC full owner46',r.stdout)

    @unittest.skipUnless(shutil.which('iverilog') and shutil.which('vvp'),'Icarus unavailable')
    def test_actual_partition_and_legacy_counterexample(self):
        sources=[ROOT/'rtl/experimental/hbm_held_return_20261003/ot_gpu_held_return_merge.sv',
                 ROOT/'rtl/experimental/hbm_held_return_20261003/ot_gpu_hbm_partition_held.sv',
                 ROOT/'rtl/hdc/kv/ot_hdc_hbm_model.sv',
                 ROOT/'rtl/test/hbm_held_return_20261003/tb_partition.sv']
        with tempfile.TemporaryDirectory(prefix='hbm-held-partition-') as d:
            for opt in (0,1):
                binary=Path(d)/f'tb-{opt}'
                subprocess.run(['iverilog','-g2012','-s','tb_partition',
                    f'-Ptb_partition.OPT={opt}','-o',str(binary),*map(str,sources)],
                    check=True,capture_output=True,text=True)
                r=subprocess.run(['vvp',str(binary)],capture_output=True,text=True)
                if opt:
                    self.assertEqual(r.returncode,0,r.stdout+r.stderr)
                    self.assertIn('PASS actual partition',r.stdout)
                else:
                    self.assertNotEqual(r.returncode,0)
                    self.assertIn('partition changed stalled identity/data/kind',r.stdout)

if __name__=='__main__': unittest.main()
