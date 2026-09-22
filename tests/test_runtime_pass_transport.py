"""Compose runtime credits, pass banks and actual strided BF16 object reads."""
from pathlib import Path
import shutil
import subprocess
import pytest
ROOT=Path(__file__).resolve().parents[1]

@pytest.mark.skipif(shutil.which('iverilog') is None,reason='iverilog unavailable')
@pytest.mark.parametrize('depth',[160,342])
@pytest.mark.parametrize('reuse',[0,1])
def test_runtime_pass_transport(tmp_path,depth,reuse):
    rows,cols,groups=3,53,7
    stride=depth*2+5; capacity=2*(11+52*stride+(depth-1)*2+1)
    def byte(a):return (a*17+(a>>8)*13+3)&255
    req=[];words=[];fetches=0
    for p in range(0,groups,3):
        count=min(3,groups-p)*depth
        fetches+=count if reuse and count<=1024 else count*rows
        for row in range(rows):
            for k in range(depth):
                for col in range(p,min(p+3,groups)):
                    req.append((10+row*depth+k,20+(row//2)*(depth//2)+k//2,
                                30+col*(depth//2)+k//2,100+len(req)))
                    word=0
                    for lane in range(8):
                        if col*8+lane<cols:
                            a=2*(11+(col*8+lane)*stride+k*2)
                            word|=(byte(a)|(byte(a+1)<<8))<<(16*lane)
                    words.append(word)
    (tmp_path/'req.hex').write_text(''.join(f'{a:08x}{s:08x}{ws:08x}{w:08x}\n' for a,s,ws,w in req))
    (tmp_path/'words.hex').write_text(''.join(f'{w:032x}\n'for w in words))
    bench=tmp_path/'tb.sv'
    bench.write_text(r'''module tb;
localparam integer DEPTH=DVAL,TOTAL=TVAL,REUSE=RVAL;
reg clk=0;always #5 clk=~clk;
reg rst_n=0,clear=0,command_valid=0;
wire command_ready,transport_ready,busy,geometry_error,protocol_error,transport_error;
integer ticks=0,issued=0,delivered=0,fills=0;
reg [127:0] req[0:TOTAL-1],expected[0:TOTAL-1];
wire [127:0] address=req[issued<TOTAL?issued:0];
wire operand_request=busy && issued<TOTAL;
wire credit;wire issue=credit && ticks%7<5;
wire [63:0] a_data,ws_data;wire [31:0] s_data;wire [127:0] w_data;
wire wvalid,wready,rvalid,rready;wire [63:0] wtag,rtag;
wire [31:0] waddress;wire [9:0] wwords,rindex;wire [127:0] rdata;
wire auxvalid,auxready,auxrspready;reg auxrsp=0;
wire [31:0] auxgen,auxa,auxs,auxws,auxw;
reg [31:0] savedgen,saveda,saveds,savedws,savedw;
assign auxready=!auxrsp && ticks%5!=0;
ot_a3_lq8_runtime_operands #(.PASS_FIRST(1),.REUSE_WEIGHT_ROWS(REUSE)) service(
.clk(clk),.rst_n(rst_n),.clear(clear),.command_valid(command_valid),.command_ready(command_ready),
.cfg_generation(32'd7),.cfg_rows(16'd3),.cfg_cols(16'd56),.cfg_depth(16'(DEPTH)),.cfg_group(8'd1),
.cfg_scale_a(1'b1),.cfg_scale_b(1'b1),.cfg_block_a(16'd2),.cfg_block_b(16'd2),.cfg_block_rows_a(16'd2),
.cfg_a_base(32'd10),.cfg_s_base(32'd20),.cfg_ws_base(32'd30),.cfg_w_base(32'd100),
.compute_admitted(1'b1),.operand_request(operand_request),.operand_issue(issue),
.operand_a(address[127:96]),.operand_s(address[95:64]),.operand_ws(address[63:32]),.operand_w(address[31:0]),
.operand_credit(credit),.a_data(a_data),.s_data(s_data),.ws_data(ws_data),.w_data(w_data),
.busy(busy),.geometry_error(geometry_error),.protocol_error(protocol_error),
.weight_request_valid(wvalid),.weight_request_ready(wready),.weight_request_tag(wtag),.weight_request_address(waddress),.weight_request_words(wwords),
.weight_response_valid(rvalid),.weight_response_ready(rready),.weight_response_tag(rtag),.weight_response_index(rindex),.weight_response_data(rdata),
.auxiliary_request_valid(auxvalid),.auxiliary_request_ready(auxready),.auxiliary_request_generation(auxgen),
.auxiliary_request_a(auxa),.auxiliary_request_s(auxs),.auxiliary_request_ws(auxws),.auxiliary_request_w(auxw),
.auxiliary_response_valid(auxrsp),.auxiliary_response_ready(auxrspready),.auxiliary_response_generation(savedgen),.auxiliary_response_w(savedw),
.auxiliary_response_a_data({32'd0,saveda}),.auxiliary_response_s_data(saveds),.auxiliary_response_ws_data({32'd0,savedws}));
wire read_valid,read_ready,memory_ready;wire [63:0] read_tag,read_offset;
wire [31:0] read_object;wire [4:0] read_bytes;reg pending=0;integer delay_left=0;
reg [63:0] memory_tag,offset;reg [127:0] memory_data;
wire memory_valid=pending && delay_left==0;
assign read_ready=!pending && ticks%3!=0;
function automatic [7:0] byte_value(input [63:0] a);byte_value=8'(a*17+(a>>8)*13+3);endfunction
always @*for(integer l=0;l<16;l=l+1)memory_data[l*8+:8]=byte_value(offset+64'(l));
ot_a3_bf16_weight_transport #(.PASS_FIRST(1),.COMPACT_PASS_REUSE(REUSE)) transport(
.clk(clk),.rst_n(rst_n),.clear(clear),.command_valid(command_valid),.command_ready(transport_ready),
.command_generation(32'd7),.command_object(32'd13),.command_service_base(32'd100),
.command_object_bytes(64'dCAPVAL),.command_element_base(64'd11),.command_rows(16'd3),.command_cols(16'd53),.command_depth(16'(DEPTH)),
.command_column_stride(32'dSTRIDEVAL),.command_k_stride(32'd2),
.request_valid(wvalid),.request_ready(wready),.request_tag(wtag),.request_address(waddress),.request_words(wwords),
.response_valid(rvalid),.response_ready(rready),.response_tag(rtag),.response_index(rindex),.response_data(rdata),
.read_valid(read_valid),.read_ready(read_ready),.read_tag(read_tag),.read_offset(read_offset),.read_object(read_object),.read_bytes(read_bytes),
.memory_valid(memory_valid),.memory_ready(memory_ready),.memory_tag(memory_tag),.memory_data(memory_data),.memory_error(1'b0),
.protocol_error(transport_error));
reg check_pending=0,check_valid=0;integer check_index=0,output_index=0;
always @(posedge clk)begin
 if(!rst_n || clear)begin
  issued<=0;delivered<=0;fills<=0;pending<=0;auxrsp<=0;check_pending<=0;check_valid<=0;
 end else begin
  ticks<=ticks+1;
  if(geometry_error || protocol_error || transport_error)$fatal(1,"service fault at %0d",issued);
  if(rvalid && rready)fills<=fills+1;
  if(auxvalid && auxready)begin auxrsp<=1;savedgen<=auxgen;saveda<=auxa;saveds<=auxs;savedws<=auxws;savedw<=auxw;end
  if(auxrsp && auxrspready)auxrsp<=0;
  if(read_valid && read_ready)begin
   if(read_object!=13 || read_bytes==0 || read_offset+64'(read_bytes)>64'dCAPVAL)$fatal(1,"object bounds");
   pending<=1;delay_left<=2;offset<=read_offset;memory_tag<=read_tag;
  end
  if(pending && delay_left>0)delay_left<=delay_left-1;
  if(memory_valid && memory_ready)pending<=0;
  check_pending<=issue;check_valid<=check_pending;output_index<=check_index;
  if(issue)begin check_index<=issued;issued<=issued+1;end
 end
end
always @(negedge clk)if(check_valid && rst_n && !clear)begin
 if(w_data!==expected[output_index] || a_data!=={32'd0,req[output_index][127:96]} ||
    s_data!==req[output_index][95:64] || ws_data!=={32'd0,req[output_index][63:32]})$fatal(1,"joined bundle %0d",output_index);
 delivered=delivered+1;
end
task launch;begin
 @(negedge clk);if(!command_ready || !transport_ready)$fatal(1,"not ready");
 command_valid=1;@(negedge clk);command_valid=0;
end endtask
initial begin
 $readmemh("req.hex",req);$readmemh("words.hex",expected);
 repeat(2)@(negedge clk);rst_n=1;launch();wait(delivered==TOTAL);repeat(8)@(negedge clk);
 if(fills!=FETCHVAL || issued!=TOTAL || !busy || command_ready)$fatal(1,"completion/fill count %0d",fills);
 // Parent-approved cancellation clears both services; restart exercises all passes again.
 clear=1;@(negedge clk);clear=0;launch();wait(issued>10);@(negedge clk);clear=1;
 @(negedge clk);clear=0;launch();wait(delivered==TOTAL);repeat(8)@(negedge clk);
 if(fills!=FETCHVAL || issued!=TOTAL)$fatal(1,"restart traffic");
 $display("PASS runtime pass transport fills=%0d issued=%0d",fills,issued);$finish;
end
initial begin #20000000;$fatal(1,"timeout");end
endmodule
'''.replace('DVAL',str(depth)).replace('TVAL',str(len(req))).replace('RVAL',str(reuse)).replace('CAPVAL',str(capacity)).replace('STRIDEVAL',str(stride)).replace('FETCHVAL',str(fetches)))
    names=['ot_a3_lq8_runtime_operands','ot_a3_lq8_operand_admission','ot_a3_lq8_operand_cursor',
           'ot_a3_lq8_auxiliary_prefetch','ot_a3_lq8_operand_join','ot_a3_weight_pass_scheduler',
           'ot_a3_weight_tile_scheduler','ot_a3_weight_tile_prefetch','ot_a3_runtime_weight_banks',
           'ot_a3_operand_bank_owner','ot_a3_bf16_weight_transport','ot_a3_weight_layout_cursor','ot_a3_bf16_weight_gather']
    sim=tmp_path/'sim'
    c=subprocess.run(['iverilog','-g2012','-s','tb','-o',str(sim),*[str(ROOT/'rtl/abi3'/f'{n}.sv')for n in names],
                      str(ROOT/'rtl/test/tb_a3_runtime_weight_banks.sv'),str(bench)],capture_output=True,text=True,timeout=30)
    assert c.returncode==0,c.stderr
    r=subprocess.run(['vvp',str(sim)],cwd=tmp_path,capture_output=True,text=True,timeout=120)
    assert r.returncode==0,r.stdout+r.stderr
    assert f'PASS runtime pass transport fills={fetches} issued={len(req)}' in r.stdout
