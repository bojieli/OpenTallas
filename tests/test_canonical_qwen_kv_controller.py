"""Controller-only RTL fixtures; never full NC6 or physical timing evidence."""
import pathlib
import re
import shutil
import subprocess
import tempfile
import unittest
from tools.gpu_sys.canonical_qwen_kv_controller_model import model, price_local
from tools.gpu_sys.canonical_qwen_kv_controller import KVControllerPort
from tools.gpu_sys.canonical_qwen_transport import TransportError, PROGRAM_SHA

ROOT = pathlib.Path(__file__).resolve().parents[1]
RTL = ROOT / 'rtl/model/qwen_kv_lifecycle_20261003/ot_gpu_qwen_kv_lifecycle_controller.sv'


def bench(body, corrupt=False, enable=1):
    header = RTL.read_text().split(')(\n', 1)[1].split('\n);', 1)[0]
    header = re.sub(r'//[^\n]*', '', header)
    direction, width = None, ''
    ports = []
    for token in header.split(','):
        token = token.strip()
        match = re.match(r'(input|output)\s+(?:wire|reg)\s*(\[[^]]+\])?\s*(\w+)$', token)
        if match:
            direction, width, name = match.groups()
            width = width or ''
        else:
            name = token
        ports.append((direction, width, name))
    declarations = '\n'.join(('reg' if d == 'input' else 'wire')+' '+w+' '+n+';' for d,w,n in ports)
    init = '\n'.join(n+'=0;' for d,w,n in ports if d=='input' and n!='clk')
    connections = ','.join('.'+n+'('+n+')' for d,w,n in ports)
    return f'''`timescale 1ns/1ps
module tb;
{declarations}
ot_gpu_qwen_kv_lifecycle_controller #(.ENABLE({enable})) dut({connections});
initial clk=0; always #5 clk=~clk;
reg [511:0] scratch[0:1023]; reg [1:0] pending;
integer j;
// Explicit test SRAM acceptance/capture, not production ready/fence ties.
always @(posedge clk) begin
 if(!por_n) begin pending<=0; shared_done<=0; end
 else begin
  if(shared_done && shared_done_ready) shared_done<=0;
  if(shared_valid && shared_ready) begin
   if(shared_write) begin scratch[shared_addr]<=shared_wdata; shared_done<=1; end
   else begin shared_rdata<=scratch[shared_addr] ^ 512'd{int(corrupt)}; pending<=1; end
  end
  if(pending!=0) begin pending<=0; shared_done<=1; end
 end
end
always @* shared_ready=por_n && !shared_done && pending==0;
task offer(input [2:0] kind,input [63:0] identity,input [19:0] k);
 begin @(negedge clk); cmd_op=kind; cmd_identity=identity; cmd_key=k;
 cmd_sequence=cmd_sequence+1; cmd_valid=1;
 #1; while(!cmd_ready) begin @(negedge clk); #1; end
 @(negedge clk); cmd_valid=0;
 end
endtask
task response;
 begin while(!rsp_valid && !fault) @(negedge clk);
 if(fault || rsp_fault) $fatal(1,"unexpected fault");
 if(rsp_identity!=cmd_identity || rsp_op!=cmd_op || rsp_key!=cmd_key || rsp_sequence!=cmd_sequence)
  $fatal(1,"identity");
 rsp_ready=1; @(negedge clk); rsp_ready=0;
 end
endtask
task begin_writer;
 begin offer(0,64'd99,20'd0); response(); end
endtask
task stages;
 begin for(j=0;j<16;j=j+1) begin
 cmd_stage_beat=j; cmd_stage_data={{64{{j[7:0]}}}};
 offer(1,64'd99,20'd0); response();
 if(rsp_capture!={{64{{j[7:0]}}}}) $fatal(1,"readback"); end end
endtask
task payloads;
 integer transaction, index, k;
 reg is_write; reg [33:0] address; reg [255:0] data, expected;
 begin for(transaction=0;transaction<528;transaction=transaction+1) begin
 while(!payload_req_valid) @(negedge clk);
 index=payload_req_sector; is_write=payload_req_write;
 address=payload_req_source_addr; data=payload_req_data;
 if(is_write) begin
  if(index<256) begin
   expected={{32{{8'haa}}}};
   expected[7:0]=index>>5; expected[135:128]=index>>5;
  end else begin expected=0; for(k=0;k<32;k=k+1) expected[k*8+:8]=8+((index-256)>>1); end
  if(data!==expected) $fatal(1,"actual staged byte merge/old tail index %0d",index);
 end
 repeat(2) @(negedge clk);
 if(!payload_req_valid || payload_req_sector!=index || payload_req_source_addr!=address || payload_req_write!=is_write)
   $fatal(1,"request changed under backpressure");
 payload_req_ready=1; @(negedge clk); payload_req_ready=0;
 payload_valid=1; payload_identity=99; payload_key=0; payload_sector=index;
 payload_source_addr=address; payload_write=is_write;
 payload_rdata={{32{{8'haa}}}}; payload_visible=1; payload_reverse=0;
 @(negedge clk); payload_valid=0; payload_visible=0;
 repeat(2) @(negedge clk);
 payload_valid=1; payload_reverse=1;
 @(negedge clk); payload_valid=0; payload_reverse=0;
 end end
endtask
task commit_writer;
 begin offer(2,99,0);
 while(!commit_valid) @(negedge clk);
 repeat(3) @(negedge clk);
 if(rsp_valid) $fatal(1,"commit before accept");
 commit_ready=1; @(negedge clk); commit_ready=0;
 payloads(); response(); end
endtask
task publish_writer;
 begin offer(3,99,0);
 repeat(3) @(negedge clk);
 if(rsp_valid) $fatal(1,"publish without metadata");
 metadata_valid=1; metadata_identity=99; metadata_key=0; metadata_record=0;
 @(negedge clk); metadata_record=1;
 @(negedge clk); metadata_valid=0;
 response(); if(writer_retained) $fatal(1,"writer held after publish"); end
endtask
task consume(input bit stage);
 begin cmd_consumer=stage; offer(5,777,0);
 repeat(3) @(negedge clk);
 if(rsp_valid) $fatal(1,"consumer always-ready");
 consumer_valid=1; consumer_identity=777; consumer_key=0; consumer_stage=stage;
 consumer_accepted=1; consumer_reverse=0;
 @(negedge clk); consumer_valid=0; consumer_accepted=0;
 repeat(3) @(negedge clk);
 if(rsp_valid) $fatal(1,"missing reverse");
 consumer_valid=1; consumer_reverse=1;
 @(negedge clk); consumer_valid=0; consumer_reverse=0;
 response();
 reader_metadata_valid=1; reader_metadata_identity=777; reader_metadata_key=0;
 reader_metadata_stage=stage; @(negedge clk); reader_metadata_valid=0;
 end
endtask
initial begin
{init}
cmd_stage_base=100; cmd_K_base=34'h100000; cmd_V_base=34'h1000000;
pending=0; por_n=0; run_enable=1;
repeat(2) @(negedge clk); por_n=1;
{body}
$display("PASS"); $finish;
end
initial begin #500000; $fatal(1,"fixture watchdog"); end
endmodule
'''


