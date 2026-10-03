"""NEW actual root/quiet responder checks; no prior HDL gates repeated."""
import pathlib,re,shutil,subprocess,tempfile,unittest
from tools.gpu_sys.canonical_qwen_local_cohorts import TOP,source_files,endpoint_lanes
from tools.gpu_sys.canonical_qwen_local_cohorts_model import model
ROOT=pathlib.Path(__file__).resolve().parents[1]
class LocalCohortTests(unittest.TestCase):
    def rtl(self,body,enabled=1):
        if not shutil.which('iverilog'):self.skipTest('iverilog missing')
        path=source_files(ROOT)[0]
        text=path.read_text().split('module '+TOP+' ',1)[1]
        header=re.sub(r'//[^\n]*','',text.split(')(\n',1)[1].split('\n);',1)[0])
        ports=[];direction=None;width=''
        for token in header.split(','):
            m=re.match(r'(input|output)\s+(?:wire|reg)\s*(\[[^]]+\])?\s*(\w+)$',token.strip())
            if m:direction,width,name=m.groups();width=width or ''
            else:name=token.strip()
            ports.append((direction,width,name))
        decl='\n'.join(('reg ' if d=='input' else 'wire ')+w+' '+n+';' for d,w,n in ports)
        init='\n'.join(n+'=0;' for d,w,n in ports if d=='input' and n!='clk')
        tb='''`timescale 1ns/1ps
module tb;
'''+decl+'\n'+TOP+' #(.ENABLE('+str(enabled)+')) dut('+','.join('.'+n+'('+n+')' for d,w,n in ports)+''');
initial clk=0;always #5 clk=~clk;
task roots;
begin
stage_root_owner[63*55+:55]=55'h7654321;stage_root_accept[63]=1;
state_root_identity=64'hfedcba9876543210;state_root_accept=1;
#1;if(!stage_root_admit[63] || !state_root_admit)$fatal(1,"source root capacity");
@(negedge clk);stage_root_accept=0;state_root_accept=0;
end endtask
task query;
begin
request_identity=64'h80000000fedc1234;request_key=(35<<14)|(1<<13)|8191;
request_valid=3;#1;if(request_ready!=3 || stage_root_admit || state_root_admit)$fatal(1,"atomic quiesce admission");
@(negedge clk);request_valid=0;
end endtask
task retire;
begin
stage_root_retire_owner=stage_root_owner;stage_root_retire[63]=1;
state_root_retire_identity=state_root_identity;state_root_retire=1;
@(negedge clk);stage_root_retire=0;state_root_retire=0;
end endtask
initial begin
'''+init+'''
por_n=0;run_enable=1;repeat(2) @(negedge clk);por_n=1;source_bound=1;
shared_router_drained=1;shared_service_ready=64'hffffffffffffffff;
state_tap_quiescent=1;state_observer_drained=1;
'''+body+'''
$display("PASS_LOCAL_COHORTS");$finish;
end
initial begin #20000;$fatal(1,"directed test watchdog, not a service bound");end
endmodule
'''
        with tempfile.TemporaryDirectory() as directory:
            p=pathlib.Path(directory);(p/'tb.sv').write_text(tb)
            result=subprocess.run(['iverilog','-g2012','-s','tb','-o',str(p/'sim'),str(path),str(p/'tb.sv')],text=True,capture_output=True)
            self.assertEqual(result.returncode,0,result.stderr)
            result=subprocess.run(['vvp',str(p/'sim')],text=True,capture_output=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertIn('PASS_LOCAL_COHORTS',result.stdout)

    def test_actual_roots_then_receipts_empty_and_exact_held_identity(self):
        self.rtl('''
roots();query();repeat(4) @(negedge clk);
if(response_valid || roots_empty || quiesce!=3)$fatal(1,"accepted roots ignored");
metadata_event_held=1;shared_service_done[63]=1;retire();repeat(3) @(negedge clk);
if(response_valid || roots_empty!=3)$fatal(1,"held receipts ignored");
shared_service_done=0;metadata_event_held=0;@(negedge clk);#1;
if(response_valid!=3 || response_quiet!=3)$fatal(1,"actual quiet missing");
request_identity=0;request_key=0;repeat(3) @(negedge clk);
if(response_identity[0+:64]!=64'h80000000fedc1234 || response_identity[64+:64]!=64'h80000000fedc1234 ||
response_key[0+:20]!=20'h8ffff || response_key[20+:20]!=20'h8ffff || stage_root_admit || state_root_admit)
 $fatal(1,"exact response or quiesce not retained");
response_ready=3;@(negedge clk);#1;if(quiesce || !stage_root_admit[63] || !state_root_admit || fault)$fatal(1,"matched query retirement");
''')

    def test_sector_idle_not_whole_byte_RPC_retirement(self):
        self.rtl('''
roots();query();stage_root_retire_owner=stage_root_owner;stage_root_retire[63]=1;
@(negedge clk);stage_root_retire=0;repeat(4) @(negedge clk);
if(response_valid!=1 || roots_empty[1] || !quiesce[1])$fatal(1,"sector idle retired whole RPC");
metadata_reverse_held=1;state_root_retire=1;state_root_retire_identity=state_root_identity;
@(negedge clk);state_root_retire=0;repeat(2) @(negedge clk);
if(response_valid[1])$fatal(1,"metadata reverse ignored");
metadata_reverse_held=0;@(negedge clk);#1;if(response_valid!=3)$fatal(1,"matched metadata final retirement");
''')

    def test_wrong_stage_owner_and_wrong_state_identity_retain_debt(self):
        self.rtl('''
roots();query();stage_root_retire_owner=stage_root_owner^ (3520'd1<<3465);stage_root_retire[63]=1;
state_root_retire_identity=state_root_identity^64'd1;state_root_retire=1;
@(negedge clk);stage_root_retire=0;state_root_retire=0;#1;
if(!fault || roots_empty || response_valid || stage_root_admit || state_root_admit)$fatal(1,"wrong root freed");
''')

    def test_new_root_under_quiesce_faults_but_old_continuation_can_retire(self):
        self.rtl('''
roots();query();retire();@(negedge clk);stage_root_accept[0]=1;
#1;if(response_valid[0])$fatal(1,"contending new stage root received quiet");
@(negedge clk);stage_root_accept=0;#1;if(!fault || response_valid)$fatal(1,"quiesce bypass accepted");
''')

    def test_reset_keeps_all_old_roots_and_held_queries(self):
        self.rtl('''
roots();query();local_reset=1;
stage_root_retire_owner=stage_root_owner;state_root_retire_identity=state_root_identity;
stage_root_retire[63]=1;state_root_retire=1;repeat(4) @(negedge clk);
if(stage_root_retire_ready || state_root_retire_ready)$fatal(1,"paused terminal accepted");
if(roots_empty || response_valid || quiesce!=3 || stage_root_admit || state_root_admit)$fatal(1,"reset erased debt");
local_reset=0;#1;
if(!stage_root_retire_ready[63] || !state_root_retire_ready)$fatal(1,"held terminal not resumed");
@(negedge clk);stage_root_retire=0;state_root_retire=0;@(negedge clk);#1;
if(response_valid!=3 || fault)$fatal(1,"old continuation lost after pause");
''')

    def test_late_receipt_revokes_offer_before_acceptance(self):
        self.rtl('''
query();@(negedge clk);#1;if(response_valid!=3)$fatal(1,"quiet setup");
metadata_ACK_held=1;response_ready=3;#1;
if(response_valid[1] || response_quiet[1])$fatal(1,"late receipt accepted quiet");
@(negedge clk);#1;if(!fault || response_valid)$fatal(1,"late debt failed closed");
''')

    def test_invalid_source_key_refuses_quiet_and_source_loss_retains(self):
        self.rtl('''
request_identity=5;request_key=(36<<14);request_valid=3;
@(negedge clk);request_valid=0;#1;if(!fault || response_valid || quiesce!=3)$fatal(1,"invalid key succeeded");
''')
        self.rtl('''
roots();query();source_bound=0;@(negedge clk);#1;
if(!fault || roots_empty || response_valid || stage_root_admit || state_root_admit)$fatal(1,"source loss erased debt");
''')

    def test_default_off_and_inventory(self):
        self.rtl('''
request_valid=3;stage_root_accept=1;state_root_accept=1;repeat(3) @(negedge clk);
if(request_ready || response_valid || stage_root_admit || state_root_admit)$fatal(1,"default off authority");
''',enabled=0)
        self.assertEqual(model()['added_raw_bits'],3823)
        self.assertEqual(endpoint_lanes(),{'stage':0,'metadata':3})
        self.assertIsNone(model()['whole_token_upper_edges'])

if __name__=='__main__':unittest.main()
