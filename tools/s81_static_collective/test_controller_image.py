"""Synthetic minimum controller mechanism tests; no production calendar claim."""
import copy
import hashlib
from pathlib import Path
import subprocess
import tempfile
import unittest
from controller_image import *

ROOT=Path(__file__).resolve().parents[2]
RTL=ROOT/'rtl/dsrom_sys/s81_static_collective/s81_static_calendar_controller.sv'

def fixture():
    controls=lambda:dict.fromkeys([n for n,_ in FIELDS],0)
    cycles=[dict(edge=e,cmd_valid=0,cmd84=0,transport_tag=0,done_valid=0,done_tag=0,controls=controls()) for e in range(28)]
    # One gather record, seq0. Explicit source request0 ->issue14 ->gather25,
    # completion ROM27 ->registered done pin28. Data values are bench inputs.
    cmd=(1<<83)|((65536+1)<<7)|5
    cycles[0].update(cmd_valid=1,cmd84=cmd,transport_tag=0x123)
    cycles[0]['controls'].update(read_slot=1,read_row=17)
    cycles[14]['controls'].update(issue_slot=1,tag=0x123,seq=0,last=1,rankmask=15)
    cycles[25]['controls'].update(commit_slot=1,commit_tag=0x123,commit_seq=0,commit_last=1,commit_rankmask=15,commit_rows=0x1000200030004)
    cycles[27].update(done_valid=1,done_tag=133)
    return dict(abi=ABI,command_abi='opentallas.s81.cmd84.v1',latencies=LATENCIES,
                evidence=[dict(path=str(RTL.relative_to(ROOT)),sha256=hashlib.sha256(RTL.read_bytes()).hexdigest())],
                native_source_binding='synthetic component read only',vm_reservations='synthetic isolated row17',
                physical_phase_binding='synthetic oneclock component',timing_price_binding='component only28edges',
                integration_ready=False,cycles=cycles)

class Check(unittest.TestCase):
    def test_image_and_rejections(self):
        request=fixture();self.assertEqual(len(compile_image(request,ROOT)),28)
        for mutate in [lambda r:r['cycles'][14]['controls'].update(seq=1024),
                       lambda r:r['cycles'][0].update(cmd84=(1<<83)|(1025<<7)|5),
                       lambda r:r['cycles'][0]['controls'].update(read_slot=0),
                       lambda r:r['cycles'][25]['controls'].update(commit_seq=1),
                       lambda r:r['cycles'][20].update(done_valid=1,done_tag=133),
                       lambda r:r.update(physical_phase_binding=None),
                       lambda r:r['evidence'][0].update(sha256='0'*64)]:
            r=copy.deepcopy(request);mutate(r)
            with self.assertRaises(ValueError):compile_image(r,ROOT)

    def test_rtl_fixed_cycles_and_faults(self):
        with tempfile.TemporaryDirectory() as scratch:
            p=Path(scratch);emit(fixture(),ROOT,p/'calendar.mem')
            tb='''`timescale 1ns/1ps
module tb;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0;reg[84:0]c_cmd=0;wire[8:0]done;wire[1:0]st;
 wire rd,issue,commit;wire[13:0]row;wire[31:0]tag;wire busy;
 s81_static_calendar_controller #(.ROM_FILE("CALENDAR"),.CYCLES(28)) dut(
 .clk(clk),.rst_n(rst_n),.c_cmd(c_cmd),.c_done(done),.c_st(st),.datapath_fault(1'b0),
 .read_slot(rd),.read_row(row),.issue_slot(issue),.commit_slot(commit),.tag(tag),.busy(busy));
 task reset;begin @(negedge clk);rst_n=0;c_cmd=0;@(negedge clk);rst_n=1;end endtask
 integer e;reg[84:0]word;
 initial begin
 word={1'b1,1'b1,10'd0,21'd0,21'd0,24'd65537,7'd5};
 reset();
 for(e=0;e<29;e=e+1)begin
  c_cmd=(e==0)?word:0;#1;

  @(posedge clk);#1;
  if(rd!==(e==1) || issue!==(e==15) || commit!==(e==26))$fatal(1,"slot shifted %0d",e);
  if(e==1 && row!=17)$fatal(1,"row");
  if(e==15 && tag!=32'h123)$fatal(1,"tag");
  if(st[0])$fatal(1,"unexpected fault");
  if(done!==((e==28)?9'h185:9'h000))$fatal(1,"done timing %0d",e);
  @(negedge clk);
 end
 reset();c_cmd=word^85'd1;@(posedge clk);#1;@(negedge clk);c_cmd=0;@(posedge clk);#1;
 if(!st[0] || rd || issue || commit || done)$fatal(1,"bad descriptor not refused");
 reset();c_cmd=word;@(posedge clk);#1;@(negedge clk);c_cmd=word;@(posedge clk);#1;@(negedge clk);c_cmd=0;@(posedge clk);#1;
 if(!st[0] || done)$fatal(1,"unexpected pulse not refused");
 $display("PASS controller fixededge slots done descriptor/calendar fault");$finish;
 end
endmodule
'''.replace('CALENDAR',str(p/'calendar.mem'))
            (p/'tb.sv').write_text(tb)
            subprocess.run(['iverilog','-g2012','-s','tb','-o',str(p/'sim'),str(RTL),str(p/'tb.sv')],check=True,capture_output=True)
            output=subprocess.run(['vvp',str(p/'sim')],check=True,capture_output=True,text=True).stdout
            self.assertIn('PASS controller',output)
            # Observed functional mutation changes the source issue edge output.
            mutant=RTL.read_text().replace('issue_slot<=enabled ?', 'issue_slot<=1\'b0 ?')
            (p/'mut.sv').write_text(mutant)
            subprocess.run(['iverilog','-g2012','-s','tb','-o',str(p/'mut'),str(p/'mut.sv'),str(p/'tb.sv')],check=True,capture_output=True)
            result=subprocess.run(['vvp',str(p/'mut')],capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0);self.assertIn('slot shifted 15',result.stdout)

if __name__=='__main__':unittest.main()
