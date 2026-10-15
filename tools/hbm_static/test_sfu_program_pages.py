import unittest
from sfu_program_pages import encode_planes
from sfu_control_image import pack

class ProgramTest(unittest.TestCase):
    def test_fullbatch_and_global_page_identity(self):
        for paw,count in ((1,1968),(2,3760)):
            raw=[pack(dict(i_v=(p*16)&0xffffff,co_dst=p%3,cp_imm1=(0x3f000000+p))) for p in range(count)]
            result=encode_planes(raw,paw)
            widths=result['payload_widths'];aw=10+paw;chunk=223-paw;pc_lo=234-aw
            for pc in (0,1023,1024,count-1):
                merged=0
                for stripe,width in enumerate(widths):
                    word=result['planes'][stripe][pc]
                    self.assertEqual(word>>240,0xc7a1)
                    self.assertEqual(word>>pc_lo&((1<<aw)-1),pc)
                    self.assertEqual(word>>width&((1<<(pc_lo-width))-1),0)
                    merged|=(word&((1<<width)-1))<<(stripe*chunk)
                self.assertEqual(merged,raw[pc])
            self.assertNotEqual(result['planes'][0][0]>>pc_lo,result['planes'][0][1024]>>pc_lo)

    def test_capacity_and_geometry_refuse(self):
        for page in (0,3):
            with self.assertRaises(ValueError):encode_planes([0],page)
        with self.assertRaises(ValueError):encode_planes([0]*2049,1)
        with self.assertRaises(ValueError):encode_planes([1<<1742],1)

if __name__=='__main__':unittest.main()
