"""Synthetic minimum controller mechanism tests; no production calendar claim."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from controller_image import *

ROOT=Path(__file__).resolve().parents[2]
MACRO_MODEL=ROOT/'physical/asap7_memory_macros/ot_rom_4096x266_m8/ot_rom_4096x266_m8.v'
RTL=ROOT/'rtl/dsrom_sys/s81_static_collective/s81_static_calendar_controller.sv'

def fixture(consumer='gather_vm',count=1,raw=False):
    # These edges are explicit synthetic component stimuli, not a production
    # source, physical phase, native service allocation or accepted job price.
    issue_edges=[14+16*(j//3)+4*(j%3) for j in range(count)]
    final_commit=issue_edges[-1]+11
    final_write=final_commit+19
    final_emit=final_write+1
    done_edge={'gather_vm':final_commit+4,'reduce_vm':final_write+3,'reduce_vm_hc':final_emit+3}[consumer]
    blank=lambda:dict.fromkeys([n for n,_ in FIELDS],0)
    cycles=[dict(edge=e,cmd_valid=0,cmd84=0,transport_tag=0,done_valid=0,done_tag=0,controls=blank()) for e in range(done_edge+1)]
    mode=int(consumer=='gather_vm');cmd=(1<<83)|(((mode<<16)|count)<<7)|5
    cycles[0].update(cmd_valid=1,cmd84=cmd,transport_tag=0x123,consumer=consumer)
    reads=[]
    for j,issue in enumerate(issue_edges):
        read=issue-14;commit=issue+11;last=int(j==count-1)
        cycles[read]['controls'].update(read_slot=1,read_row=17+j)
        reads.append(dict(edge=read,row=17+j,consumer='tp4'))
        cycles[issue]['controls'].update(issue_slot=1,tag=0x123,seq=j,last=last,rankmask=15)
        cycles[commit]['controls'].update(commit_slot=1,commit_gather=mode,commit_tag=0x123,commit_seq=j,commit_last=last,commit_rankmask=15,
            commit_rows=sum((4096+r*64+j)<<(15*r) for r in range(4)))
        if not mode:
            cycles[commit+1]['controls'].update(hc_reduce_slot=1)
            cycles[commit+19]['controls'].update(hc_write_slot=1,hc_expect_seq=j,hc_expect_last=last)
            if consumer=='reduce_vm_hc':
                cycles[commit+19]['controls'].update(hc_assemble_slot=1,hc_word_index=j%16)
                if j%16==15:cycles[commit+20]['controls'].update(hc_emit_slot=1,hc_emit_tag=0x123)
    if raw:
        assert count==1
        for e,row,kind in [(1,100,'raw_payload'),(2,101,'raw_meta')]:
            cycles[e]['controls'].update(read_slot=1,read_row=row);reads.append(dict(edge=e,row=row,consumer=kind))
        cycles[15]['controls']['raw_capture_payload_slot']=1
        cycles[16]['controls']['raw_capture_meta_slot']=1
        cycles[18]['controls'].update(channel_tx_slot=4,channel_tx_kind=0,channel_tx_seq=9<<20,channel_tx_last=4)
        cycles[20]['controls'].update(channel_rx_slot=4,channel_rx_kind=0,channel_rx_seq=9<<20,channel_rx_last=4)
        cycles[21]['controls'].update(raw_rx_write_slot=1,raw_rx_payload_row=1234,raw_rx_meta_row=1235,raw_rx_tag=0xaa)
    cycles[done_edge].update(done_valid=1,done_tag=133)
    return dict(abi=ABI,command_abi='opentallas.s81.cmd84.v1',latencies=LATENCIES,
                evidence=[dict(path=str(RTL.relative_to(ROOT)),sha256=hashlib.sha256(RTL.read_bytes()).hexdigest())],
                native_source_binding='synthetic component read only',vm_reservations='synthetic isolated rows only',read_reservations=reads,
                physical_phase_binding='synthetic oneclock component',timing_price_binding='synthetic controller edges only',
                integration_ready=False,cycles=cycles)


def fixture_page():
    """Two synthetic controller jobs on the requested2400cycle physical page."""
    template=fixture(raw=True);request=copy.deepcopy(template)
    blank=lambda:dict.fromkeys([n for n,_ in FIELDS],0)
    request['cycles']=[dict(edge=e,cmd_valid=0,cmd84=0,transport_tag=0,done_valid=0,done_tag=0,controls=blank()) for e in range(2400)]
    request['read_reservations']=[]
    for start in (0,1200):
        for c in template['cycles']:
            row=copy.deepcopy(c);row['edge']+=start;request['cycles'][row['edge']]=row
        for item in template['read_reservations']:
            item=copy.deepcopy(item);item['edge']+=start;request['read_reservations'].append(item)
    return request

class Check(unittest.TestCase):
    def test_image_and_rejections(self):
        request=fixture(raw=True);self.assertEqual(len(compile_image(request,ROOT)),30)
        mutations=[lambda r:r['cycles'][14]['controls'].update(seq=1024),
                   lambda r:r['cycles'][0].update(cmd84=(1<<83)|(1025<<7)|5),
                   lambda r:r['cycles'][0]['controls'].update(read_slot=0),
                   lambda r:r['cycles'][25]['controls'].update(commit_seq=1),
                   lambda r:r['cycles'][20].update(done_valid=1,done_tag=133),
                   lambda r:r.update(physical_phase_binding=None),
                   lambda r:r['evidence'][0].update(sha256='0'*64),
                   lambda r:r.update(abi='opentallas.s81.collective-fixed-edge-rom.v1'),
                   lambda r:r['cycles'][0].update(consumer='reduce_vm'),
                   lambda r:r['cycles'][25]['controls'].update(commit_gather=0),
                   lambda r:r['cycles'][15]['controls'].update(raw_capture_meta_slot=1),
                   lambda r:r['read_reservations'][1].update(row=999),
                   lambda r:r.update(read_reservations=[]),
                   lambda r:r['cycles'][21]['controls'].update(raw_rx_meta_row=1234),
                   lambda r:r['cycles'][21]['controls'].update(raw_rx_write_slot=0),
                   lambda r:r['cycles'][16]['controls'].update(channel_tx_slot=4),
                   lambda r:r['cycles'][26]['controls'].update(hc_assemble_slot=1)]
        for mutate in mutations:
            r=copy.deepcopy(request);mutate(r)
            with self.assertRaises((ValueError,KeyError)):compile_image(r,ROOT)

    def test_pincap_visible_completion_and_profile(self):
        request=fixture()
        old=copy.deepcopy(request)
        old['latencies']['gather_to_vm_source_edges']=1
        with self.assertRaisesRegex(ValueError,'latency profile'):
            compile_image(old,ROOT)
        early=copy.deepcopy(request)
        early['cycles'][-1].update(done_valid=0,done_tag=0)
        early['cycles'][-2].update(done_valid=1,done_tag=133)
        with self.assertRaisesRegex(ValueError,'final scheduled output'):
            compile_image(early,ROOT)
        compile_image(request,ROOT)

    def test_reduced_word_consumers(self):
        reduced=fixture('reduce_vm');self.assertEqual(len(compile_image(reduced,ROOT)),48)
        # A single reduced word needs no16wordHCassembly consumer.
        self.assertFalse(any(c['controls']['hc_assemble_slot'] for c in reduced['cycles']))
        early=copy.deepcopy(reduced);early['cycles'][30].update(done_valid=1,done_tag=133)
        with self.assertRaises(ValueError):compile_image(early,ROOT)
        assembled=fixture('reduce_vm_hc',16);compile_image(assembled,ROOT)
        missing=copy.deepcopy(assembled);missing['cycles'][44]['controls']['hc_assemble_slot']=0
        with self.assertRaises(ValueError):compile_image(missing,ROOT)
        oversized=copy.deepcopy(reduced)
        oversized['cycles']=[reduced['cycles'][0]]*4097
        with self.assertRaisesRegex(ValueError,'4096cycle page'):compile_image(oversized,ROOT)
        wrong=copy.deepcopy(assembled);wrong['cycles'][44]['controls']['hc_word_index']=1
        with self.assertRaises(ValueError):compile_image(wrong,ROOT)

    def run_rtl(self,request,name,mutate=False,partitioned=False,clock_mutant=False):
        selected_rtl=RTL.with_name("s81_static_calendar_controller7.sv") if partitioned else RTL
        with tempfile.TemporaryDirectory() as scratch:
            p=Path(scratch);emit(request,ROOT,p/'calendar.mem');n=len(request['cycles'])
            # Icarus11 cannot parse typed string parameters. Remove only that
            # declaration keyword from the pinned physical functional model;
            # actual cell/decoder/read behavior stays byte-identical.
            macro=p/'macro.v';macro.write_text(MACRO_MODEL.read_text().replace('parameter string','parameter'))
            connections=[];offset=0
            for field,width in FIELDS:
                connections.append(f'.{field}(observed[{offset} +: {width}])');offset+=width
            tb='''`timescale 1ns/1ps
module tb;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0;reg[84:0]c_cmd=0;wire[8:0]done;wire[1:0]st,blank_st,oversize_st;wire[8:0]blank_done,oversize_done;
 wire[CB-1:0]observed;wire busy;
 reg[RW-1:0]plan[0:N-1];reg[CB-1:0]expected;reg[8:0]expected_done;
 s81_static_calendar_controller #(.ROM_FILE("CALENDAR"),.CYCLES(N)) dut(
 .clk(clk),.rst_n(rst_n),.c_cmd(c_cmd),.c_done(done),.c_st(st),.datapath_fault(1'b0),
 CONNECTIONS,.busy(busy));
 s81_static_calendar_controller blank(.clk(clk),.rst_n(rst_n),.c_cmd(c_cmd),.c_done(blank_done),.c_st(blank_st),.datapath_fault(1'b0));
 s81_static_calendar_controller #(.ROM_FILE("CALENDAR"),.CYCLES(4097)) oversize(.clk(clk),.rst_n(rst_n),.c_cmd(c_cmd),.c_done(oversize_done),.c_st(oversize_st),.datapath_fault(1'b0));
 task reset;begin @(negedge clk);rst_n=0;c_cmd=0;@(negedge clk);rst_n=1;end endtask
 integer e;reg[84:0]word;
 initial begin
 $readmemh("CALENDAR",plan);word=plan[0][CB+:85];reset();
 for(e=0;e<=2*N;e=e+1)begin
  c_cmd=(e<2*N)?plan[e%N][CB+:85]:0;
  expected=(e==0)?0:plan[(e-1)%N][0+:CB];
  expected_done=(e==0)?0:plan[(e-1)%N][CB+85+:9];
  @(posedge clk);#1;
  if(observed!==expected)$fatal(1,"control slot mismatch %0d",e);
  if(st[0])$fatal(1,"unexpected configured fault");
  if(done!==expected_done)$fatal(1,"done timing %0d",e);
  if(blank_st[1] || blank_done || (e>0 && !blank_st[0]))$fatal(1,"missing image not refused");
  if(oversize_st[1] || oversize_done || (e>0 && !oversize_st[0]))$fatal(1,"oversize physical page not refused");
  @(negedge clk);
 end
 reset();c_cmd=word^85'd1;@(posedge clk);#1;@(negedge clk);c_cmd=0;@(posedge clk);#1;
 if(!st[0] || observed || done)$fatal(1,"bad descriptor not refused");
 reset();c_cmd=word;@(posedge clk);#1;@(negedge clk);c_cmd=word;@(posedge clk);#1;@(negedge clk);c_cmd=0;@(posedge clk);#1;
 if(!st[0] || done)$fatal(1,"unexpected pulse not refused");
 $display("PASS v2 controller all468registered controls actual3ROM twopage-replays fixededge done descriptor/calendar/missingimage/oversize fault");$finish;
 end
endmodule
'''.replace('CONNECTIONS',','.join(connections)).replace('CALENDAR',str(p/'calendar.mem')).replace('CB',str(CONTROL_BITS)).replace('RW',str(ROM_BITS)).replace('N',str(n))
            # N replacement is only the standalone placeholder above; source
            # text contains no other uppercase N after CONNECTIONS substitution.
            if partitioned:
                tb=tb.replace('s81_static_calendar_controller #','s81_static_calendar_controller7 #').replace('s81_static_calendar_controller blank','s81_static_calendar_controller7 blank')
                romclocks=outclocks='{3{clk}}'
                if clock_mutant:
                    family,index=clock_mutant
                    vector=['clk','clk','clk'];vector[2-index]="1'b0"
                    stopped='{'+','.join(vector)+'}'
                    if family=='rom':romclocks=stopped
                    else:outclocks=stopped
                tb=tb.replace('.clk(clk),','.clk(clk),.clk_rom('+romclocks+'),.clk_outputs('+outclocks+'),')
            (p/'tb.sv').write_text(tb)
            subprocess.run(['iverilog','-g2012','-s','tb','-o',str(p/'sim'),str(selected_rtl),str(macro),str(p/'tb.sv')],check=True,capture_output=False)
            if clock_mutant:
                negative=subprocess.run(['vvp',str(p/'sim')],capture_output=True,text=True)
                self.assertNotEqual(negative.returncode,0)
                self.assertRegex(negative.stdout,'control slot mismatch|unexpected configured fault')
                print('PASS calendar7 stopped-clock mutant rejected',clock_mutant)
                return
            output=subprocess.run(['vvp',str(p/'sim')],check=True,capture_output=True,text=True).stdout
            self.assertIn('PASS v2 controller',output)
            mutant_output=None;macro_mutant_output=None
            if mutate:
                mutant=selected_rtl.read_text().replace('raw_rx_tag<=enabled ?', 'raw_rx_tag<=1\'b0 ?')
                self.assertNotEqual(mutant,selected_rtl.read_text());(p/'mut.sv').write_text(mutant)
                subprocess.run(['iverilog','-g2012','-s','tb','-o',str(p/'mut'),str(p/'mut.sv'),str(macro),str(p/'tb.sv')],check=True,capture_output=False)
                result=subprocess.run(['vvp',str(p/'mut')],capture_output=True,text=True)
                self.assertNotEqual(result.returncode,0);self.assertIn('control slot mismatch 22',result.stdout)
                mutant_output=result.stdout+result.stderr
                wrong_address=selected_rtl.read_text().replace('.addr_in(macro_addr)',".addr_in(macro_addr ^ 12'd1)")
                self.assertNotEqual(wrong_address,selected_rtl.read_text());(p/'macro_mut.sv').write_text(wrong_address)
                subprocess.run(['iverilog','-g2012','-s','tb','-o',str(p/'macro_mut'),str(p/'macro_mut.sv'),str(macro),str(p/'tb.sv')],check=True,capture_output=False)
                result=subprocess.run(['vvp',str(p/'macro_mut')],capture_output=True,text=True)
                self.assertNotEqual(result.returncode,0);self.assertIn('control slot mismatch 1',result.stdout)
                macro_mutant_output=result.stdout+result.stderr
            if os.environ.get('S81_CONTROLLER_EVIDENCE'):
                dest=Path(os.environ['S81_CONTROLLER_EVIDENCE']);dest.mkdir(parents=True,exist_ok=True)
                (dest/(name+'.mem')).write_bytes((p/'calendar.mem').read_bytes())
                for b in range(3):
                    (dest/(name+f'.mem.b{b}.viamap.hex')).write_bytes(Path(str(p/'calendar.mem')+f'.b{b}.viamap.hex').read_bytes())
                if n<=128:(dest/(name+'.json')).write_text(json.dumps(request,indent=2)+'\n')
                (dest/(name+'.log')).write_text(output)
                if mutate:
                    (dest/'mutant_suppressed_raw_tag.log').write_text(mutant_output)
                    (dest/'mutant_actual_macro_address.log').write_text(macro_mutant_output)

    def test_rtl_calendar7_exact_and_clock_mutant(self):
        self.run_rtl(fixture(raw=True),'calendar7_exact',partitioned=True)
        for family in ('rom','output'):
            for index in range(3):
                self.run_rtl(fixture(raw=True),'calendar7_clock_mutant',partitioned=True,clock_mutant=(family,index))

    def test_rtl_gather_and_raw_fields(self):self.run_rtl(fixture(raw=True),'gather_raw',True)
    def test_rtl_actual_2400cycle_page(self):self.run_rtl(fixture_page(),'page2400_twojobs')
    def test_rtl_reduced_word_fields(self):
        self.run_rtl(fixture('reduce_vm'),'reduce_vm')
        self.run_rtl(fixture('reduce_vm_hc',16),'reduce_vm_hc')

if __name__=='__main__':unittest.main()
