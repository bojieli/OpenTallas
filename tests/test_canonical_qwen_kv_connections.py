"""Focused NEW connection RTL tests; no repeat controller or NC6 gate."""
import pathlib,re,shutil,subprocess,tempfile,unittest
from tools.gpu_sys.canonical_qwen_kv_connections import source_files,TOP
from tools.gpu_sys.canonical_qwen_kv_connections_model import model,bound,connected_model

ROOT=pathlib.Path(__file__).resolve().parents[1]
BASE=ROOT/'rtl/model/qwen_kv_connections_20261003'

def declarations(path):
    header=re.sub(r'//[^\n]*','',path.read_text().split(')(\n',1)[1].split('\n);',1)[0])
    ports=[];direction=None;width=''
    for token in header.split(','):
        token=token.strip()
        m=re.match(r'(input|output)\s+(?:wire|reg)\s*(\[[^]]+\])?\s*(\w+)$',token)
        if m:direction,width,name=m.groups();width=width or ''
        else:name=token
        ports.append((direction,width,name))
    return ports

class ConnectionTests(unittest.TestCase):
    def run_rtl(self,module,body):
        if not shutil.which('iverilog'):self.skipTest('iverilog missing')
        ports=declarations(BASE/(module+'.sv'))
        decl='\n'.join(('reg ' if d=='input' else 'wire ')+w+' '+n+';' for d,w,n in ports)
        init='\n'.join(n+'=0;' for d,w,n in ports if d=='input' and n!='clk')
        conn=','.join('.'+n+'('+n+')' for d,w,n in ports)
        tb='''`timescale 1ns/1ps
module tb;
'''+decl+'\n'+module+' #(.ENABLE(1)) dut('+conn+''');
initial clk=0;always #5 clk=~clk;
initial begin
'''+init+'''
por_n=0;run_enable=1;repeat(2) @(negedge clk);por_n=1;
'''+body+'''
$display("PASS");$finish;
end
initial begin #100000;$fatal(1,"new connection fixture watchdog");end
endmodule
'''
        with tempfile.TemporaryDirectory() as directory:
            p=pathlib.Path(directory);(p/'tb.sv').write_text(tb)
            build=subprocess.run(['iverilog','-g2012','-s','tb','-o',str(p/'sim'),*(str(n) for n in source_files(ROOT)),str(p/'tb.sv')],capture_output=True,text=True)
            self.assertEqual(build.returncode,0,build.stderr)
            run=subprocess.run(['vvp',str(p/'sim')],capture_output=True,text=True)
            self.assertEqual(run.returncode,0,run.stdout+run.stderr)
            self.assertIn('PASS',run.stdout)

    def test_shared_native_contender_and_retained_actual_destination(self):
        self.run_rtl('ot_gpu_qwen_kv_shared_router','''
kv_rank=1;kv_SM=24;kv_valid=1;kv_addr=99;kv_wdata=512'habc;
native_valid[56]=1;native_addr[560+:10]=77;service_ready[56]=1;
#1;if(kv_ready || !native_ready[56] || service_addr[560+:10]!=77) $fatal(1,"native contender");
@(negedge clk);native_valid=0;service_done[56]=1;service_rdata[56*512+:512]=512'h987;
#1;if(kv_done || !native_done[56] || drained) $fatal(1,"wrong completion owner");
repeat(3) @(negedge clk);if(kv_ready) $fatal(1,"retained native capacity");
native_done_ready[56]=1;@(negedge clk);service_done=0;native_done_ready=0;
native_valid[56]=1;#1;if(!kv_ready || native_ready[56] || service_addr[560+:10]!=99) $fatal(1,"finite alternating grant");
@(negedge clk);kv_valid=0;native_valid=0;kv_rank=0;kv_SM=0;
service_done[56]=1;#1;if(!kv_done || kv_rdata!=512'h987) $fatal(1,"current address used as accepted home");
repeat(3) @(negedge clk);if(drained || native_done[56]) $fatal(1,"early shared reuse");
kv_done_ready=1;@(negedge clk);service_done=0;#1;if(!drained || fault) $fatal(1,"shared did not drain");
''')

    def test_unowned_shared_reply_faults(self):
        self.run_rtl('ot_gpu_qwen_kv_shared_router','service_done[63]=1;@(negedge clk);if(!fault || kv_done) $fatal(1,"unowned response");')

    def test_bitmap_physical_ACK_and_reverse_precede_event(self):
        self.run_rtl('ot_gpu_qwen_kv_state_observer','''
source_bound=1;state_base_rank1=34'h100000;observe_rank=1;
observe_source_addr=34'h100000+35*1024;observe_physical_addr=34'h300000020;
observe_owner=46'h2abc12345679;observe_old_captured=1;
observe_new_data=256'h80;writer_retained=1;writer_identity=64'h8000000000000099;
writer_key=(35<<14)|(1<<13)|7;writer_PC=1600;observe_valid=1;
@(negedge clk);observe_valid=0;ACK_owner=observe_owner;ACK_physical_addr=observe_physical_addr;
ACK_valid=1;ACK_visible=1;@(negedge clk);ACK_valid=0;ACK_visible=0;
repeat(3) @(negedge clk);if(event_valid || observe_ready) $fatal(1,"missing reverse ignored");
ACK_valid=1;ACK_reverse=1;@(negedge clk);ACK_valid=0;ACK_reverse=0;
if(!event_valid || event_identity!=writer_identity || event_key!=writer_key || event_kind!=0) $fatal(1,"bitmap source decode");
repeat(3) @(negedge clk);if(drained) $fatal(1,"unconsumed metadata reused");
event_ready=1;@(negedge clk);if(!drained || fault) $fatal(1,"observer drain");
''')

    def test_metadata_wrong_protected_owner_retains_capture(self):
        self.run_rtl('ot_gpu_qwen_kv_state_observer','''
source_bound=1;state_base_rank0=34'h100000;observe_source_addr=34'h100000+37440;
observe_physical_addr=34'h300000020;observe_owner=46'h2abc12345679;observe_valid=1;
@(negedge clk);observe_valid=0;ACK_valid=1;ACK_visible=1;
ACK_owner=observe_owner^46'h10000000000;ACK_physical_addr=observe_physical_addr;
@(negedge clk);if(!fault || drained || event_valid) $fatal(1,"wrong owner retired");
''')

    def test_source_underflow_is_not_valid_state_extent(self):
        self.run_rtl('ot_gpu_qwen_kv_state_observer','''
source_bound=1;state_base_rank0=34'h100000;observe_source_addr=34'hffffe0;
observe_physical_addr=32;observe_valid=1;@(negedge clk);
if(!fault || drained) $fatal(1,"state base underflow");
'''.replace("34'hffffe0","34'hfffe0"))

    def test_connected_acquire_requires_actual_packed_record_and_old_producer(self):
        self.run_rtl(TOP,'''
source_bound=1;state_base_rank0=34'h100000;
hydrate_valid=1;hydrate_key=0;hydrate_producer=99;
@(negedge clk);hydrate_valid=0;
observe_source_addr=34'h100000+36864;observe_physical_addr=34'h300000020;
observe_owner=46'h2abc12345679;observe_old_captured=1;
observe_old_data=(256'd99<<13)|(256'd123<<77)|(256'd1<<90);
observe_new_data=(256'd777<<13)|(256'd123<<77)|(256'd2<<90);observe_valid=1;
@(negedge clk);observe_valid=0;
cmd_valid=1;cmd_op=4;cmd_identity=777;cmd_key=0;cmd_producer=99;cmd_PC=124;cmd_sequence=1;
repeat(3) @(negedge clk);if(cmd_ready || rsp_valid) $fatal(1,"acquire before physical metadata");
ACK_owner=observe_owner;ACK_physical_addr=observe_physical_addr;ACK_valid=1;ACK_visible=1;ACK_reverse=1;
@(negedge clk);ACK_valid=0;ACK_visible=0;ACK_reverse=0;
#1;if(!cmd_ready) $fatal(1,"matched actual record not admitted");
@(negedge clk);cmd_valid=0;
while(!rsp_valid && !fault) @(negedge clk);
if(fault || rsp_fault || rsp_identity!=777 || rsp_producer!=99 || rsp_op!=4 || !state_observer_drained)
 $fatal(1,"physical acquire join");
''')

    def test_native_parent_done_alone_does_not_emit_consumer(self):
        self.run_rtl('ot_gpu_qwen_kv_reader_services','''
operation_identity=777;operation_key=123;operation_owner=55'h4abc123456789a;operation_valid=1;
@(negedge clk);operation_valid=0;native_done_valid=1;native_done_owner=operation_owner;
@(negedge clk);native_done_valid=0;
repeat(4) @(negedge clk);if(consumer_valid || operation_ready || drained) $fatal(1,"reverse omitted");
native_reverse_valid=1;native_reverse_owner=operation_owner;@(negedge clk);native_reverse_valid=0;
if(!consumer_valid || consumer_identity!=777 || consumer_key!=123) $fatal(1,"consumer context lost");
consumer_ready=1;@(negedge clk);if(!drained || fault) $fatal(1,"consumer not drained");
''')

    def test_all_eight_actual_fence_replies_required(self):
        self.run_rtl('ot_gpu_qwen_kv_reader_services','''
drain_valid=1;drain_identity=64'h8000000000000777;drain_key=123;
@(negedge clk);drain_valid=0;endpoint_req_ready=255;
@(negedge clk);endpoint_req_ready=0;
endpoint_rsp_identity={8{drain_identity}};endpoint_rsp_key={8{drain_key}};
endpoint_rsp_valid=127;endpoint_rsp_quiet=127;
@(negedge clk);endpoint_rsp_valid=0;
repeat(5) @(negedge clk);if(drain_done_valid || drained) $fatal(1,"missing reverse CDC ignored");
endpoint_rsp_valid=128;endpoint_rsp_quiet=128;@(negedge clk);endpoint_rsp_valid=0;
if(!drain_done_valid || drain_done_identity!=drain_identity || drain_done_key!=123 || drain_done_allcopies!=255)
 $fatal(1,"matched whole drain");
drain_done_ready=1;@(negedge clk);if(!drained || fault) $fatal(1,"drain finish");
''')

    def test_false_fence_reply_cannot_release(self):
        self.run_rtl('ot_gpu_qwen_kv_reader_services','''
drain_valid=1;drain_identity=777;@(negedge clk);drain_valid=0;endpoint_req_ready=1;
@(negedge clk);endpoint_req_ready=0;endpoint_rsp_valid=1;endpoint_rsp_identity[63:0]=777;
endpoint_rsp_quiet=0;@(negedge clk);if(!fault || drain_done_valid || drained) $fatal(1,"false empty proof");
''')

    def test_costs_keep_unknown_and_source_counts(self):
        self.assertEqual(model()['router']['service_replicas'],64)
        self.assertEqual(connected_model()['sector_operations_per_commit'],528)
        self.assertIsNone(connected_model()['whole_token_cycles'])
        with self.assertRaises(ValueError):bound(0,19,1)
        self.assertEqual(bound(19,7,3)['shared_offer_to_capture_upper_edges'],40)

if __name__=='__main__':unittest.main()
