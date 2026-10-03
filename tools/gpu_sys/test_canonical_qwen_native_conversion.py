"""Bounded converter gates: integer/rational bit oracles, no VM/checkpoint.

These are component simulations, not full-model inference or hardware timing.
"""
import importlib.util
import json
from pathlib import Path
import random
import shutil
import subprocess
import tempfile
import unittest
from fractions import Fraction

ROOT=Path(__file__).resolve().parents[2]
ABI=ROOT/'results/uarch/qwen_native_conversion_20261003/inputs/canonical_qwen_native_opcode_abi.py'
spec=importlib.util.spec_from_file_location('conversion_model',ROOT/'tools/gpu_sys/canonical_qwen_native_conversion.py')
model=importlib.util.module_from_spec(spec);spec.loader.exec_module(model)

# Independent integer RNE, used only to prepare component test stimuli.
def even_div(n,d):
    q,r=divmod(n,d)
    return q+int(2*r>d or (2*r==d and q&1))

def ieee(value, negative_zero=False):
    if value==0:return 0x80000000 if negative_zero else 0
    sign=0x80000000 if value<0 else 0
    v=abs(value);n,d=v.numerator,v.denominator
    e=n.bit_length()-d.bit_length()
    if (n<<max(-e,0)) < (d<<max(e,0)):e-=1
    if e < -126:
        q=even_div(n<<149,d)
        return sign | q
    shift=23-e
    q=even_div(n<<max(shift,0),d<<max(-shift,0))
    if q==1<<24:q>>=1;e+=1
    if e>127:return sign|0x7f800000
    return sign|((e+127)<<23)|(q&0x7fffff)

def rational(bits):
    exp=(bits>>23)&255;frac=bits&0x7fffff
    if exp==255:raise ValueError('nonfinite')
    sig=frac if exp==0 else (1<<23)|frac
    p=-149 if exp==0 else exp-150
    v=Fraction(sig<<max(p,0),1<<max(-p,0))
    return -v if bits>>31 else v

