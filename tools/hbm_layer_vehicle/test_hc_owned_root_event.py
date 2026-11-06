#!/usr/bin/env python3
import ast
from pathlib import Path
import unittest
import hc_owned_root_event as E

ROOT=Path(__file__).resolve().parents[2]

def function(path,name):
    tree=ast.parse(path.read_text())
    f=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
    ns={};exec(compile(ast.Module(body=[f],type_ignores=[]),str(path),'exec'),ns)
    return ns[name]


class EventTests(unittest.TestCase):
    def test_default_payload_and_frame_match_existing_encoders(self):
        old=function(ROOT/'tools/rtl_hbm_hc_eng_static_gate.py','word')
        frame=function(ROOT/'tools/hbm_layer_vehicle/hc_images.py','prog_rows')
        for time,npos,slot,pc in ((0,1,0,0),(1,8,3,1023),((1<<20)-1,1,1,19)):
            expected=old(time,launch=1,npos=npos,wslot=slot,eps=0x358637bd)
            self.assertEqual(E.launch_payload(time,npos=npos,wslot=slot),expected)
            self.assertEqual(E.program_word(time,npos=npos,wslot=slot,pc=pc),frame([expected],base=pc)[0])

    def test_owned_runtime_row_is_launch_only_and_one_shared_type(self):
        for row in range(24):
            word=E.launch_payload(508,global_row=row)
            self.assertEqual((word>>26)&31,row)
            self.assertEqual((word>>64)&1,1)
            self.assertEqual((word>>20)&1,0)
            self.assertEqual(E.root_parameters(global_row=row),dict(NOUT=1,WROW0=0,OROW0=-1))

    def test_unqualified_batch_and_field_overflow_rejected(self):
        for fields in (dict(global_row=-1),dict(global_row=24),dict(global_row=0,npos=2),dict(wslot=4),dict(npos=0)):
            with self.subTest(fields=fields),self.assertRaises(ValueError):E.launch_payload(1,**fields)
        with self.assertRaises(ValueError):E.launch_payload(1<<20)
        with self.assertRaises(ValueError):E.program_word(1,pc=1024)


if __name__=='__main__':unittest.main()
