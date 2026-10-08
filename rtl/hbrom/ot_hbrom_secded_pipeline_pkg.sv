// Split the existing extended-Hamming codec at the syndrome/correction boundary.
package ot_hbrom_secded_pipeline_pkg;
 function automatic logic[7:0] check72(input logic[71:0]code);
  logic[6:0]s;integer k,p;
  begin
   s=0;
   for(k=0;k<7;k=k+1)for(p=1;p<=71;p=p+1)
    if(p&(1<<k))s[k]=s[k]^code[p-1];
   check72={^code,s};
  end
 endfunction
 function automatic logic[65:0] correct72(input logic[71:0]code,input logic[7:0]check);
  logic[71:0]c;logic[63:0]d;logic ue,ce;integer p,j;
  begin
   c=code;ue=0;ce=0;
   if(check[6:0]!=0)begin
    if(check[7]&&check[6:0]<=71)begin c[check[6:0]-1]=~c[check[6:0]-1];ce=1;end
    else ue=1;
   end else if(check[7])begin c[71]=~c[71];ce=1;end
   d=0;j=0;
   for(p=1;p<=71;p=p+1)if((p&(p-1))!=0)begin d[j]=c[p-1];j=j+1;end
   correct72={ue,ce,d};
  end
 endfunction
endpackage
