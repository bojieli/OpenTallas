import copy
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from dsrom_L20_native_me_matrix_provider import ReleasedMeMatrixWords,OPERATIONS,digest
import dsrom_s82_payload_interface as API

class MatrixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.matrices=[]
        with gzip.open(ROOT/'results/uarch/dsrom_s81_released_binding_20261004/canonical/matrix_map.jsonl.gz','rt') as f:
            for line in f:
                m=json.loads(line)
                if m['layer']==20 and m.get('original_alias',m['alias']) in {x[0] for x in OPERATIONS.values()}:
                    cls.matrices.append(m)
    def provider(self,node,fragment=0,rank=0):
        alias,K,rows,split,obase,xbase=OPERATIONS[node]
        matrices=[copy.deepcopy(m) for m in self.matrices if m.get('original_alias',m['alias'])==alias]
        instruction=dict(unit=1,me_k=K>>split,me_split=split,me_nout=rows,me_round=1,me_wsrc=0,
                         me_oen=1,me_obase=obase,me_xbase=xbase,me_ks=8,me_ots=8,me_ojs=1)
        dispatch=dict(source_dispatch_bound=True,fragments=[dict(stage=37,rank=rank,source_matrix_sha256=digest(m)) for m in matrices])
        execution=SimpleNamespace(source=SimpleNamespace(nodes={node:dict(instruction=instruction)},
                       resolve=lambda n,r:dict(fragments=[dict(matrix=m) for m in matrices])),
                       dispatch=lambda n,r:dispatch)
        source=SimpleNamespace(root=Path(API.SNAPSHOT),descriptor=lambda name:(None,None,dict(dtype='F8_E8M0' if name.endswith('.scale') else matrices[fragment]['source_dtype'])),
            element=lambda tensor,row,col:127 if tensor.endswith('.scale') else (0x38 if matrices[fragment]['source_dtype']=='F8_E4M3' else ((row*17+col)&65535)))
        return ReleasedMeMatrixWords(execution,source,node,rank,fragment=fragment),execution
    def test_all_six_and_two_ordered_wo_fragments_all_ranks(self):
        for node in OPERATIONS:
            for rank in range(4):
                for f in range(2 if node in ('L20.I68','L20.I69') else 1):
                    p,_=self.provider(node,f,rank)
                    self.assertEqual(p.matrix['K'],OPERATIONS[node][1])
                    self.assertEqual(p.matrix.get('row_offset',0),768*f)
                    pair=p.pairs[0];plan=next(x for x in p.matrix['plans'] if x[1]==pair)
                    row,parity=divmod(plan[5],2);macro=4*pair+parity
                    coords=API.word_coordinates(p.matrix,rank,macro,row)
                    self.assertTrue(coords)
                    if node in ('L20.I68','L20.I69'):
                        with self.assertRaisesRegex(ValueError,'host conversion forbidden'):p.read(37,rank,macro,row)
                        word=p.raw_decoder_word(37,rank,macro,row)
                        for _,_,bit,_ in coords:self.assertEqual((word>>bit)&65535,0x7f38)
                    else:
                        self.assertEqual(p.read(37,rank,macro,row),API.matrix_word(p.matrix,p.source,rank,macro,row))
    def test_rejected_controls_and_addresses(self):
        p,e=self.provider('L20.I68')
        e.source.nodes['L20.I68']['instruction']['me_round']=0
        with self.assertRaisesRegex(ValueError,'literal'):ReleasedMeMatrixWords(e,p.source,'L20.I68',0)
        for args in [(36,0,4*p.pairs[0],0),(37,1,4*p.pairs[0],0),(37,0,9668,0),(37,0,4*p.pairs[0],4096)]:
            with self.assertRaises(ValueError):p.raw_decoder_word(*args)
        p,e=self.provider('L20.I69')
        e.dispatch('L20.I69',0)['fragments'][0]['source_matrix_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'identity'):ReleasedMeMatrixWords(e,p.source,'L20.I69',0)
    def test_goodall_raw_chunk_identity_and_scale_join(self):
        p,e=self.provider('L20.I68')
        def chunk(row,k,count):
            home=API.M.physical_address(p.matrix,p.rank,row,k)
            sr,sc=home['source_row'],home['source_col']
            return dict(source_matrix_sha256=p.source_matrix_sha256,source_row=sr,
                        source_col=sc,dtype='F8_E4M3',codes=b'\x38',
                        scales=[dict(row=sr//32,col=sc//32,bits=127)])
        raw=SimpleNamespace(source_matrix_sha256=p.source_matrix_sha256,rank=0,raw_chunk=chunk)
        p=ReleasedMeMatrixWords(e,p.source,'L20.I68',0,raw_provider=raw)
        plan=p.matrix['plans'][0];physical,parity=divmod(plan[5],2)
        word=p.raw_decoder_word(37,0,4*plan[1]+parity,physical)
        self.assertEqual(word & 65535,0x7f38)
        original=raw.raw_chunk
        def bad(*args):
            c=original(*args);c['scales'][0]['col']+=1;return c
        raw.raw_chunk=bad
        with self.assertRaisesRegex(ValueError,'scale identity'):
            p.raw_decoder_word(37,0,4*plan[1]+parity,physical)

    def test_real_native_decoder_and_shared_edge_adapter(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)
            # Actual existing RTL decoder, including subnormal RNE and fault.
            (p/'tb.sv').write_text('''module tb;reg clk=0,rst_n=0,in_v=0;reg[7:0]code=0,scale=0;wire out_v,fault;wire[15:0]value;
 ot_chip_v41x_woa_fp8_decode d(.*);
 task run(input[7:0]c,s,input[15:0]expected,input f);begin
 clk=0;code=c;scale=s;in_v=1;#1;clk=1;#1;
 if(!out_v||fault!==f||(!f&&value!==expected))$fatal(1,"native decoder mismatch");end endtask
 initial begin #1;clk=1;#1;clk=0;rst_n=1;
 run(8'h38,127,16'h3f80,0);run(8'hb8,127,16'hbf80,0);
 run(8'h01,127,16'h3b00,0);run(8'h38,0,16'h0040,0);
 run(8'h38,255,0,1);run(8'h7f,127,0,1);$display("NATIVE_DECODE_PASS");$finish;end endmodule''')
            subprocess.run(['iverilog','-g2012','-s','tb','-o',str(p/'sim'),str(ROOT/'rtl/chip/ot_chip_v41x_woa_fp8_decode.sv'),str(p/'tb.sv')],check=True)
            result=subprocess.run(['vvp',str(p/'sim')],capture_output=True,text=True,check=True)
            self.assertIn('NATIVE_DECODE_PASS',result.stdout)
            # Lifecycle mock does no arithmetic; actual arithmetic checked above.
            (p/'test.cpp').write_text('''#include "s81_L20_native_me_matrix.hpp"
class VerilatedContext{};
struct Decoder{bool clk=0,rst_n=0,in_v=0,out_v=0,fault=0;unsigned code=0,scale=0,value=0;Decoder(VerilatedContext*){}void eval(){if(clk){out_v=rst_n&&in_v;fault=false;value=code;}}};
int main(){VerilatedContext c;unsigned reads=0;
 DsromL20MeNativeConversion<Decoder> d(&c,[&](unsigned,unsigned){reads++;std::array<uint32_t,9>w{};w.fill(0x7f387f38);return w;});
 auto p=d.participant();d.request(2,7);if(d.ready())return 1;
 try{d.read(2,7);return 2;}catch(const std::runtime_error&){}
 try{d.request(2,8);return 3;}catch(const std::runtime_error&){}
 p.prepare({});p.rising(true);p.falling(true);if(!d.ready()||reads!=1)return 4;
 if(d.read(2,7)[0]!=0x00380038)return 5;
 try{d.read(2,8);return 6;}catch(const std::runtime_error&){}
 try{p.rising(false);return 7;}catch(const std::runtime_error&){}
 d.retire(2,7);if(d.ready())return 8;d.request(2,8);return 0;}''')
            subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror','-I',str(ROOT/'tools/runtime/dsrom'),str(p/'test.cpp'),'-o',str(p/'test')],check=True)
            subprocess.run([str(p/'test')],check=True)
if __name__=='__main__':unittest.main()
