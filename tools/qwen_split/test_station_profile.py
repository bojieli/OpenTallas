"""Actual station ABI, emitted rectangles and preferred-track phase checks."""
import os
from unittest.mock import patch
from types import SimpleNamespace
import unittest
from qwen_split import station_profile as S
from qwen_split.test_fragment_pin_rectangles import die_pin_writer
from qwen_rom_fulldie import Master

class StationProfile(unittest.TestCase):
    def test_real_rectangles_and_source_abi_survive_writer(self):
        model = dict(station_profile={'qualified':False}, insts=[])
        M = {}; S.install_masters(M, model, Master)
        for name in S.MASTERS:
            wh, ports, pins, sha = S.geometry(name)
            self.assertEqual(wh, (52.68,103.656))
            self.assertEqual(sum(n for n,d in ports.values()),1547)
            emitted=die_pin_writer()(M[name],1,{p:n for p,(n,d) in ports.items()})
            actual={p.removesuffix('[0]') if ports.get(p.removesuffix('[0]'),(0,))[0]==1 else p:(L,tuple(r)) for p,L,r in emitted}
            self.assertEqual(actual,pins)
            # Vertical M5 tracks remain legal at actual R0 and MY origins.
            for pin,(layer,(x0,y0,x1,y1)) in pins.items():
                if layer != 'M5': continue
                for mirror in (False,True):
                    x=(x0+x1)/2
                    if mirror: x=wh[0]-x
                    self.assertAlmostEqual((x-.012)/.048,round((x-.012)/.048),places=6,msg=pin)

    def test_diagnostic_is_explicit_and_unknown_profile_refused(self):
        with patch.dict(os.environ,{'OT_SPLIT_STATION_PROFILE':'legacy'}):
            self.assertIsNone(S.apply({'insts':[]}))
        with patch.dict(os.environ,{'OT_SPLIT_STATION_PROFILE':'unknown'}):
            with self.assertRaises(ValueError):S.selected()
        i=SimpleNamespace(master='qfd_xcst_s',w=64.8,h=103.68)
        with patch.dict(os.environ,{'OT_SPLIT_STATION_PROFILE':'m5c_diagnostic'}):
            m={'insts':[i]};rec=S.apply(m)
        self.assertFalse(rec['qualified']);self.assertIn('FAIL',rec['native_status'])
        self.assertEqual(i.master,'qfd_xcst_s_m5');self.assertEqual(i.w,52.68)

if __name__=='__main__':unittest.main()
