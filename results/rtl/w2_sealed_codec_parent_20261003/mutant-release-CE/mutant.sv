`timescale 1ps/1ps
// Pure characterization leaf; no production or NC6 successor instantiation.
// Original F0 interleaved extended Hamming packing. Each physical word has a
// STATIC address/stage seal. CE returns a repair candidate, never clean release.
module ot_w2_sealed_secded72 #(
 parameter logic [6:0] PC_ID=7'd0,
 parameter logic [9:0] WORD_INDEX=10'd0,
 parameter logic [2:0] WORD_KIND=3'd0,
 parameter integer PAYLOAD_BITS=44
)(
 input wire [43:0] payload,
 input wire [71:0] current_word,
 output logic [71:0] encoded_word,
 output logic [6:0] syndrome,
 output logic overall_odd,clean,correctable,uncorrectable,seal_ok,padding_ok,
 output logic release_clean,
 output logic [43:0] repaired_payload,
 output logic [71:0] repaired_word
);
 logic [63:0] encode_data,repair_data;
 logic [71:0] fixed_word;
 integer pos,data_index,parity_index;
 logic parity_bit;
 initial if(PAYLOAD_BITS<1||PAYLOAD_BITS>44) $fatal(1,"payload geometry");
 always_comb begin
  encode_data={WORD_KIND,WORD_INDEX,PC_ID,payload};
  encoded_word='0;data_index=0;
  for(pos=1;pos<=71;pos=pos+1)begin
   if((pos&(pos-1))!=0)begin
    encoded_word[pos-1]=encode_data[data_index];data_index=data_index+1;
   end
  end
  for(parity_index=0;parity_index<7;parity_index=parity_index+1)begin
   parity_bit=1'b0;
   for(pos=1;pos<=71;pos=pos+1)
    if((pos&(1<<parity_index))!=0)parity_bit=parity_bit^encoded_word[pos-1];
   encoded_word[(1<<parity_index)-1]=parity_bit;
  end
  encoded_word[71]=^encoded_word[70:0];
  syndrome='0;
  for(parity_index=0;parity_index<7;parity_index=parity_index+1)begin
   parity_bit=1'b0;
   for(pos=1;pos<=71;pos=pos+1)
    if((pos&(1<<parity_index))!=0)parity_bit=parity_bit^current_word[pos-1];
   syndrome[parity_index]=parity_bit;
  end
  overall_odd=^current_word;
  clean=(syndrome==0)&&!overall_odd;
  correctable=overall_odd&&(syndrome<=7'd71);
  uncorrectable=(!overall_odd&&(syndrome!=0))||(overall_odd&&(syndrome>7'd71));
  fixed_word=current_word;
  if(correctable)begin
   if(syndrome==0)fixed_word[71]=~fixed_word[71];
   else fixed_word[syndrome-1'b1]=~fixed_word[syndrome-1'b1];
  end
  repair_data='0;data_index=0;
  for(pos=1;pos<=71;pos=pos+1)begin
   if((pos&(pos-1))!=0)begin
    repair_data[data_index]=fixed_word[pos-1];data_index=data_index+1;
   end
  end
  seal_ok=(repair_data[63:44]=={WORD_KIND,WORD_INDEX,PC_ID});
  padding_ok=1'b1;
  for(pos=PAYLOAD_BITS;pos<44;pos=pos+1)padding_ok=padding_ok&&!repair_data[pos];
  // Critically: repaired_data on CE is NOT irreversible-consumption permission.
  release_clean=(clean||correctable)&&seal_ok&&padding_ok;
  repaired_payload='0;repaired_word='0;
  if(!uncorrectable&&seal_ok&&padding_ok)begin
   repaired_payload=repair_data[43:0];repaired_word=fixed_word;
  end
 end
endmodule
