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

if __name__=='__main__':unittest.main()
