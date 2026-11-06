#include <stdint.h>
#include <stdio.h>
static uint8_t csa(uint8_t a,uint8_t b,uint8_t pr,int mutant){
 uint8_t d=~pr,s=a^b^d,c=((a&b)|(a&d)|(b&d))<<1;
 uint8_t p=s^c,g=s&c,pp=p;
 for(int shift=1;shift<=4;shift*=2){uint8_t ng=g|(pp&(g<<shift));uint8_t np=(pp&((1<<shift)-1))|(pp&(pp<<shift));g=ng;pp=np;}
 return p^(((g|pp)<<1)|(mutant?0:1));
}
int main(void){
 unsigned long long algebra=0,lookup=0,carry=0,mutant=0,total=0;
 for(unsigned rank=0;rank<256;rank++)for(unsigned gb=0;gb<256;gb++)for(unsigned pf=0;pf<256;pf++){
  uint8_t old=-(uint8_t)((uint8_t)(rank-gb)*pf);
  uint8_t parallel=(uint8_t)(gb*pf)-(uint8_t)(rank*pf);
  uint8_t lo=(gb-(rank&15))*pf,hi=-(int)((rank>>4)*pf);
  uint8_t table=lo+((hi&15)<<4);
  algebra+=old!=parallel;lookup+=old!=table;
  mutant+=old!=(uint8_t)(parallel+1);total++;
 }
 unsigned long long csa_mut=0;
 for(unsigned f=0;f<256;f++)for(unsigned gbpf=0;gbpf<256;gbpf++)for(unsigned rankpf=0;rankpf<256;rankpf++){
  uint8_t expected=f+gbpf-rankpf;
  carry+=csa(f,gbpf,rankpf,0)!=expected;
  csa_mut+=csa(f,gbpf,rankpf,1)!=expected;
 }
 printf("{\"cases_each\":%llu,\"parallel_diff\":%llu,\"lookup_diff\":%llu,\"csa_diff\":%llu,\"offset_mutant_diff\":%llu,\"carry_mutant_diff\":%llu}\n",total,algebra,lookup,carry,mutant,csa_mut);
 return algebra||lookup||carry||!mutant||!csa_mut;
}
