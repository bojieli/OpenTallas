"""NEW OLD-capture/visibility tap checks; no controller/NC6 gate repeated."""
import pathlib,re,shutil,subprocess,tempfile,unittest
from tools.gpu_sys.canonical_qwen_state_tap import TOP,source_files,observer_bindings
from tools.gpu_sys.canonical_qwen_state_tap_model import model,bound
ROOT=pathlib.Path(__file__).resolve().parents[1]

class StateTapTests(unittest.TestCase):
    def rtl(self,body,observer=False,enabled=1):
        if not shutil.which('iverilog'): self.skipTest('iverilog absent')
        path=source_files(ROOT)[0]
        header=re.sub(r'//[^\n]*','',path.read_text().split(')(\n',1)[1].split('\n);',1)[0])
        ports=[];direction=None;width=''
        for token in header.split(','):
            m=re.match(r'(input|output)\s+(?:wire|reg)\s*(\[[^]]+\])?\s*(\w+)$',token.strip())
            if m: direction,width,name=m.groups();width=width or ''
            else: name=token.strip()
            ports.append((direction,width,name))
        linked={'observe_ready','ACK_ready'} if observer else set()
        declarations='\n'.join(('reg ' if d=='input' and n not in linked else 'wire ')+w+' '+n+';' for d,w,n in ports)
        initialize='\n'.join(n+'=0;' for d,w,n in ports if d=='input' and n!='clk' and n not in linked)
        extra=''
        if observer:
            extra='''reg event_ready,writer_retained;
reg [63:0] writer_identity;reg [19:0] writer_key;reg [10:0] writer_PC;
wire event_valid,event_fault,event_drained;wire [2:0] event_kind;
wire [63:0] event_identity,event_producer;wire [19:0] event_key;wire [10:0] event_PC;
ot_gpu_qwen_kv_state_observer #(.ENABLE(1)) observer(
.clk(clk),.por_n(por_n),.run_enable(run_enable),.source_bound(source_bound),
.state_base_rank0(34'h200000),.state_base_rank1(34'h100000),
'''+','.join('.'+n+'('+n+')' for n in observer_bindings())+''',
.writer_retained(writer_retained),.writer_identity(writer_identity),.writer_key(writer_key),.writer_PC(writer_PC),
.event_valid(event_valid),.event_ready(event_ready),.event_kind(event_kind),.event_identity(event_identity),
.event_producer(event_producer),.event_key(event_key),.event_PC(event_PC),.fault(event_fault),.drained(event_drained));
'''
        tb='''`timescale 1ns/1ps
module tb;
'''+declarations+'\n'+TOP+' #(.ENABLE('+str(enabled)+')) dut('+','.join('.'+n+'('+n+')' for d,w,n in ports)+');\n'+extra+'''
initial clk=0;always #5 clk=~clk;
task cmd;
begin
command_valid=1;#1;if(!command_ready)$fatal(1,"actual sector grant required");
@(negedge clk);command_valid=0;
end endtask
task old_read;
begin
caller_req_v[5]=1;caller_req_we[5]=0;raw_req_rdy[5]=1;
#1;if(!req_permit[5])$fatal(1,"OLD not permitted");
@(negedge clk);caller_req_v=0;raw_rsp_v[5]=1;caller_rsp_rdy[5]=1;
#1;if(!capture_permit[5])$fatal(1,"OLD capture not permitted");
@(negedge clk);raw_rsp_v=0;caller_rsp_rdy=0;
end endtask
task reverse_old;
begin
reverse_valid=1;reverse_write=0;#1;if(!reverse_ready)$fatal(1,"OLD reverse");
@(negedge clk);reverse_valid=0;
end endtask
task new_write;
begin
caller_req_v[5]=1;caller_req_we[5]=1;caller_req_data[5*256+:256]=observe_new_data;
#1;if(!req_permit[5] || !observe_valid)$fatal(1,"NEW actual acceptance");
@(negedge clk);caller_req_v=0;raw_wr_done_v[5]=1;caller_wr_done_rdy[5]=1;
#1;if(!capture_permit[5] || !ACK_valid || !ACK_visible)$fatal(1,"real write capture");
@(negedge clk);raw_wr_done_v=0;caller_wr_done_rdy=0;
end endtask
task reverse_new;
begin
reverse_valid=1;reverse_write=1;#1;if(!reverse_ready || !ACK_reverse)$fatal(1,"NEW reverse");
@(negedge clk);reverse_valid=0;
end endtask
initial begin
'''+initialize+'''
por_n=0;run_enable=1;repeat(2) @(negedge clk);por_n=1;
source_bound=1;command_sector_granted=1;state_client_mask=6'b100000;
command_rank=1;bus_rank=1;bus_PC=127;command_owner={7'd127,3'd5,32'hf1234567,4'd15};
command_byte_mask=32'hffffffff;command_identity=64'h1234567890abcdef;command_source_addr=34'h100000;
command_physical_addr=34'h300000000;
caller_req_addr[5*34+:34]=command_physical_addr;
caller_req_tag[5*32+:32]=32'hf1234567;caller_req_gen[5*4+:4]=15;
raw_rsp_tag=caller_req_tag;raw_wr_done_tag=caller_req_tag;
raw_rsp_gen=caller_req_gen;raw_wr_done_gen=caller_req_gen;
reverse_owner=command_owner;reverse_rank=command_rank;reverse_physical_addr=command_physical_addr;
'''+('event_ready=0;writer_retained=1;writer_identity=42;writer_key=20\'h2000;writer_PC=40;\n' if observer else 'observe_ready=1;ACK_ready=1;\n')+body+'''
$display("PASS_STATE_TAP");$finish;
end
initial begin #20000;$fatal(1,"directed test watchdog; no production service bound");end
endmodule
'''
        with tempfile.TemporaryDirectory() as directory:
            p=pathlib.Path(directory);(p/'tb.sv').write_text(tb)
            build=subprocess.run(['iverilog','-g2012','-s','tb','-o',str(p/'sim'),*(str(x) for x in source_files(ROOT)),str(p/'tb.sv')],capture_output=True,text=True)
            self.assertEqual(build.returncode,0,build.stderr)
            run=subprocess.run(['vvp',str(p/'sim')],capture_output=True,text=True)
            self.assertEqual(run.returncode,0,run.stdout+run.stderr)
            self.assertIn('PASS_STATE_TAP',run.stdout)

    def test_bitmap_actual_OLD_and_write_ACK_reverse_event_debt(self):
        self.rtl('''
command_write=1;command_byte_mask=1;command_new_data=256'h1;raw_rsp_data[5*256+:256]=256'h1000;
#1;if(req_permit[5] || capture_permit[5])$fatal(1,"unbound state permitted");
cmd();old_read();
repeat(4) @(negedge clk);if(observe_valid || reply_valid || quiescent)$fatal(1,"missing OLD reverse ignored");
reverse_old();#1;if(observe_old_data!=256'h1000)$fatal(1,"OLD was manufactured");
new_write();repeat(4) @(negedge clk);if(reply_valid || event_valid)$fatal(1,"missing NEW reverse ignored");
reverse_new();#1;
if(!reply_valid || !event_valid || event_kind!=0 || event_identity!=42 || event_key!=20'h2000)$fatal(1,"source bitmap event");
repeat(3) @(negedge clk);if(quiescent || event_drained)$fatal(1,"held reply/event dropped");
reply_ready=1;@(negedge clk);reply_ready=0;#1;
if(!quiescent || event_drained || fault || event_fault)$fatal(1,"separate event retirement");
event_ready=1;@(negedge clk);#1;if(!event_drained)$fatal(1,"event not consumed");
''',True)

    def test_acquire_byte_reply_does_not_wait_for_later_acquire_command(self):
        self.rtl('''
writer_retained=0;command_write=1;command_source_addr=34'h100000+36864;
raw_rsp_data[5*256+:256]=(256'd1<<90)|(256'd40<<77)|(256'd12<<13)|256'd7;
command_new_data=(256'd2<<90)|(256'd40<<77)|(256'd33<<13)|256'd7;
cmd();old_read();reverse_old();new_write();reverse_new();#1;
if(!reply_valid || !event_valid || event_kind!=2 || event_identity!=33 || event_producer!=12)$fatal(1,"acquire source event");
reply_ready=1;@(negedge clk);#1;
if(!quiescent || !event_valid || event_drained)$fatal(1,"acquire event not retained independently");
''',True)

    def test_read_only_returns_actual_capture_after_matched_reverse(self):
        self.rtl('''
command_write=0;raw_rsp_data[5*256+:256]=256'hfeed1234;
cmd();old_read();if(reply_valid)$fatal(1,"premature read reply");reverse_old();#1;
if(!reply_valid || reply_old_data!=256'hfeed1234 || observe_valid || ACK_valid)$fatal(1,"read only capture");
''')

    def test_wrong_return_generation_refuses_capture_retains_debt(self):
        self.rtl('''
command_write=1;cmd();caller_req_v[5]=1;raw_req_rdy[5]=1;@(negedge clk);caller_req_v=0;
raw_rsp_v[5]=1;raw_rsp_gen[5*4+:4]=0;caller_rsp_rdy[5]=1;
#1;if(capture_permit[5])$fatal(1,"stale generation permitted");
@(negedge clk);#1;if(!fault || quiescent || reply_valid)$fatal(1,"stale capture lost debt");
''')

    def test_wrong_rank_reverse_refuses_and_retains(self):
        self.rtl('''
command_write=1;cmd();old_read();reverse_valid=1;reverse_rank=0;
#1;if(reverse_ready)$fatal(1,"wrong rank reverse");
@(negedge clk);#1;if(!fault || quiescent || observe_valid)$fatal(1,"wrong reverse cleared debt");
''')

    def test_reset_pause_retains_actual_capture_and_owner(self):
        self.rtl('''
command_write=1;raw_rsp_data[5*256+:256]=256'h9876;cmd();old_read();local_reset=1;
reverse_valid=1;repeat(4) @(negedge clk);
if(reverse_ready || quiescent || reply_valid || req_permit[5])$fatal(1,"reset released debt");
local_reset=0;#1;if(!reverse_ready)$fatal(1,"matching continuation lost");
@(negedge clk);reverse_valid=0;#1;
if(observe_old_data!=256'h9876 || observe_owner!=command_owner || fault)$fatal(1,"capture reset corrupted");
''')

    def test_wrong_NEW_bytes_and_grant_absence_fail_closed(self):
        self.rtl('''
command_sector_granted=0;command_valid=1;#1;if(command_ready)$fatal(1,"ungranted admitted");
@(negedge clk);command_valid=0;command_sector_granted=1;command_write=1;command_new_data=256'habcd;
cmd();old_read();reverse_old();caller_req_v[5]=1;caller_req_we[5]=1;caller_req_data[5*256+:256]=256'habce;
#1;if(req_permit[5] || observe_valid)$fatal(1,"wrong NEW data allowed");
@(negedge clk);#1;if(!fault || quiescent)$fatal(1,"wrong data lost debt");
''')

    def test_completion_before_request_and_lost_classifier_fail_closed(self):
        self.rtl("""
command_write=1;cmd();raw_wr_done_v[5]=1;caller_wr_done_rdy[5]=1;
#1;if(capture_permit[5])$fatal(1,"early completion permitted");
@(negedge clk);#1;if(!fault || quiescent || reply_valid)$fatal(1,"early completion lost debt");
""")
        self.rtl("""
command_write=1;cmd();old_read();state_client_mask=0;
#1;if(req_permit[5] || capture_permit[5] || reverse_ready)$fatal(1,"classification loss permitted");
@(negedge clk);#1;if(!fault || quiescent)$fatal(1,"classification loss cleared debt");
""")

    def test_default_off_no_acceptance_or_success(self):
        self.rtl("""
command_valid=1;command_write=1;caller_req_v=6'b100000;raw_req_rdy=6'b111111;
repeat(3) @(negedge clk);
if(command_ready || req_permit || capture_permit || observe_valid || ACK_valid || reply_valid || reverse_ready)
 $fatal(1,"default off offers authority");
""",enabled=0)

    def test_inventory_and_positive_serial_bounds(self):
        m=model();self.assertEqual(m['raw_control_and_capture_bits'],729)
        self.assertEqual(bound(19,2,19,2,1),49)
        self.assertIsNone(m['whole_token_cycles'])
        self.assertFalse(m['rate_adopted'])
        with self.assertRaises(ValueError):bound(19,0,19,2,1)

if __name__=='__main__':unittest.main()
