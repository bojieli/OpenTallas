"""Canonical licensed PHY FDI slicing uses actual native ports and every bit once."""
import json
import importlib.util
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
_spec=importlib.util.spec_from_file_location('_kv_bound_netlist_under_test',
    Path(__file__).with_name('kv_bound_netlist.py'))
B=importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(B)

class PhyFdi(unittest.TestCase):
    def test_native_main_splits_both_licensed_phy_bundles(self):
        self.check_binding()

    def test_main_preserves_already_scalarized_native_phy_ports(self):
        self.check_binding(native=True)

    def test_main_rejects_mixed_bundle_and_native_ports(self):
        with self.assertRaisesRegex(SystemExit, 'mixes bundled and native'):
            self.check_binding(mixed=True)

    def check_binding(self, native=False, mixed=False):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp); die=p/'die.v'; out=p/'bound'
            die.write_text("""module die();
  wire [0:0] refclk;
  wire [0:0] por_n;
  wire [1168:0] n_ucie;
  wire [2088:0] n_host;
  ot_qkvd_ucie_x64_phy ucie_rom (.clk(refclk[0]), .rst_n(por_n[0]), .fdi(n_ucie[1168:0]));
  ot_qfd_serdes_112g_x12_phy serdes_host (.clk(refclk[0]), .rst_n(por_n[0]), .fdi(n_host[2088:0]));
endmodule
""")
            if native:
                text=die.read_text()
                for net,fw in [('n_ucie',583),('n_host',1043)]:
                    text=text.replace(f'.fdi({net}[{2*fw+2}:0])',
                        f'.tx_up({net}[0]), .tx_v({net}[1]), .tx_flit({net}[{fw+1}:2]), '
                        f'.rx_v({net}[{fw+2}]), .rx_flit({net}[{2*fw+2}:{fw+3}])')
                die.write_text(text)
            if mixed:
                die.write_text(die.read_text().replace('.fdi(n_ucie[1168:0])',
                    '.fdi(n_ucie[1168:0]), .tx_v(n_ucie[1])'))
            for entry in B.PHY_BINDINGS.values():
                dst=p/entry['file'];dst.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(B.K.ROOT/entry['file'],dst)
            with patch.object(B,'ROOT',p), patch.object(B.PB,'ROOT',p):
                self.assertEqual(B.main([str(die),'--out-dir',str(out)]),0)
            nets,_,_,insts=B.PB.parse_die(str(out/'die_bound.v'))
            by={i:(m,c) for m,i,_,c in insts if m!='__assign__'}
            for inst,net,fw in [('ucie_rom','n_ucie',583),('serdes_host','n_host',1043)]:
                mst,ports=by[inst]
                self.assertNotIn('fdi',ports)
                self.assertEqual(set(ports),{'clk','rst_n','tx_up','tx_v','tx_flit','rx_v','rx_flit'})
                used=[]
                for pn,lo,w in [('tx_up',0,1),('tx_v',1,1),('tx_flit',2,fw),('rx_v',fw+2,1),('rx_flit',fw+3,fw)]:
                    bs=B.PB.expr_bits(ports[pn],nets)
                    self.assertEqual(list(reversed(bs)),[(net,i) for i in range(lo,lo+w)])
                    used+=bs
                self.assertEqual(len(used),2*fw+3)
                self.assertEqual(len(set(used)),len(used))
            rec=json.loads((out/'bound_netlist.json').read_text())
            self.assertTrue(all(r['how']==('identity' if native else 'bound') and r['unassigned_bits']==0 for r in rec['masters'].values()))
