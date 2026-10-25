#!/usr/bin/env python3
"""Focused proxy projection guards; no synthesis/route dependency."""
from pathlib import Path
import re
import tempfile
import unittest
import phy_line_projection as P


def native():
    ds=['input wire clk']+[f'{d} wire [{w-1}:0] bump_ucie_rom_{p}' for p,(d,w) in P.PROXY.items()]
    cs=['.clk(clk)','.rst_n(rst_n)','.tx_up(tx_up)','.tx_v(tx_v)','.tx_flit(tx_flit)','.rx_v(rx_v)','.rx_flit(rx_flit)']+[f'.{p}(bump_ucie_rom_{p})' for p in P.PROXY]
    return 'module kv3_sys_c_part (\n'+',\n'.join(ds)+'\n);\not_qkvd_ucie_x64_phy u_ucie_rom (\n'+',\n'.join(cs)+'\n);\nendmodule\n'


def wrapper():
    ds=['input wire clk']+[f'{d} wire [{w-1}:0] bump_ucie_rom_{p}' for p,(d,w) in P.PROXY.items()]
    cs=['.clk(clk)']+[f'.bump_ucie_rom_{p}(bump_ucie_rom_{p})' for p in P.PROXY]
    return 'module kv3_sys_c_part (\n'+',\n'.join(ds)+'\n);\nkv3_sys_c_part_bound u_bound (\n'+',\n'.join(cs)+'\n);\nendmodule\n'


class Projection(unittest.TestCase):
    def test_native_preserves_fdi(self):
        out,a=P.project(native());self.assertEqual(a['physical_fdi_pins'],sorted(P.FDI));self.assertNotIn('bump_ucie_rom',out)
        for pin in P.FDI:self.assertEqual(re.findall(r'\.'+pin+r'\((.*?)\)',out),re.findall(r'\.'+pin+r'\((.*?)\)',native()))
        self.assertNotRegex(out,r',\s*\);')
    def test_wrapper(self):
        out,a=P.project(wrapper(),instance='u_bound',wrapper=True);self.assertNotIn('bump_ucie_rom',out);self.assertIn('.clk(clk)',out);self.assertNotRegex(out,r',\s*\);')
    def test_unapproved_consumers(self):
        with self.assertRaises(ValueError):P.project(native()+'assign x=bump_ucie_rom_far_v;')
    def test_wrong_width(self):
        with self.assertRaises(ValueError):P.project(native().replace('[582:0] bump_ucie_rom_far_flit','[581:0] bump_ucie_rom_far_flit'))
    def test_wrong_module(self):
        with self.assertRaises(ValueError):P.project(native().replace(P.CELL,'wrong_phy'))
    def test_extra_hardpin(self):
        with self.assertRaises(ValueError):P.project(native().replace('.clk(clk)','.new_pin(clk),\n.clk(clk)'))
    def test_wrong_direct_connection(self):
        with self.assertRaises(ValueError):P.project(native().replace('.far_v(bump_ucie_rom_far_v)',".far_v(1'b0)"))
    def test_same_line_extra_connection(self):
        with self.assertRaises(ValueError):P.project(native().replace(".clk(clk),\n", "").replace(".far_v(bump_ucie_rom_far_v),\n", ".far_v(bump_ucie_rom_far_v), .clk(clk),\n"))
    def test_wrong_wrapper_module(self):
        with self.assertRaises(ValueError):P.project(wrapper().replace('kv3_sys_c_part_bound','other_bound'),instance='u_bound',wrapper=True)
    def test_filelist(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp);(d/'n.sv').write_text(native());(d/'w.sv').write_text(wrapper());(d/'a.f').write_text('n.sv\nw.sv\n')
            a=P.project_filelist(d/'a.f',d/'physical');self.assertEqual(len(a),2);self.assertTrue((d/'physical/physical_rtl.f').exists())
    def test_filelist_missing_wrapper(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp);(d/'n.sv').write_text(native());(d/'a.f').write_text('n.sv\n')
            with self.assertRaises(ValueError):P.project_filelist(d/'a.f',d/'physical')

if __name__=='__main__':unittest.main()
