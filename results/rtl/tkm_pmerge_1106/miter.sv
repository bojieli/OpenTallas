module miter(input[343:0]entry,input[7:0]entry_tag,output bad,output bad_mut1,output bad_mut2);
wire[343:0]g,c,m1,m2;
ot_tkm_merge_gold gold(entry,entry_tag,g);
ot_tkm_merge_parallel candidate(entry,entry_tag,c);
ot_tkm_merge_parallel #(.MUT(1)) mutant1(entry,entry_tag,m1);
ot_tkm_merge_parallel #(.MUT(2)) mutant2(entry,entry_tag,m2);
assign bad=|(g^c);assign bad_mut1=|(g^m1);assign bad_mut2=|(g^m2);
endmodule
