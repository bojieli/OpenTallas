"""Compose the actual cursor and cached gather behind G2 burst identities."""
from pathlib import Path
import shutil
import subprocess
import pytest
ROOT=Path(__file__).resolve().parents[1]

@pytest.mark.skipif(shutil.which('iverilog') is None, reason='iverilog unavailable')
@pytest.mark.parametrize('burst', [1, 32, 512])
@pytest.mark.parametrize('resident', [0, 1])
@pytest.mark.parametrize('pass_first,compact,depth', [(0,0,80),(1,0,160),(1,1,160),(1,1,342)])
def test_transport(tmp_path, burst, resident, pass_first, compact, depth):
    rows,cols=2,53
    base,s0,s1=7,111,2
    capacity=2*(base+(cols-1)*s0+(depth-1)*s1+1)
    expected=[]
    def byte(a): return (a*17+(a>>8)*13+3)&255
    groups=(cols+7)//8
    order=[(row,p) for row in range(rows) for p in range(0,groups,3)]
    if pass_first:
        order.sort(key=lambda rp:(rp[1],rp[0]))
    for row,p in order:
        if not(compact and row>0 and min(3,groups-p)*depth<=1024):
            for k in range(depth):
                for c in range(p,min(p+3,(cols+7)//8)):
                    word=0
                    for lane in range(8):
                        if c*8+lane<cols:
                            a=2*(base+(c*8+lane)*s0+k*s1)
                            word|=(byte(a)|(byte(a+1)<<8))<<(16*lane)
                    expected.append(word)
    (tmp_path/'expected.hex').write_text(''.join(f'{w:032x}\n' for w in expected))
    total=groups*depth if resident and not pass_first else len(expected)
    bench=tmp_path/'tb.sv'
    bench.write_text(r'''
module tb;
parameter integer BURST=32,RESIDENT=0,PASS_FIRST=0,COMPACT=0;
reg clk=0;always #5 clk=~clk;
reg rst_n=0,clear=0,command_valid=0,request_valid=0;
reg [31:0] command_generation=9,command_object=13,command_service_base=32'hfffff000;
reg [63:0] command_object_bytes=11876,command_element_base=7;
reg [15:0] command_rows=2,command_cols=53,command_depth=80;
reg [31:0] command_column_stride=111,command_k_stride=2;
wire command_ready,request_ready,response_valid,read_valid,memory_ready,protocol_error,transport_drained;
reg [63:0] request_tag;
reg [31:0] request_address;
reg [9:0] request_words;
wire [63:0] response_tag,read_tag,read_offset;
wire [31:0] read_object;
wire [9:0] response_index;
wire [127:0] response_data;
wire [4:0] read_bytes;
integer ticks=0,received=0,reads=0,latency=0,checks=0;
reg pending=0,checking=1;
reg [63:0] saved_tag,saved_offset;
wire read_ready=!pending && ticks%3!=0;
wire memory_valid=pending && latency==0;
wire [63:0] memory_tag=saved_tag;
wire memory_error=0;
reg [127:0] memory_data;
wire response_ready=ticks%7<4;
reg [127:0] expected[0:1119];
integer expected_index=0;
reg [63:0] expected_tag;
ot_a3_bf16_weight_transport #(.PASS_FIRST(PASS_FIRST),.COMPACT_PASS_REUSE(COMPACT)) dut(.*);
function automatic [7:0] byte_value(input [63:0] a);byte_value=8'(a*17+(a>>8)*13+3);endfunction
always @*for(integer l=0;l<16;l=l+1)memory_data[l*8+:8]=byte_value(saved_offset+64'(l));
reg held=0;reg [201:0] payload;
always @(posedge clk)begin
 ticks<=ticks+1;if(ticks>1000000)$fatal(1,"timeout");
 if(clear || !rst_n)begin pending<=0;held<=0;end
 else begin
  if(held && (!response_valid || payload!=={response_tag,response_index,response_data}))$fatal(1,"response changed while stalled");
  held<=response_valid && !response_ready;payload<={response_tag,response_index,response_data};
  if(read_valid && read_ready)begin
   if(read_object!=command_object || read_tag[63:32]!=command_generation || read_bytes==0 || read_offset+64'(read_bytes)>command_object_bytes)$fatal(1,"read bounds/identity");
   pending<=1;saved_tag<=read_tag;saved_offset<=read_offset;latency<=2;reads<=reads+1;
  end
  if(pending && latency!=0)latency<=latency-1;
  if(memory_valid && memory_ready)pending<=0;
  if(response_valid && response_ready && checking)begin
   if(response_data!==expected[received] || response_tag!=expected_tag || response_index!=expected_index)$fatal(1,"bank fill mismatch word=%0d index=%0d",received,response_index);
   received<=received+1;expected_index<=expected_index+1;
  end
  if(checking && protocol_error)$fatal(1,"unexpected transport fault");
 end
end
task restart;
 begin
  @(negedge clk);clear=1;request_valid=0;
  @(negedge clk);clear=0;command_generation=command_generation+1;#1;
  if(!command_ready)$fatal(1,"command readiness");command_valid=1;
  @(negedge clk);command_valid=0;
 end
endtask
task send(input [31:0] address,input integer words,input bit bad_generation);
 begin
  while(!request_ready)@(negedge clk);
  request_address=address;request_words=10'(words);request_tag={command_generation,address}^(bad_generation?64'h100000000:64'd0);
  expected_tag=request_tag;expected_index=0;request_valid=1;
  @(negedge clk);request_valid=0;
 end
endtask
task fault;
 begin wait(protocol_error);repeat(150)@(negedge clk);if(!protocol_error || !transport_drained)$fatal(1,"fault did not drain");checks=checks+1;end
endtask
integer pos,count,total;
initial begin
 $readmemh("expected.hex",expected);
 repeat(2)@(negedge clk);rst_n=1;restart();
 total=RESIDENT?560:1120;
 for(pos=0;pos<total;pos=pos+count)begin
  count=total-pos<BURST?total-pos:BURST;
  send(command_service_base+32'(pos),count,0);
  wait(received==pos+count);@(negedge clk);
 end
 if(!transport_drained)$fatal(1,"completed burst not drained");checks=checks+1;
 // Resident replay stops after the first row without consuming the next row.
 checking=0;restart();send(command_service_base,0,0);fault();
 restart();send(command_service_base,1,1);fault();
 restart();send(command_service_base+1,1,0);fault();
 restart();send(command_service_base,513,0);fault();
 command_service_base=32'hfffffff0;restart();send(command_service_base,32,0);fault();
 // A burst extending past the cursor's shape must fault instead of hanging.
 command_service_base=0;command_rows=1;command_cols=8;command_depth=2;
 restart();send(0,3,0);fault();
 $display("PASS transport words=%0d checks=%0d",received,checks);$finish;
end
endmodule
'''.replace('command_object_bytes=11876',f'command_object_bytes={capacity}')
       .replace('command_depth=80',f'command_depth={depth}')
       .replace("command_service_base=32'hfffff000", "command_service_base=32'hffff0000")
       .replace('expected[0:1119]',f'expected[0:{len(expected)-1}]')
       .replace('total=RESIDENT?560:1120;',f'total={total};'))
    sim=tmp_path/'sim'
    sources=['ot_a3_weight_layout_cursor','ot_a3_bf16_weight_gather','ot_a3_bf16_weight_transport']
    subprocess.run(['iverilog','-g2012','-s','tb',f'-Ptb.BURST={burst}',f'-Ptb.RESIDENT={resident}','-o',str(sim),
                    f'-Ptb.PASS_FIRST={pass_first}',f'-Ptb.COMPACT={compact}',
                    *[str(ROOT/'rtl/abi3'/f'{s}.sv') for s in sources],str(bench)],check=True,capture_output=True,text=True)
    r=subprocess.run(['vvp',str(sim)],cwd=tmp_path,capture_output=True,text=True,timeout=60)
    assert r.returncode==0,r.stdout+r.stderr
    assert f'PASS transport words={total} checks=7' in r.stdout
