module m(input [7:0] oh,input[3:0] w,lap,input[11:0] tags,input[2:0] rp,output bad);
wire[7:0] pl={lap,~lap}|{~w,~w};wire l1=|(oh&pl);reg[2:0]tagc;reg wc;integer i;always @* begin tagc=0;wc=0;for(i=0;i<4;i=i+1) if(oh[i]||oh[i+4])begin tagc=tagc|tags[3*i+:3];wc=wc|w[i];end end
wire old=l1&&(!wc||tagc==rp);wire[7:0]v;genvar z;generate for(z=0;z<4;z=z+1)begin assign v[z]=!w[z]||(!lap[z]&&tags[z*3+:3]==rp);assign v[z+4]=!w[z]||(lap[z]&&tags[z*3+:3]==rp);end endgenerate
wire hot=oh!=0&&((oh&(oh-1))==0);assign bad=hot&&(old!=|(oh&v));endmodule
