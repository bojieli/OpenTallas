from pathlib import Path
p=Path(__file__).parent
r=[]
for name,kind in [('off32_old','base'),('off32_split','split'),('off32_pure','pure')]:
 s='module '+name+'(input clk,input[31:0]iteration,input[15:0]step,output reg[31:0]off32);\n'
 if kind=='base':
  s+='reg[31:0]aq;reg[15:0]bq;wire[15:0]'+','.join('p%d'%n for n in range(7))+';reg[15:0]'+','.join('q%d'%n for n in range(7))+';wire[31:0]z;\n'
  s+='base2 a(aq,bq,'+','.join('p%d'%n for n in range(7))+');base3 b('+','.join('q%d'%n for n in range(7))+',z);\n'
  s+='always@(posedge clk)begin aq<=iteration;bq<=step;'+''.join('q%d<=p%d;'%(n,n) for n in range(7))+'off32<=z;end\n'
 else:
  s+='wire[7:0]'+','.join('p%d'%n for n in range(26))+';reg[7:0]'+','.join('q%d'%n for n in range(26))+';wire[31:0]z;\n'
  s+='new1 a(iteration,step,'+','.join('p%d'%n for n in range(26))+');always@(posedge clk)begin '+''.join('q%d<=p%d;'%(n,n) for n in range(26))+'end\n'
  if kind=='split':
   s+='wire[15:0]lo,h0,h1;wire carry;reg[15:0]lq,hq0,hq1;reg cq;split2 b('+','.join('q%d'%n for n in range(26))+',lo,h0,h1,carry);split3 c(lq,hq0,hq1,cq,z);always@(posedge clk)begin lq<=lo;hq0<=h0;hq1<=h1;cq<=carry;off32<=z;end\n'
  else:
   s+='wire[31:0]x,y;reg[31:0]xq,yq;pure2 b('+','.join('q%d'%n for n in range(26))+',x,y);pure3 c(xq,yq,z);always@(posedge clk)begin xq<=x;yq<=y;off32<=z;end\n'
 s+='endmodule\n';r.append(s)
(p/'standalone.sv').write_text('\n'.join(r))
