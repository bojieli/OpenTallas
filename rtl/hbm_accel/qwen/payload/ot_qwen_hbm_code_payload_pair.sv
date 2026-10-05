`timescale 1ps/1fs
// Post-CDC CODE-only storage leaf. Translation, span installation/publication,
// stream-prefix, reuse and transport credit remain with the enclosing owner.
// Both SRAMs capture the same accepted write. Reads are old-before-write,
// then one protected capture edge plus the existing W6 decode combinational cone.
module ot_qwen_hbm_code_payload_pair #(
  parameter integer ENABLE=0, COLUMN_BASE=0, ROWS=4496
)(
  input wire clk, por_n,
  input wire wr_v, output wire wr_r,
  input ot_hbm_r14_pkg::owned_t wr_owned,
  input wire wr_span_bound, wr_kind,
  input wire [12:0] wr_row, input wire [11:0] wr_column,
  output wire visible_v, input wire visible_r,
  output ot_hbm_r14_pkg::identity_t visible_id,
  output wire [11:0] visible_tag, output wire [4:0] visible_beat,
  output wire [12:0] visible_row, output wire [11:0] visible_column,
  input wire [1:0] rd_v, rd_span_bound, rd_published,
  input wire [25:0] rd_row, output wire [1:0] rd_r, rd_rsp_v,
  output wire [511:0] rd_data,
  output wire [1:0] rd_corrected, rd_uncorrectable,
  output wire fault
);
  import ot_hbm_r14_pkg::*;
  import ot_gpu_w6_secded_pkg::*;
  localparam integer BANKS=(ROWS+1023)/1024;
  generate if (!ENABLE) begin : off
    assign wr_r=0; assign visible_v=0; assign visible_id='0;
    assign visible_tag=0; assign visible_beat=0;
    assign visible_row=0; assign visible_column=0;
    assign rd_r=0; assign rd_rsp_v=0; assign rd_data=0;
    assign rd_corrected=0; assign rd_uncorrectable=0; assign fault=0;
  end else begin : on
    typedef struct packed {
      logic sticky, visible;
      logic [1:0] read_in, read_out;
      logic [2:0] bank0, bank1, check0, check1;
    } control_t;
    typedef struct packed {
      identity_t id; logic [11:0] tag; logic [4:0] beat;
      logic [12:0] row; logic [11:0] column;
    } metadata_t;
    reg [71:0] control_code;
    reg [287:0] metadata_code;
    reg [287:0] captured_code[0:1];
    wire [65:0] cd=decode64(control_code);
    control_t c, n;
    assign c=cd[$bits(control_t)-1:0];
    wire control_bad=cd[65] || (|cd[63:$bits(control_t)]);
    wire [255:0] metadata_raw;
    wire [3:0] metadata_ue;
    for(genvar k=0;k<4;k=k+1) begin : md
      wire [65:0] d=decode64(metadata_code[k*72+:72]);
      assign metadata_raw[k*64+:64]=d[63:0];
      assign metadata_ue[k]=d[65];
    end
    metadata_t m;
    assign m=metadata_raw[$bits(metadata_t)-1:0];
    wire metadata_bad=c.visible && ((|metadata_ue) || (|metadata_raw[255:$bits(metadata_t)]));
    wire [1:0] read_bad;
    assign fault=control_bad || c.sticky || metadata_bad || (|(read_bad & c.read_out));
    wire column_ok=(wr_column==12'(COLUMN_BASE)) || (wr_column==12'(COLUMN_BASE+1));
    wire format_ok=!wr_kind && column_ok && (wr_row<ROWS);
    assign wr_r=wr_span_bound && format_ok && !fault && (!c.visible || visible_r);
    wire write_fire=wr_v && wr_r;
    assign visible_v=c.visible && !fault;
    assign visible_id=m.id; assign visible_tag=m.tag; assign visible_beat=m.beat;
    assign visible_row=m.row; assign visible_column=m.column;
    wire [1:0] read_fire;
    for(genvar p=0;p<2;p=p+1) begin : port
      assign rd_r[p]=rd_span_bound[p] && rd_published[p] && (rd_row[p*13+:13]<ROWS) && !fault;
      assign read_fire[p]=rd_v[p] && rd_r[p];
      assign rd_rsp_v[p]=c.read_out[p] && !fault;
      wire [3:0] ue, corrected;
      for(genvar k=0;k<4;k=k+1) begin : decode
        wire [65:0] d=decode64(captured_code[p][k*72+:72]);
        assign rd_data[p*256+k*64+:64]=d[63:0];
        assign ue[k]=d[65]; assign corrected[k]=d[64];
      end
      assign read_bad[p]=|ue;
      assign rd_uncorrectable[p]=c.read_out[p] && (|ue);
      assign rd_corrected[p]=c.read_out[p] && (|corrected);
    end
    // Pack/unpack only: parity positions are those of the existing W6 codec.
    // The four encode64/decode64 calls remain the sole payload ECC algorithm.
    function automatic [7:0] checks(input [71:0] code);
      checks={code[71],code[63],code[31],code[15],code[7],code[3],code[1],code[0]};
    endfunction
    function automatic [71:0] assemble(input [63:0] data,input [7:0] check);
      integer bitpos,j;
      begin
        assemble=0; j=0;
        for(bitpos=1;bitpos<=71;bitpos=bitpos+1)
          if((bitpos & (bitpos-1))!=0) begin assemble[bitpos-1]=data[j];j=j+1;end
        assemble[0]=check[0];assemble[1]=check[1];assemble[3]=check[2];
        assemble[7]=check[3];assemble[15]=check[4];assemble[31]=check[5];
        assemble[63]=check[6];assemble[71]=check[7];
      end
    endfunction
    wire [31:0] write_checks;
    for(genvar k=0;k<4;k=k+1) begin : encode
      wire [71:0] encoded=encode64(wr_owned.data[k*64+:64]);
      assign write_checks[k*8+:8]=checks(encoded);
    end
    wire [255:0] packed_checks=256'(write_checks) << (wr_row[2:0]*32);
    wire [255:0] check_mask=256'hffffffff << (wr_row[2:0]*32);
    wire [255:0] data_q[0:1][0:BANKS-1], check_q[0:1][0:BANKS-1];
    for(genvar p=0;p<2;p=p+1) begin : column
      for(genvar b=0;b<BANKS;b=b+1) begin : bank
        wire we=write_fire && wr_column==12'(COLUMN_BASE+p) && wr_row[12:10]==3'(b);
        wire re=read_fire[p] && rd_row[p*13+10+:3]==3'(b);
        ot_sram_1r1w_1024x256_m2_r2c2 data_store(
          .clk(clk),.r_ce_in(re),.r_addr_in(rd_row[p*13+:10]),.rd_out(data_q[p][b]),
          .w_ce_in(we),.w_addr_in(wr_row[9:0]),.wd_in(wr_owned.data),.w_mask_in({256{1'b1}}),
          .rr_en(2'b0),.rr_addr(18'b0),.cr_en(2'b0),.cr_sel(16'b0));
        ot_sram_1r1w_128x256_m1_r2c2 check_store(
          .clk(clk),.r_ce_in(re),.r_addr_in(rd_row[p*13+3+:7]),.rd_out(check_q[p][b]),
          .w_ce_in(we),.w_addr_in(wr_row[9:3]),.wd_in(packed_checks),.w_mask_in(check_mask),
          .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
      end
      wire [2:0] rb=(p==0)?c.bank0:c.bank1;
      wire [2:0] rs=(p==0)?c.check0:c.check1;
      wire [31:0] selected_checks=check_q[p][rb] >> (rs*32);
      for(genvar k=0;k<4;k=k+1) begin : capture
        always @(posedge clk)
          if(c.read_in[p] && !control_bad)
            captured_code[p][k*72+:72]<=assemble(data_q[p][rb][k*64+:64],selected_checks[k*8+:8]);
      end
    end
    always @* begin
      n=c;
      n.read_in=read_fire; n.read_out=c.read_in;
      if(read_fire[0]) begin n.bank0=rd_row[12:10];n.check0=rd_row[2:0];end
      if(read_fire[1]) begin n.bank1=rd_row[25:23];n.check1=rd_row[15:13];end
      if(visible_v && visible_r)n.visible=0;
      if(write_fire)n.visible=1;
      if(control_bad || metadata_bad || (|(read_bad & c.read_out)) ||
         (wr_v && wr_span_bound && !format_ok)) n.sticky=1;
    end
    always @(posedge clk or negedge por_n) begin
      if(!por_n) begin control_code<=0;metadata_code<=0;end
      else if(!control_bad) begin
        control_code<=encode64(64'(n));
        if(write_fire) begin : receipt
          metadata_t next_metadata;
          next_metadata={wr_owned.id,wr_owned.physical_tag,wr_owned.beat,wr_row,wr_column};
          for(integer k=0;k<4;k=k+1)
            metadata_code[k*72+:72]<=encode64(64'(256'(next_metadata)>>(k*64)));
        end
      end
    end
  end endgenerate
endmodule
