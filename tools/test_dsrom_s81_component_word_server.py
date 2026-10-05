import gzip
import json
import socket
import struct
import threading
import unittest

from dsrom_s81_component_word_server import ROOT, SELECTED, SelectedWord
from dsrom_s82_native_word_server import serve_connection


class ComponentWord(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with gzip.open(ROOT/SELECTED/'matrix_map.jsonl.gz','rt') as f:
            cls.matrix=json.loads(next(f))

    def test_exact_native_arguments_banks_and_parity(self):
        calls=[]
        def codec(m,c,r,macro,row):
            calls.append((m,c,r,macro,row));return (1<<273)+macro
        c=object();read=SelectedWord(self.matrix,c,codec)
        for macro in range(4):
            self.assertEqual(read(0,0,macro,0),(1<<273)+macro)
        self.assertEqual([(r,m,a) for _,_,r,m,a in calls],[(0,i,0) for i in range(4)])
        self.assertTrue(all(m is self.matrix and source is c for m,source,*_ in calls))

    def test_wrong_component_never_calls_codec(self):
        def codec(*args):
            self.fail('wrong owner must be rejected before source access')
        read=SelectedWord(self.matrix,object(),codec)
        for req in ((1,0,0,0),(0,1,0,0),(0,0,4,0),(0,0,0,4096),(0,0,0,-1)):
            with self.subTest(req=req), self.assertRaises(ValueError):read(*req)

    def test_historical_geometry_or_conversion_refused(self):
        for key,value in (('compiled_NP',2388),('conversion','FP8+UE8M0->BF16_RNE'),('format','bf16')):
            with self.subTest(key=key), self.assertRaises(ValueError):
                SelectedWord(dict(self.matrix,**{key:value}),object())

    def exchange(self,read):
        a,b=socket.socketpair();result=[]
        def worker():
            with a:result.append(serve_connection(a,read))
        t=threading.Thread(target=worker);t.start()
        with b:
            b.sendall(struct.pack('<4I',0,0,3,79))
            data=b''
            while len(data)<40:
                data+=b.recv(40-len(data))
        t.join()
        return data,result

    def test_wire_is_274bit_little_endian(self):
        value=(1<<273)+0x12345678
        data,result=self.exchange(SelectedWord(self.matrix,object(),lambda *args:value))
        self.assertEqual(data,struct.pack('<I',0)+value.to_bytes(36,'little'))
        self.assertEqual(result,[True])

    def test_source_failure_is_nonzero_status_not_usable_zero(self):
        def failure(*args):raise FileNotFoundError('missing locked shard')
        data,result=self.exchange(SelectedWord(self.matrix,object(),failure))
        self.assertEqual(struct.unpack('<I',data[:4])[0],1)
        self.assertEqual(result,[False])

    def test_oversized_codec_result_rejected(self):
        data,result=self.exchange(SelectedWord(self.matrix,object(),lambda *args:1<<274))
        self.assertEqual(struct.unpack('<I',data[:4])[0],1)
        self.assertEqual(result,[False])


if __name__=='__main__':
    unittest.main()
