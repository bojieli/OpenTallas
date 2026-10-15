"""Check the current Q-LINK header against every generated compute endpoint."""
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from qwen_split import static_link_bind as B

@dataclass
class Inst:
    name: str
    master: str
    x: float=0
    y: float=0
    w: float=43.176
    h: float=43.176
    orient: str='R0'
    kind: str='link'
    region: str='io'
    domain: str='stream'

class CurrentLinkAbi(unittest.TestCase):
    def test_source_scalar_root_and_shared_rx_word(self):
        source=B.ROOT/B.SOURCE
        self.assertTrue(source.is_file(), 'actual current Q-LINK source required')
        model=dict(insts=[Inst('d2d_rom','qfd_d2d_rom'),Inst('native59','native59'),Inst('ucie_kv','phy',1000,1000),Inst('x3_mux','old')],
                   buses=[('clk','clock_trunk',1,[('pll','clk'),('d2d_rom','ck')]),('rst','reset',1,[('root','rst'),('d2d_rom','rst_n')])])
        rec=B.apply(model)
        ends=[p for _,_,_,es in model['buses'] for i,p in es if i=='d2d_rom']
        self.assertIn('ck',ends)
        self.assertNotIn('ck0',ends)
        self.assertIn('rx_payload',ends)
        self.assertNotIn('native_rx_payload',ends)
        self.assertIn('cal_seg',rec['open_inputs'])
        self.assertFalse(rec['qualified'])
        self.assertEqual(len(ends),len(set(ends)))
        self.assertNotIn('x3_mux',[i.name for i in model['insts']])

    def test_actual_source_phy_and_bumps_are_present_and_missing_hook_is_refused(self):
        from qwen_rom_fulldie import Master
        from qwen_split.direct_up4 import partition_master
        model = dict(insts=[Inst('d2d_rom','qfd_d2d_rom',w=777.6,h=518.4),
                            Inst('native59','native59',x=100,y=1000),
                            Inst('ucie_kv','phy',x=1000,y=1000)],
                     buses=[('clk','clock_trunk',1,[('pll','clk'),('d2d_rom','ck')]),
                            ('rst','reset',1,[('root','rst'),('d2d_rom','rst_n')])])
        B.apply(model)
        # A graph-only source swap used to reach OpenROAD without its actual
        # physical-master hook, then fail on bump_fwd_epoch/qfd_sigbump.
        with self.assertRaisesRegex(ValueError,'physical master contract: missing='):
            B.validate_case_masters({}, model)
        masters = {}
        B.install_masters(masters,model,Master,partition_master)
        self.assertEqual(set(masters),{B.MASTER,B.BUMP,'ot_qkvd_ucie_x64_phy'})
        self.assertEqual(set(masters[B.MASTER].ports),set(B.rtl_ports(B.ROOT/B.SOURCE,B.MASTER)))
        self.assertEqual(masters['ot_qkvd_ucie_x64_phy'].ports['rx_flit'][1],583)
        masters['ot_qkvd_ucie_x64_phy'].ports['rx_flit'] = ('pins', 1043,'N','M5',[],1)
        with self.assertRaisesRegex(ValueError,'rx_flit needs 583'):
            B.validate_case_masters(masters,model)

if __name__=='__main__':unittest.main()
