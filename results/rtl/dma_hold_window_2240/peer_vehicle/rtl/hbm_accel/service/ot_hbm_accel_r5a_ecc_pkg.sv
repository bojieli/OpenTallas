// Codec split at the syndrome/correction boundary for a real registered pipeline.
package ot_hbm_accel_r5a_ecc_pkg;
 import ot_gpu_w6_secded_pkg::*;
 function automatic[63:0] raw64(input[71:0] c);
  integer j;j=0;for(integer p=1;p<=71;p++)if((p&(p-1))!=0)begin raw64[j]=c[p-1];j++;end
 endfunction
 function automatic[7:0] parity64(input[71:0] c);
  for(integer k=0;k<7;k++)parity64[k]=c[(1<<k)-1];parity64[7]=c[71];
 endfunction
 function automatic[71:0] join64(input[63:0] d,input[7:0] p);
  reg[71:0] c;integer j;c=0;j=0;
  for(integer i=1;i<=71;i++)if((i&(i-1))!=0)begin c[i-1]=d[j];j++;end
  for(integer k=0;k<7;k++)c[(1<<k)-1]=p[k];c[71]=p[7];join64=c;
 endfunction
 function automatic[7:0] syndrome64(input[71:0] c);
  reg[7:0] s;s=0;
  for(integer k=0;k<7;k++)for(integer p=1;p<=71;p++)if((p&(1<<k))!=0)s[k]=s[k]^c[p-1];
  s[7]=^c;syndrome64=s;
 endfunction
 function automatic[65:0] finish64(input[71:0] c,input[7:0] s);
  reg[71:0] x;reg ue; x=c;ue=(s[6:0]!=0)&&(!s[7]||s[6:0]>71);
  for(integer p=1;p<=71;p++)if(s[7]&&s[6:0]==7'(p))x[p-1]=~c[p-1];
  finish64={ue,s[7]&&!ue,raw64(x)};
 endfunction
endpackage
