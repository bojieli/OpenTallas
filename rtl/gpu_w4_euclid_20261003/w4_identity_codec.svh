function automatic [71:0] w4_encode(input [54:0] payload);
 reg [63:0] data;reg [71:0] c;reg parity;integer p,k,j;
 begin
  data={9'b0,payload};c=0;j=0;
  for(p=1;p<=71;p=p+1) if((p&(p-1))!=0)begin c[p-1]=data[j];j=j+1;end
  for(k=1;k<=64;k=k*2)begin parity=0;for(p=1;p<=71;p=p+1)if((p&k)!=0)parity=parity^c[p-1];c[k-1]=parity;end
  c[71]=^c[70:0];w4_encode=c;
 end
endfunction
function automatic [55:0] w4_decode(input [71:0] word);
 reg [71:0] c;reg [63:0] data;reg parity,bad;integer p,k,j,syndrome;
 begin
  c=word;syndrome=0;
  for(k=1;k<=64;k=k*2)begin parity=0;for(p=1;p<=71;p=p+1)if((p&k)!=0)parity=parity^c[p-1];if(parity)syndrome=syndrome+k;end
  bad=0;
  if((^c)==1'b1)begin if(syndrome>0&&syndrome<=71)c[syndrome-1]=~c[syndrome-1];else if(syndrome>71)bad=1;end
  else if(syndrome!=0)bad=1;
  data=0;j=0;for(p=1;p<=71;p=p+1)if((p&(p-1))!=0)begin data[j]=c[p-1];j=j+1;end
  if(data[63:55]!=0)bad=1;
  w4_decode={bad,data[54:0]};
 end
endfunction
