from pathlib import Path
p=Path(__file__).parent
pairs=[(i,j) for j in range(4) for i in range(8) if i+j<8]
assert len(pairs)==26
ports=','.join('input [7:0] p%d'%n for n in range(26))
cols=[[] for _ in range(32)]
for n,(i,j) in enumerate(pairs):
 for b in range(min(8,32-4*(i+j))):cols[4*(i+j)+b].append('p%d[%d]'%(n,b))
net=[];idx=0;layers=0
while max(map(len,cols))>2:
 nxt=[[] for _ in range(32)]
 for b,ss in enumerate(cols):
  ss=ss[:]
  while len(ss)>=3:
   a,c,d=ss[:3];ss=ss[3:];s='s%d'%idx;t='c%d'%idx;idx+=1
   net.append('wire %s,%s;assign %s=%s^%s^%s;assign %s=(%s&%s)|(%s&%s)|(%s&%s);'%(s,t,s,a,c,d,t,a,c,a,d,c,d))
   nxt[b].append(s)
   if b<31:nxt[b+1].append(t)
  nxt[b]+=ss
 cols=nxt;layers+=1
rows=['{'+','.join(cols[b][k] if len(cols[b])>k else "1'b0" for b in reversed(range(32)))+'}' for k in range(2)]
compress='\n'.join(net)+'\nwire[31:0] r0='+rows[0]+';\nwire[31:0] r1='+rows[1]+';\n'
mods=[]
mods.append('module base1(input[31:0]a,input[15:0]b,output[31:0]x,output[15:0]y);assign x=a;assign y=b;endmodule')
mods.append('module base2(input[31:0]a,input[15:0]b,'+','.join('output[15:0]p%d'%n for n in range(7))+');'+''.join('assign p%d=a[%d+:8]*b[%d+:8];'%(n,8*i,8*j) for n,(i,j) in enumerate([(0,0),(1,0),(2,0),(3,0),(0,1),(1,1),(2,1)]))+'endmodule')
off="{16'd0,p0}+{8'd0,p1,8'd0}+{p2,16'd0}+{p3[7:0],24'd0}+{8'd0,p4,8'd0}+{p5,16'd0}+{p6[7:0],24'd0}"
mods.append('module base3('+','.join('input[15:0]p%d'%n for n in range(7))+',output[31:0]y);assign y='+off+';endmodule')
mods.append('module new1(input[31:0]a,input[15:0]b,'+','.join('output[7:0]p%d'%n for n in range(26))+');'+''.join('assign p%d=a[%d+:4]*b[%d+:4];'%(n,4*i,4*j) for n,(i,j) in enumerate(pairs))+'endmodule')
mods.append('module pure2('+ports+',output[31:0]x,y);'+compress+'assign x=r0;assign y=r1;endmodule')
mods.append('module split2('+ports+',output[15:0]lo,h0,h1,output carry);'+compress+"assign {carry,lo}={1'b0,r0[15:0]}+{1'b0,r1[15:0]};assign h0=r0[31:16];assign h1=r1[31:16];endmodule")
mods.append('module pure3(input[31:0]x,y,output[31:0]z);assign z=x+y;endmodule')
mods.append('module split3(input[15:0]lo,h0,h1,input carry,output[31:0]z);assign z={h0+h1+carry,lo};endmodule')
# explicit width high expression
mods[-1]='module split3(input[15:0]lo,h0,h1,input carry,output[31:0]z);wire[15:0]h=h0+h1+carry;assign z={h,lo};endmodule'
(p/'leaf.v').write_text('\n'.join(mods)+'\n')
print('pairs',len(pairs),'FA',idx,'layers',layers)
