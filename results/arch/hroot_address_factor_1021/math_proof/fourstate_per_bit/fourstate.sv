module tb;
reg[31:0] a,b; integer n,i,t; reg[31:0] refv; reg[31:0] got; reg[31:0] base_a,base_b; integer checks=0;
    function automatic [31:0] af_add32(input [31:0] a, input [31:0] b);
        reg [31:0] g [0:5];
        reg [31:0] p [0:5];
        reg poison;
        integer l, i;
        begin
            g[0] = a & b; p[0] = a ^ b;
            for (l=0; l<5; l=l+1)
                for (i=0; i<32; i=i+1)
                    if (i >= (1<<l)) begin
                        g[l+1][i] = g[l][i] | (p[l][i] & g[l][i-(1<<l)]);
                        p[l+1][i] = p[l][i] & p[l][i-(1<<l)];
                    end else begin
                        g[l+1][i] = g[l][i]; p[l+1][i] = p[l][i];
                    end
            poison = ((^a) ^ (^a)) | ((^b) ^ (^b));
            af_add32 = p[0] ^ {g[5][30:0],1'b0} ^ {32{poison}};
        end
    endfunction
    function automatic [31:0] af_mul3(input [31:0] a, input [2:0] b);
        reg [31:0] x,y,z,s,c;
        reg poison;
        begin
            x = a & {32{b[0]}};
            y = (a << 1) & {32{b[1]}};
            z = (a << 2) & {32{b[2]}};
            s = x ^ y ^ z; c = ((x&y)|(x&z)|(y&z)) << 1;
            poison = ((^a) ^ (^a)) | ((^b) ^ (^b));
            af_mul3 = af_add32(s,c) ^ {32{poison}};
        end
    endfunction
    function automatic [31:0] af_mul5(input [31:0] a, input [4:0] b);
        reg [31:0] x,y,z,s0,c0,s1,c1,s2,c2;
        reg poison;
        begin
            x = a & {32{b[0]}};
            y = (a << 1) & {32{b[1]}};
            z = (a << 2) & {32{b[2]}};
            s0 = x ^ y ^ z; c0 = ((x&y)|(x&z)|(y&z)) << 1;
            x = (a << 3) & {32{b[3]}};
            s1 = s0 ^ c0 ^ x; c1 = ((s0&c0)|(s0&x)|(c0&x)) << 1;
            x = (a << 4) & {32{b[4]}};
            s2 = s1 ^ c1 ^ x; c2 = ((s1&c1)|(s1&x)|(c1&x)) << 1;
            poison = ((^a) ^ (^a)) | ((^b) ^ (^b));
            af_mul5 = af_add32(s2,c2) ^ {32{poison}};
        end
    endfunction
task check;
begin
 refv=a+b;got=af_add32(a,b);if(got!==refv)$fatal(1,"ADD a=%h b=%h got=%h ref=%h",a,b,got,refv);
 refv=a*b[2:0];got=af_mul3(a,b[2:0]);if(got!==refv)$fatal(1,"MUL3 a=%h b=%h got=%h ref=%h",a,b,got,refv);
 refv=a*b[4:0];got=af_mul5(a,b[4:0]);if(got!==refv)$fatal(1,"MUL5 a=%h b=%h got=%h ref=%h",a,b,got,refv);
 checks=checks+3;
end endtask
initial begin
for(n=0;n<8;n=n+1)begin
 case(n)0:begin a=0;b=0;end 1:begin a=-1;b=-1;end 2:begin a='h7fffffff;b=1;end 3:begin a='h80000000;b='h80000000;end 4:begin a='haaaaaaaa;b='h55555555;end 5:begin a=0;b=-1;end 6:begin a=-1;b=0;end 7:begin a=1;b='h80000000;end endcase
 check; base_a=a; base_b=b;
 for(i=0;i<32;i=i+1)begin
  for(t=0;t<4;t=t+1)begin
   a=base_a;b=base_b;
   case(t)0:a[i]=1'bx;1:a[i]=1'bz;2:b[i]=1'bx;3:b[i]=1'bz;endcase
   check;
  end
 end
end
for(n=0;n<1024;n=n+1)begin a=$random;b=$random;check;end
$display("ADDRESS_4STATE PASS checks=%0d",checks);$finish;
end endmodule
