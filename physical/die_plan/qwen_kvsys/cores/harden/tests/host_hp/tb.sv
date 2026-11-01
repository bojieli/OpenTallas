module tb;
reg ck=0;always #5 ck=~ck;
reg rst_n=0,take=0;reg[2047:0] words;reg[59:0] flags;reg[5:0] caught=0;
for(genvar n=0;n<6;n=n+1)begin:g
wire[511:0] a,b,m;wire[14:0] af,bf,mf;
hp_old #(.RP_REPL(1<<n)) a0(ck,rst_n,take,words,flags,a,af);
hp_new #(.RP_REPL(1<<n)) b0(ck,rst_n,take,words,flags,b,bf);
hp_mut #(.RP_REPL(1<<n)) m0(ck,rst_n,take,words,flags,m,mf);
always @(negedge ck)if(rst_n)begin
 assert({a,af}=={b,bf})else $fatal(1,"HP_LOCKSTEP n=%0d",n);
 if({a,af}!={m,mf})caught[n]=1;
end
end
initial begin
words=0;flags=0;repeat(3)@(negedge ck);rst_n=1;
for(int cycle=0;cycle<2048;cycle++)begin
 for(int k=0;k<64;k++)words[k*32+:32]=$urandom;
 flags=60'({$urandom,$urandom});take=($urandom%3)!=0;
 @(negedge ck);
end
assert(caught==6'b111111)else $fatal(1,"HP_MUTANT_NOT_CAUGHT %b",caught);
$display("HP_LOCKSTEP PASS variants6 cycles2048 payload512 flags15 mutant6/6 cycles_added0");$finish;
end
endmodule
