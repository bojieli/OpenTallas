#include <cstdint>
#include <cstdio>
#include <cstring>
#include <cmath>
#include <cfenv>
#pragma STDC FENV_ACCESS ON
static float f(uint32_t u){float x;std::memcpy(&x,&u,4);return x;}
static uint32_t bits(float x){uint32_t u;std::memcpy(&u,&x,4);return u;}
int main(){
 std::fesetround(FE_TONEAREST);
 uint32_t s=0x92170523;auto next=[&](){s^=s<<13;s^=s>>17;s^=s<<5;return s;};
 uint32_t edge[]={0,0x80000000,1,0x80000001,0x007fffff,0x00800000,0x80800000,0x3f800000,0xbf800000,0x3f800001,0x3f000000,0x40000000,0x7f7fffff,0xff7fffff,0x7f800000,0xff800000,0x7fc12345};
 for(unsigned n=0;n<512;n++){
  unsigned op=n%4,canon=(n/4)%2;
  uint32_t a=n<272?edge[(n/4)%17]:next(),b=n<272?edge[(n/16+7)%17]:next();
  if(n<16){a=0x80000000;b=op==0?0x80000000:0x3f800000;}
  unsigned err=0;uint32_t y=0;
  if((a&0x7f800000)==0x7f800000||(op!=3&&(b&0x7f800000)==0x7f800000)||
     (op==2&&(b&0x7fffffff)==0)||(op==3&&(a>>31)&&(a&0x7fffffff)))err=1;
  else{
   volatile float x=f(a),z=f(b);float result=op==0?x+z:op==1?x*z:op==2?x/z:std::sqrt(x);
   y=bits(result);if(!std::isfinite(result)){err=2;y=0;}
   if(canon&&(y&0x7fffffff)==0)y=0;
  }
  std::printf("%x %08x %08x %x %08x %x\n",op,a,b,canon,y,err);
 }
}
