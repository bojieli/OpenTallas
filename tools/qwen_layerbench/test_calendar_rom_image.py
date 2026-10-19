import unittest
from calendar_rom_image import compile_image

class CalendarImage(unittest.TestCase):
    def test_production_count_and_alignment(self):
        seg=dict(boot=[(8,1)],init=[(12,3)]*3,decode=[(1,5)]*390,head=[(2,7)]*384)
        r,w=compile_image(seg,'a'*64)
        self.assertGreater(r['entries'],511)
        self.assertEqual(r['descriptor'][0]&1023,r['entries'])
        for name in seg:
            off=r['ranges'][name]['first']
            self.assertEqual(off%4,0)
            for i,(d,c) in enumerate(seg[name]):
                j=off+i
                self.assertEqual((w[j//4]>>(128*(j%4)))&((1<<128)-1),(d<<116)|c)
    def test_refuse_truncation_and_zero_delta(self):
        seg=dict(boot=[],init=[],decode=[(1,1)]*1024,head=[])
        with self.assertRaises(ValueError):compile_image(seg,'b'*64)
        seg['decode']=[(0,1)]
        with self.assertRaises(ValueError):compile_image(seg,'b'*64)
        del seg['head']
        with self.assertRaises(ValueError):compile_image(seg,'b'*64)

if __name__=='__main__':unittest.main()