def fp8_value(code):
    c=code&127
    if c==127:raise ValueError('reserved')
    v=Fraction(c,512) if c<8 else Fraction(8+c%8,8)*Fraction(2)**(c//8-7)
    return -v if code&128 else v

def vectors():
    rng=random.Random(211225)
    vals=[0,1,-1,2**24+1,2**24+3,-2**24-1,-2**24-3,2**63-1,-2**63]
    vals += [rng.randrange(-2**63,2**63) for _ in range(256)]
    for v in vals:yield 21,2,1,v&((1<<64)-1),0,ieee(Fraction(v)),0
    for v in range(256):yield 21,3,1,v,0,ieee(Fraction(v)),0
    for v in [0,255,2**32-1,2**31+129]:yield 21,1,1,v,0,ieee(Fraction(v)),0
    for bits in [0,0x80000000,0x7fc00123,0x7f800000,0xff800000]:
        yield 21,0,1,bits,0,bits,0
    for bits in [0,1,0x80000000,0x3ff33333,0xbff33333,0x5effffff,0xdeffffff,0x5f000000,0xdf000000,0x7f800000,0x7fc00000]+[rng.getrandbits(32) for _ in range(256)]:
        fault=((bits>>23)&255)==255 or (bits&0x7fffffff)>=0x5f000000
        v=0 if fault else int(rational(bits))
        yield 22,0,1,bits,0,v&((1<<64)-1),int(fault)
    for bits in [0,0x80000000,1,0x80000001,0x3f800000,0x3fc00000,0x00800000,0x007fffff,0x7f7fffff]+[rng.getrandbits(32)&0xff7fffff for _ in range(128)]:
        for p in [-300,-151,-150,-149,-127,-126,-1,0,1,23,127,128,300]:
            v=rational(bits)*Fraction(2)**p
            expect=ieee(v,negative_zero=bool(bits>>31))
            yield 23,0,2,bits,p&0xffffffff,expect,int((expect&0x7f800000)==0x7f800000)
    yield 23,2,1,3,0xffffffff,0x3fc00000,0
    yield 23,1,2,0xffffffff,0x100000000,0x4f800000,0
    yield 23,3,3,2,1,0x40800000,0
    # Huge exponents are handled without constructing huge Python integers.
    for p,out,fault in [(0x7fffffff,0x7f800000,1),(0x80000000,0,0)]:
        yield 23,0,1,0x3f800000,p,out,fault
    for bits in [0x7f800000,0xff800000,0x7f800001,0xff800001,0x7fc12345]:
        yield 23,0,2,bits,0,bits|(0x400000 if bits&0x7fffff else 0),1
    for c in range(256):
        bad=(c&127)==127
        yield 25,3,1,c,0,0 if bad else ieee(fp8_value(c)),int(bad)
        if not bad:
            yield 24,0,1,ieee(fp8_value(c)),0,0 if c==128 else c,0
    # Every adjacent positive-grid midpoint, either side, both signs.
    table=[fp8_value(c) for c in range(127)]
    for c in range(126):
        mid=(table[c]+table[c+1])/2
        for v in [mid-Fraction(1,2**20),mid,mid+Fraction(1,2**20)]:
            for s in [1,-1]:
                bits=ieee(v*s);mag=abs(rational(bits))
                code=min(range(127),key=lambda i:(abs(table[i]-mag),i&1))
                yield 24,0,1,bits,0,code|(128 if s<0 and code else 0),0
    for bits,out,fault in [(0x7f7fffff,126,0),(0xff7fffff,254,0),(0x80000000,0,0),(0x7fc00000,0,1),(0xff800000,0,1)]:
        yield 24,0,1,bits,0,out,fault

TB='''
module tb;
reg [5:0] opcode; reg[1:0] dtype,a_type,b_type,c_type;
reg a_scalar,b_scalar,c_scalar; reg[3:0] lane_mask;
reg[255:0] a_data,b_data,c_data;
wire[255:0] result, off_result;wire[1:0] result_type,off_type;
wire[3:0] lane_fault,off_fault;wire supported,off_supported;
ot_gpu_native_conversion #(.ENABLE(1)) dut(.*);
ot_gpu_native_conversion off(.opcode(opcode),.dtype(dtype),.a_type(a_type),.b_type(b_type),.c_type(c_type),.a_scalar(a_scalar),.b_scalar(b_scalar),.c_scalar(c_scalar),.lane_mask(lane_mask),.a_data(a_data),.b_data(b_data),.c_data(c_data),.result(off_result),.result_type(off_type),.lane_fault(off_fault),.supported(off_supported));
integer fd,rc,id,op,at,bt,fault,count;reg[63:0] av,bv,expected;
initial begin
 dtype=0;c_type=0;a_scalar=0;b_scalar=0;c_scalar=0;lane_mask=15;c_data=0;count=0;
 fd=$fopen("VECTORS","r");if(!fd)$fatal(1,"vectors missing");
 while(!$feof(fd))begin
 rc=$fscanf(fd,"%d %d %d %d %h %h %h %d\\n",id,op,at,bt,av,bv,expected,fault);
 if(rc==8)begin
 opcode=op;a_type=at;b_type=bt;a_data={4{av}};b_data={4{bv}};#1;
 if(!supported || result!={4{expected}} || lane_fault!={4{fault[0]}})
 $fatal(1,"vector%0d op%0d a%h b%h got%h expected%h fault%b expected%0d",id,op,av,bv,result,expected,lane_fault,fault);
 if(off_supported || off_result!=0 || off_fault!=0)$fatal(1,"default-off violated");
 if(result_type!=(op==22?2:op==24?3:0))$fatal(1,"result type");count=count+1;
 end else if(!$feof(fd))$fatal(1,"bad vector");
 end
 // Every non-conversion global ID including low5 aliases must refuse.
 for(op=0;op<64;op=op+1)if(op<21 || op>25)begin
 opcode=op;#1;if(supported || result!=0 || lane_fault!=0)$fatal(1,"opcode alias%0d",op);
 end
 opcode=21;a_type=2;a_data={64'd4,64'd3,64'd2,64'd1};a_scalar=1;lane_mask=5;#1;
 if(result!={64'd0,64'h3f800000,64'd0,64'h3f800000} || lane_fault!=0)$fatal(1,"scalar mask");
 a_scalar=0;lane_mask=15;#1;
 if(result!={64'h40800000,64'h40400000,64'h40000000,64'h3f800000})$fatal(1,"lane ordering");
 opcode=22;a_type=2;#1;if(supported)$fatal(1,"F2I unsupported source type");
 opcode=23;a_type=0;b_type=0;#1;if(supported)$fatal(1,"LDEXP float exponent");
 opcode=25;a_type=0;#1;if(supported)$fatal(1,"unpack float code");
 $display("PASS conversion vectors=%0d six-bit IDs/default-off/scalar/mask/type refusals",count);$finish;
end
endmodule
'''

class ConversionGate(unittest.TestCase):
    def test_model_header_pins_and_migration_refusal(self):
        got=model.compose(ROOT,ABI)
        frozen=json.loads((ROOT/'results/uarch/qwen_native_conversion_20261003/model_r1.json').read_text())
        self.assertEqual(got,frozen)
        self.assertEqual(model.header(got),(ROOT/'rtl/gpu/native/ot_gpu_native_conversion_abi.svh').read_text())
        self.assertFalse(got['hardware_admission'])
        with tempfile.TemporaryDirectory() as td:
            bad=Path(td)/'bad.py';bad.write_text(ABI.read_text()+"\nOPCODES['I2F']=17\n")
            with self.assertRaises(ValueError):model.compose(ROOT,bad)

    def test_actual_rtl(self):
        self.assertIsNotNone(shutil.which('iverilog'))
        with tempfile.TemporaryDirectory() as td:
            td=Path(td);vs=list(vectors())
            (td/'vectors.txt').write_text(''.join(f'{i} {op} {at} {bt} {av:016x} {bv:016x} {ex:016x} {fault}\n' for i,(op,at,bt,av,bv,ex,fault) in enumerate(vs)))
            (td/'tb.sv').write_text(TB.replace('VECTORS',str(td/'vectors.txt')))
            subprocess.run(['iverilog','-g2012','-s','tb','-I',str(ROOT/'rtl/gpu/native'),'-o',str(td/'a.vvp'),str(ROOT/'rtl/abi3/ot_a3_format_pkg.sv'),str(ROOT/'rtl/gpu_sys/ot_gpu_simt_lane.sv'),str(ROOT/'rtl/gpu/native/ot_gpu_native_conversion.sv'),str(td/'tb.sv')],check=True,capture_output=True,text=True)
            run=subprocess.run(['vvp',str(td/'a.vvp')],check=True,capture_output=True,text=True)
            self.assertIn(f'PASS conversion vectors={len(vs)}',run.stdout)
            print(run.stdout.strip())

if __name__=='__main__':unittest.main()
