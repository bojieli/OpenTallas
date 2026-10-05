`timescale 1ns/1ps
// ONE serialized factory profile ROM, not64replicas. Nash sealed source cursors
// are the only inputs. Never connect cmd_* or command SHA to this module.
// Priority service holds on the existing cursor until its actual advance;
// another actor waits profile_valid0. No new cursor/lease/clock/identity state.
module ot_gpu_native_shape_authority #(
 parameter bit ENABLE=0,
 parameter integer DESCRIPTORS=116,PROFILE_ROWS=10950,
 parameter BASE_FILE="",PROFILE_FILE="",DESCRIPTOR_FILE="",PC_TEMPLATE_FILE=""
)(
 input wire [63:0] source_valid,
 input wire [15295:0] source_tuple,input wire [4095:0] source_sequence,
 input wire [511:0] source_descriptor,source_types,
 input wire [191:0] source_operands,
 input wire [255:0] source_signed_i8_mask,source_vector_mask,
 input wire [2047:0] source_counts,
 output reg [63:0] profile_valid,
 output reg [15295:0] profile_tuple,output reg [703:0] profile_PC,
 output reg [4095:0] profile_sequence,output reg [16383:0] profile_shape,
 output reg [255:0] profile_present,profile_double,
 output reg [63:0] profile_result_double
);
 reg [16:0] base_rom[0:DESCRIPTORS*256-1];
 reg [328:0] profile_rom[0:PROFILE_ROWS-1];
 reg [23:0] descriptor_rom[0:DESCRIPTORS-1];
 reg [15:0] pc_templates[0:1736];
 integer actor,lane,chosen,address,row_index,anchor,ordinal;
 reg selected;reg [238:0] tuple_id;reg [63:0] sequence_id;
 reg [7:0] descriptor,types;reg [2:0] operands;
 reg [3:0] signed_mask,rank_mask,vary_mask;
 reg [31:0] counts;reg [11:0] literal_types;reg [58:0] source_key;
 reg [16:0] base_word;reg [328:0] row_word;reg [23:0] recipe;
 reg legal;reg [10:0] PC;
 initial begin
  for(integer r=0;r<DESCRIPTORS*256;r=r+1)base_rom[r]=0;
  for(integer r=0;r<PROFILE_ROWS;r=r+1)profile_rom[r]=0;
  for(integer r=0;r<DESCRIPTORS;r=r+1)descriptor_rom[r]=0;
  for(integer r=0;r<1737;r=r+1)pc_templates[r]=0;
  if(BASE_FILE!="")$readmemh(BASE_FILE,base_rom);
  if(PROFILE_FILE!="")$readmemh(PROFILE_FILE,profile_rom);
  if(DESCRIPTOR_FILE!="")$readmemh(DESCRIPTOR_FILE,descriptor_rom);
  if(PC_TEMPLATE_FILE!="")$readmemh(PC_TEMPLATE_FILE,pc_templates);
 end
 always @*begin
  profile_valid=0;profile_tuple=0;profile_PC=0;profile_sequence=0;
  profile_shape=0;profile_present=0;profile_double=0;profile_result_double=0;
  selected=0;chosen=0;tuple_id=0;sequence_id=0;descriptor=0;types=0;
  operands=0;signed_mask=0;rank_mask=0;counts=0;literal_types=0;
  vary_mask=0;anchor=1;source_key=0;address=0;ordinal=0;row_index=0;
  base_word=0;row_word=0;recipe=0;legal=0;PC=0;
  for(actor=0;actor<64;actor=actor+1)begin
   if(ENABLE&&source_valid[actor]&&!selected)begin
    selected=1;chosen=actor;tuple_id=source_tuple[actor*239+:239];
    sequence_id=source_sequence[actor*64+:64];descriptor=source_descriptor[actor*8+:8];
    types=source_types[actor*8+:8];operands=source_operands[actor*3+:3];
    signed_mask=source_signed_i8_mask[actor*4+:4];rank_mask=source_vector_mask[actor*4+:4];
    counts=source_counts[actor*32+:32];
   end
  end
  for(lane=0;lane<4;lane=lane+1)begin
   literal_types[lane*3+:3]=signed_mask[lane]?3'd4:{1'b0,types[lane*2+:2]};
   if(counts[lane*8+:8]>1)vary_mask[lane]=1;
   if(counts[lane*8+:8]>anchor)anchor=counts[lane*8+:8];
  end
  PC=tuple_id[174:164];source_key={rank_mask,counts,literal_types,operands,descriptor};
  if(selected&&descriptor<DESCRIPTORS&&PC<1737&&tuple_id[35:30]==chosen&&anchor<=128)begin
   address={descriptor,rank_mask,vary_mask};base_word=base_rom[address];
   ordinal=(anchor>1)?anchor-2:0;row_index=base_word[15:0]+ordinal;recipe=descriptor_rom[descriptor];
   if(base_word[16]&&row_index<PROFILE_ROWS)begin
    row_word=profile_rom[row_index];
    legal=row_word[328]&&row_word[327]&&row_word[314:256]==source_key&&
     recipe[22]&&recipe[21:18]<13&&pc_templates[PC][recipe[21:18]];
    for(lane=0;lane<4;lane=lane+1)
     if(signed_mask[lane]&&(types[lane*2+:2]!=3||recipe[5:0]!=21))legal=0;
    if(legal)begin
     profile_valid[chosen]=1;profile_tuple[chosen*239+:239]=tuple_id;
     profile_PC[chosen*11+:11]=PC;profile_sequence[chosen*64+:64]=sequence_id;
     profile_shape[chosen*256+:256]=row_word[255:0];
     profile_present[chosen*4+:4]=(4'h1<<operands)-1'b1;
     for(lane=0;lane<4;lane=lane+1)
      if(lane<operands&&literal_types[lane*3+:3]==2&&counts[lane*8+:8]>64)
       profile_double[chosen*4+lane]=1;
     profile_result_double[chosen]=(row_word[325:323]==2&&row_word[322:315]>64);
    end
   end
  end
 end
endmodule