class ControllerRTLTests(unittest.TestCase):
    def run_case(self, body, **kwargs):
        if not shutil.which('iverilog'):
            self.skipTest('iverilog unavailable')
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory)
            (path/'tb.sv').write_text(bench(body, **kwargs))
            compile = subprocess.run(['iverilog','-g2012','-s','tb','-o',str(path/'sim'),str(RTL),str(path/'tb.sv')], capture_output=True, text=True)
            self.assertEqual(compile.returncode,0,compile.stderr)
            run = subprocess.run(['vvp',str(path/'sim')], capture_output=True, text=True, timeout=20)
            self.assertEqual(run.returncode,0,run.stdout+run.stderr)
            self.assertIn('PASS',run.stdout)

    def test_complete_with_physical_backpressure_and_separate_reverse(self):
        self.run_case('''begin_writer(); stages(); commit_writer(); publish_writer();
cmd_producer=99; offer(4,777,0); response(); if(idle) $fatal(1,"live reader marked idle"); consume(0); consume(1);
offer(6,777,0); while(!drain_valid) @(negedge clk);
repeat(4) @(negedge clk); if(rsp_valid) $fatal(1,"early drain");
drain_ready=1; @(negedge clk); drain_ready=0;
repeat(4) @(negedge clk); if(rsp_valid) $fatal(1,"missing drain receipt");
drain_done_valid=1; drain_done_identity=777; drain_done_key=0; drain_done_allcopies=255;
@(negedge clk); drain_done_valid=0; response();
if(dut.reader_live[0]) $fatal(1,"reader retained");''')

    def test_incomplete_staging_cannot_commit(self):
        self.run_case('begin_writer(); offer(2,99,0); repeat(4) @(negedge clk); if(!fault || !writer_retained) $fatal(1,"incomplete commit");')

    def test_old_sector_wrong_identity_is_not_completion(self):
        self.run_case('''begin_writer(); stages(); offer(2,99,0);
while(!commit_valid) @(negedge clk); commit_ready=1; @(negedge clk); commit_ready=0;
while(!payload_req_valid) @(negedge clk); payload_req_ready=1; @(negedge clk); payload_req_ready=0;
payload_valid=1; payload_identity=98; payload_sector=0; payload_source_addr=cmd_K_base; payload_visible=1;
repeat(3) @(negedge clk); if(!fault || !writer_retained) $fatal(1,"wrong writer");''')

    def test_physical_source_address_mismatch(self):
        self.run_case('''begin_writer(); stages(); offer(2,99,0);
while(!commit_valid) @(negedge clk); commit_ready=1; @(negedge clk); commit_ready=0;
while(!payload_req_valid) @(negedge clk); payload_req_ready=1; @(negedge clk); payload_req_ready=0;
payload_valid=1; payload_identity=99; payload_sector=0; payload_source_addr=cmd_K_base+32; payload_visible=1;
repeat(3) @(negedge clk); if(!fault || !writer_retained) $fatal(1,"wrong source sector");''')

    def test_metadata_record_before_bitmap_refused(self):
        self.run_case('''begin_writer(); stages(); commit_writer();
metadata_valid=1; metadata_identity=99; metadata_record=1;
repeat(3) @(negedge clk); if(!fault || !writer_retained) $fatal(1,"metadata order");''')

    def test_real_sram_readback_corruption_refused(self):
        self.run_case('''begin_writer(); cmd_stage_data=512'd42; offer(1,99,0);
while(!fault) @(negedge clk); if(!writer_retained || dut.stage_mask!=0) $fatal(1,"bad capture retired");''',corrupt=True)

    def test_partial_allcopy_drain_refused(self):
        self.run_case('''begin_writer(); stages(); commit_writer(); publish_writer();
cmd_producer=99; offer(4,777,0); response(); consume(0); consume(1);
offer(6,777,0); while(!drain_valid) @(negedge clk); drain_ready=1;
@(negedge clk); drain_ready=0; drain_done_valid=1;
drain_done_identity=777; drain_done_key=0; drain_done_allcopies=127;
repeat(3) @(negedge clk); if(!fault || !dut.reader_live[0]) $fatal(1,"partial drain retired");''')

    def test_quiesce_does_not_erase_entering_lease(self):
        self.run_case('''begin_writer(); quiesce=1; repeat(5) @(negedge clk);
if(cmd_ready || !writer_retained || idle) $fatal(1,"quiesce debt lost");''')

    def test_quiesce_allows_actual_writer_continuation(self):
        self.run_case('begin_writer(); quiesce=1; stages(); commit_writer(); publish_writer(); if(!idle) $fatal(1,"quiesce cannot drain");')

    def test_component_default_off(self):
        self.run_case('cmd_valid=1; repeat(5) @(negedge clk); if(cmd_ready || shared_valid || commit_valid || rsp_valid) $fatal(1,"not default off");',enable=0)

    def test_duplicate_consumer_callback_cannot_reuse_receipt(self):
        self.run_case("""begin_writer(); stages(); commit_writer(); publish_writer();
cmd_producer=99; offer(4,777,0); response(); consume(0);
cmd_consumer=0; offer(5,777,0); repeat(4) @(negedge clk);
if(!fault || !dut.reader_live[0]) $fatal(1,"duplicate consumer");""")

    def test_stale_reverse_drain_identity_retains_owner(self):
        self.run_case("""begin_writer(); stages(); commit_writer(); publish_writer();
cmd_producer=99; offer(4,777,0); response(); consume(0); consume(1);
offer(6,777,0); while(!drain_valid) @(negedge clk); drain_ready=1;
@(negedge clk); drain_ready=0; drain_done_valid=1;
drain_done_identity=776; drain_done_key=0; drain_done_allcopies=255;
repeat(3) @(negedge clk); if(!fault || !dut.reader_live[0]) $fatal(1,"stale reverse");""")

    def test_prospective_price_requires_positive_all_external_terms(self):
        with self.assertRaises(ValueError):
            price_local({})
        service = {k: 11 for k in ('shared_write', 'shared_read', 'payload_partial_read',
                    'payload_write_visible_reverse', 'metadata_visible',
                    'SCORES_accepted_reverse', 'PV_accepted_reverse', 'allcopy_drain')}
        priced = price_local(service)
        self.assertEqual(priced['commit_edges'],4+(16+256+272)*11)
        self.assertFalse(priced['headline_adopted'])
        service['allcopy_drain']=0
        with self.assertRaises(ValueError):
            price_local(service)

    def test_raw_inventory_matches_actual_sequential_declarations(self):
        source=RTL.read_text()
        header=source.split(')(\n',1)[1].split('\n);',1)[0]
        count=0
        for width, name in re.findall(r'output reg\s*(\[[^]]+\])?\s*([^,\n]+)',header):
            count += int(width[1:-1].split(':')[0])+1 if width else 1
        for width,names in re.findall(r'\breg\s*(\[\d+:\d+\])?\s*([^;]+);',source.split('\n);',1)[1]):
            bits=int(width[1:-1].split(':')[0])+1 if width else 1
            for name in names.split(','):
                array=re.search(r'\[(\d+):(\d+)\]',name)
                count+=bits*(abs(int(array[1])-int(array[2]))+1 if array else 1)
        self.assertEqual(count,model()['raw_control_bits'])

    def test_callbacks_drive_actual_rtl_staging_and_readback(self):
        # A console around the real RTL, with the same explicit test SRAM as
        # the directed gate. No Python implementation of controller state.
        header=re.sub(r'//[^\n]*','',RTL.read_text().split(')(\n',1)[1].split('\n);',1)[0])
        inputs=[]; names=[]; direction=None
        for token in header.split(','):
            token=token.strip()
            match=re.match(r'(input|output)\s+(?:wire|reg)\s*(?:\[[^]]+\])?\s*(\w+)$',token)
            if match:
                direction,name=match.groups()
            else:
                name=token
            names.append(name)
            if direction=='input': inputs.append(name)
        assigns=' '.join(str(names.index(n))+': '+n+'=value;' for n in inputs)
        reads=' '.join(str(i)+': $display("PORT %h",'+n+');' for i,n in enumerate(names))
        body="""begin: rpc
integer operation, index, count; reg [511:0] value;
while(1) begin
 count=$fscanf(32'h80000000,"%d %d %h",operation,index,value);
 if(count!=3) $finish;
 case(operation)
  0: begin case(index) ASSIGNS endcase #0; $display("PORT 0"); end
  1: begin #0; case(index) READS endcase end
  2: begin @(negedge clk); $display("PORT 0"); end
  3: $finish;
 endcase
 $fflush();
end
end""".replace('ASSIGNS',assigns).replace('READS',reads)
        with tempfile.TemporaryDirectory() as directory:
            path=pathlib.Path(directory); (path/'tb.sv').write_text(bench(body))
            subprocess.run(['iverilog','-g2012','-s','tb','-o',str(path/'sim'),str(RTL),str(path/'tb.sv')],check=True,capture_output=True)
            process=subprocess.Popen(['vvp',str(path/'sim')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True)
            self.addCleanup(process.stdout.close); self.addCleanup(process.stdin.close)
            class Ports:
                def parameter(self,k): return 1 if k=='ENABLE' else None
                def exchange(self,op,index=0,value=0):
                    process.stdin.write(f'{op} {index} {value:x}\n'); process.stdin.flush()
                    line=process.stdout.readline()
                    if not line.startswith('PORT '): raise AssertionError(line)
                    return int(line.split()[1],16)
                def set(self,k,v): self.exchange(0,names.index(k),v)
                def get(self,k): return self.exchange(1,names.index(k))
                def tick(self): self.exchange(2)
                def settle(self): pass
            class Source:
                def kv_controller_source(self,request):
                    return dict(stage_base=100,stage_SM=3,K_base=0x100000,V_base=0x1000000,stage_lease_retained=True)
            ports=Ports(); control=KVControllerPort(ports,Source())
            try:
                request=dict(program_sha256=PROGRAM_SHA,source_PC=40,sequence=0,tag=99,key=[0,0,0])
                result=control.handlers['kv_begin'](request)
                self.assertTrue(result['writer_retained'])
                raw=bytes(range(128))
                request.update(sequence=1,payload=raw,addresses=[0x100000+d*16 for d in range(128)])
                result=control.handlers['kv_stage_write'](request)
                import hashlib
                self.assertEqual(result['payload_sha256'],hashlib.sha256(raw).hexdigest())
                self.assertEqual(ports.get('shared_SM'),3)
                self.assertEqual(ports.get('writer_retained'),1)
                # Missing real remaining stage beats fails in hardware rather
                # than turning a Python bytes count into a successful commit.
                request.update(sequence=2,bytes=1024)
                with self.assertRaisesRegex(TransportError,'controller fault'):
                    control.handlers['kv_commit'](request)
                self.assertEqual(ports.get('writer_retained'),1)
            finally:
                process.stdin.write('3 0 0\n'); process.stdin.flush(); process.wait()

    def test_reader_does_not_require_retired_writer_stage_lease(self):
        class Ports:
            def parameter(self,k): return 1
        class Source:
            def kv_controller_source(self,request):
                return dict(stage_base=100,stage_SM=3,K_base=0x100000,V_base=0x1000000,stage_lease_retained=False)
        control=KVControllerPort(Ports(),Source())
        request=dict(program_sha256=PROGRAM_SHA,source_PC=40,sequence=10,key=[0,0,0])
        self.assertEqual(control._source(request,needs_stage=False)['stage_SM'],3)
        with self.assertRaises(TransportError): control._source(request,needs_stage=True)

    def test_model_preserves_unknown_external_service(self):
        m=model()
        self.assertEqual(m['stage_physical_bytes'],1024)
        self.assertEqual(m['added_SRAM_bytes'],0)
        self.assertEqual(m['reader_rows'],72)
        self.assertEqual(m['payload_sector_writes'],272)
        self.assertTrue(all(v is None for v in m['external_bounds'].values()))
        self.assertFalse(m['physical_clock_qualified'])

if __name__ == '__main__':
    unittest.main()
