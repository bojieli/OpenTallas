"""Source metadata and exhaustive 256 signed bytes; no checkpoint/inference."""
import hashlib,importlib.util,json,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from tools.gpu_sys import canonical_qwen_native_signed_i8 as M

TB='''module tb;
reg[5:0] opcode;reg[1:0] dtype,a_type,b_type,c_type;
reg a_scalar,b_scalar,c_scalar,a_signed_i8;reg[3:0] lane_mask;
reg[255:0] a_data,b_data,c_data;
wire[255:0] result,disabled_result;wire[1:0] result_type,disabled_type;
wire[3:0] lane_fault,disabled_fault;wire supported,disabled_supported;
ot_gpu_native_conversion_i8 #(.ENABLE(1)) dut(.*);
ot_gpu_native_conversion_i8 disabled(.opcode(opcode),.dtype(dtype),.a_type(a_type),.b_type(b_type),.c_type(c_type),.a_scalar(a_scalar),.b_scalar(b_scalar),.c_scalar(c_scalar),.a_signed_i8(a_signed_i8),.lane_mask(lane_mask),.a_data(a_data),.b_data(b_data),.c_data(c_data),.result(disabled_result),.result_type(disabled_type),.lane_fault(disabled_fault),.supported(disabled_supported));
integer fd,rc,bytecode,pairs,op;reg[31:0] expected_signed,expected_unsigned;
initial begin
opcode=21;dtype=0;a_type=3;b_type=1;c_type=0;a_scalar=0;b_scalar=0;c_scalar=0;
lane_mask=15;b_data=0;c_data=0;pairs=0;
fd=$fopen("VECTORS","r");if(!fd)$fatal(1,"vectors missing");
while(!$feof(fd))begin
rc=$fscanf(fd,"%d %h %h\\n",bytecode,expected_signed,expected_unsigned);
if(rc==3)begin
// Nonzero unused carrier bits must not affect the signed-byte interpretation.
a_data={4{64'h123456789abcd000 | bytecode}};a_signed_i8=1;#1;
if(!supported || result!={4{32'd0,expected_signed}} || lane_fault!=0 || result_type!=0)$fatal(1,"signed byte%0d result%h expected%h",bytecode,result,expected_signed);
if(disabled_supported || disabled_result!=0 || disabled_fault!=0)$fatal(1,"default-off");
a_signed_i8=0;#1;
if(!supported || result!={4{32'd0,expected_unsigned}})$fatal(1,"U8 alias%0d",bytecode);
pairs=pairs+1;
end else if(!$feof(fd))$fatal(1,"bad vector");
end
// Carrier mismatches refuse even though low8 contains a legal signed byte.
a_signed_i8=1;
for(op=0;op<3;op=op+1)begin a_type=op;#1;if(supported || result!=0 || lane_fault!=0)$fatal(1,"carrier mismatch");end
a_type=3;
for(op=0;op<64;op=op+1)if(op!=21)begin opcode=op;#1;if(supported || result!=0 || lane_fault!=0)$fatal(1,"profile opcode alias%0d",op);end
opcode=21;a_scalar=1;lane_mask=5;a_data=256'h80;#1;
if(result!={64'd0,64'hc3000000,64'd0,64'hc3000000})$fatal(1,"signed scalar mask");
a_scalar=0;lane_mask=15;a_data={64'h7f,64'h81,64'hff,64'h80};#1;
if(result!={64'h42fe0000,64'hc2fe0000,64'hbf800000,64'hc3000000})$fatal(1,"signed lane order");
$display("PASS I8 exhaustive256/U8distinct256/profile-carrier/opcode/defaultoff/scalar/mask");$finish;
end endmodule'''

def bits(n):
    if not n:return 0
    s=0x80000000 if n<0 else 0;n=abs(n);e=n.bit_length()-1
    return s|((e+127)<<23)|((n<<(23-e))&0x7fffff)

class SignedI8Gate(unittest.TestCase):
    def test_source_model_and_original_pins(self):
        self.assertEqual(M.compose(ROOT),json.loads((ROOT/'results/uarch/qwen_native_signed_i8_20261003/model_r1.json').read_text()))
        old=json.loads((ROOT/'results/uarch/qwen_native_conversion_20261003/gate_r1.json').read_text())
        for p in ('rtl/gpu/native/ot_gpu_native_conversion.sv','rtl/gpu/native/ot_gpu_native_conversion_abi.svh'):
            self.assertEqual(hashlib.sha256((ROOT/p).read_bytes()).hexdigest(),old['source_pins'][p])
    def test_exact_metadata_and_negative_enrollment(self):
        i8=M.i2f_profile('I8');u8=M.i2f_profile('U8')
        self.assertEqual(i8['carrier_type'],3);self.assertEqual(i8['signed_i8_mask'],1)
        self.assertEqual(u8['signed_i8_mask'],0);self.assertNotEqual(i8,u8)
        self.assertEqual(M.validate_profile(source_dtype='I8',carrier_type=3,signed_i8_mask=1,opcode=21),i8)
        for dtype,carrier,mask,op in [('I8',3,0,21),('U8',3,1,21),('I8',2,1,21),('I8',3,1,53),('I8',3,2,21),('I8',3,True,21)]:
            with self.assertRaises(ValueError):M.validate_profile(source_dtype=dtype,carrier_type=carrier,signed_i8_mask=mask,opcode=op)
        with self.assertRaises(ValueError):M.i2f_profile('I8',source_op='FP8_PACK')
        with self.assertRaises(ValueError):M.i2f_profile('INT8_guess_from_shape')
    def test_actual_signed_byte_rtl(self):
        with tempfile.TemporaryDirectory() as td:
            td=Path(td);(td/'vectors').write_text(''.join(f'{c} {bits(c if c<128 else c-256):08x} {bits(c):08x}\n' for c in range(256)))
            (td/'tb.sv').write_text(TB.replace('VECTORS',str(td/'vectors')))
            paths=['rtl/abi3/ot_a3_format_pkg.sv','rtl/gpu_sys/ot_gpu_simt_lane.sv','rtl/gpu/native/ot_gpu_native_conversion.sv','rtl/gpu/native/ot_gpu_native_conversion_i8.sv']
            subprocess.run(['iverilog','-g2012','-s','tb','-I',str(ROOT/'rtl/gpu/native'),'-o',str(td/'a.vvp'),*[str(ROOT/p) for p in paths],str(td/'tb.sv')],check=True,capture_output=True,text=True)
            out=subprocess.run(['vvp',str(td/'a.vvp')],check=True,capture_output=True,text=True)
            self.assertIn('PASS I8 exhaustive256/U8distinct256',out.stdout);print(out.stdout.strip())
if __name__=='__main__':unittest.main()
