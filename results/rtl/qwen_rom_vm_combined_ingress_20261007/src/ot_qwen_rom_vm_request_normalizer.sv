// Candidate only: full-width source-semantic normalization, no clock or storage.
// Native source reference: ot_qwen_rom_rt_die_w12_vprm_stream4 vector-memory block.
// Default-off output interface; caller must retain its legacy path when disabled.
module ot_qwen_rom_vm_request_normalizer #(
 parameter integer ENABLE=0, VWA=16, VM_ELEMS=1048576
)(
 input wire me_wanted,
 input wire [2239:0] scalar_re,
 input wire [2240*24-1:0] scalar_raddr,
 input wire seq_re,input wire [VWA-1:0] seq_rword,
 input wire [48:0] word_we,input wire [49*24-1:0] word_waddr,
 input wire [49*16-1:0] word_wmask,
 input wire [64:0] scalar_we,input wire [65*24-1:0] scalar_waddr,
 input wire seq_we,input wire [VWA-1:0] seq_wword,
 input wire [865*32-1:0] ordered_write_data,
 output wire [2255:0] read_publish_en,read_en,read_zero,
 output wire [2256*32-1:0] read_addr,
 output wire [864:0] write_en,
 output wire [865*32-1:0] write_addr,write_data,
 input wire [2256*32-1:0] backend_read_data,
 output wire [2256*32-1:0] publish_read_data
);
 assign write_data=ordered_write_data;
 genvar i,l;
 generate for(i=0;i<2240;i=i+1)begin:g_sr
  localparam integer SLOT=i<192?i:i+16;
  wire [31:0] a={8'd0,scalar_raddr[i*24+:24]};
  wire want=(ENABLE!=0)&&scalar_re[i]&&(i<192||me_wanted);
  assign read_publish_en[SLOT]=want;
  assign read_en[SLOT]=want&&(a<VM_ELEMS);
  assign read_zero[SLOT]=want&&!(a<VM_ELEMS);
  assign read_addr[SLOT*32+:32]=a;
  assign publish_read_data[SLOT*32+:32]=read_zero[SLOT]?32'd0:backend_read_data[SLOT*32+:32];
 end
 for(i=0;i<49;i=i+1)begin:g_ww
  wire [31:0] wide_word={8'd0,word_waddr[i*24+:24]};
  wire word_in=wide_word<(VM_ELEMS/16);
  for(l=0;l<16;l=l+1)begin:g_lane
   wire [31:0] a=(wide_word<<4)+l;
   wire in_bounds=(VM_ELEMS%16==0)?word_in:(a<VM_ELEMS);
   assign write_en[i*16+l]=(ENABLE!=0)&&me_wanted&&word_we[i]&&word_wmask[i*16+l]&&in_bounds;
   assign write_addr[(i*16+l)*32+:32]=a;
  end
 end
 for(i=0;i<65;i=i+1)begin:g_sw
  wire [31:0] a={8'd0,scalar_waddr[i*24+:24]};
  assign write_en[784+i]=(ENABLE!=0)&&scalar_we[i]&&(a<VM_ELEMS);
  assign write_addr[(784+i)*32+:32]=a;
 end
 for(l=0;l<16;l=l+1)begin:g_seq
  wire [31:0] rw=seq_rword,ww=seq_wword;
  wire [31:0] ra=(rw<<4)+l,wa=(ww<<4)+l;
  wire rin=(VM_ELEMS%16==0)?(rw<VM_ELEMS/16):(ra<VM_ELEMS);
  wire win=(VM_ELEMS%16==0)?(ww<VM_ELEMS/16):(wa<VM_ELEMS);
  assign read_publish_en[192+l]=(ENABLE!=0)&&seq_re;
  assign read_en[192+l]=(ENABLE!=0)&&seq_re&&rin;
  assign read_zero[192+l]=(ENABLE!=0)&&seq_re&&!rin;
  assign read_addr[(192+l)*32+:32]=ra;
  assign publish_read_data[(192+l)*32+:32]=read_zero[192+l]?32'd0:backend_read_data[(192+l)*32+:32];
  assign write_en[849+l]=(ENABLE!=0)&&seq_we&&win;
  assign write_addr[(849+l)*32+:32]=wa;
 end endgenerate
 initial if(VWA<1||VWA>24||VM_ELEMS<1||VM_ELEMS>16777216)
  $fatal(1,"unsupported candidate normalizer source ABI");
endmodule
