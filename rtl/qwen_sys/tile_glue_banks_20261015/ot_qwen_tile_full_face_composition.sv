// Active five-full-word native face candidate. Each registered word has its
// own clock and its own point-to-point reset from the balanced reset tree.
module ot_qwen_tile_face_banks_full #(parameter integer MUT=0)(
 input wire [4:0] ck_face,rst_face_n,
 input wire [507:0]tap_d,input wire [513:0]na_d,nb_d,to_d,ny_d,
 output wire [507:0]tap_q,output wire [513:0]na_q,nb_q,to_q,ny_q);
 localparam integer DATA_MUT=(MUT<3)?MUT:0;
 qwen_glue_v508 #(.MUT(DATA_MUT)) tap_bank(.clk(ck_face[0]),.rst_n(rst_face_n[0]),.d(tap_d),.q(tap_q));
 qwen_glue_v514 #(.MUT(DATA_MUT)) na_bank(.clk((MUT==3)?ck_face[0]:ck_face[1]),.rst_n(rst_face_n[1]),.d(na_d),.q(na_q));
 qwen_glue_v514 #(.MUT(DATA_MUT)) nb_bank(.clk(ck_face[2]),.rst_n(rst_face_n[2]),.d(nb_d),.q(nb_q));
 qwen_glue_v514 #(.MUT(DATA_MUT)) to_bank(.clk(ck_face[3]),.rst_n(rst_face_n[3]),.d(to_d),.q(to_q));
 qwen_glue_v514 #(.MUT(DATA_MUT)) ny_bank(.clk(ck_face[4]),.rst_n(rst_face_n[4]),.d(ny_d),.q(ny_q));
endmodule

// Exact active packing's reset assignment. The remaining reset target bits
// belong to the real operand/TX/RQR/child registers in the future parent.
module ot_qwen_tile_native_face_reset #(parameter integer RMUT=0)(
 input wire [8:0]ck_reset,input wire [4:0]ck_face,input wire rst_n,
 input wire [507:0]tap_d,input wire [513:0]na_d,nb_d,to_d,ny_d,
 output wire [507:0]tap_q,output wire [513:0]na_q,nb_q,to_q,ny_q,
 output wire [95:0]reset_targets);
 ot_qwen_native_reset_tree #(.MUT(RMUT)) u_reset(.ck_reset(ck_reset),.rst_n(rst_n),.child_reset_n(reset_targets));
 ot_qwen_tile_face_banks_full u_faces(.ck_face(ck_face),
  .rst_face_n({reset_targets[41],reset_targets[38],reset_targets[31],reset_targets[20],reset_targets[79]}),
  .tap_d(tap_d),.na_d(na_d),.nb_d(nb_d),.to_d(to_d),.ny_d(ny_d),
  .tap_q(tap_q),.na_q(na_q),.nb_q(nb_q),.to_q(to_q),.ny_q(ny_q));
endmodule
