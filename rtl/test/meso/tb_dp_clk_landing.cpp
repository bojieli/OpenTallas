#include "Vtb_dp_clk_landing.h"
#include "verilated.h"
#include <cstdio>
#include <cstdlib>
#include <vector>
#include <algorithm>
struct Word { unsigned value; long time; };
int main(int argc,char** argv) {
  Verilated::commandArgs(argc,argv);
  int phase=argc>1?atoi(argv[1]):0;
  int wneg=argc>2?atoi(argv[2]):0;   // S81-RINGHOLD-3: build with -GWNEG=1 and pass 1 (falling-edge ring write)
  Vtb_dp_clk_landing m;
  m.clk=0;m.fclk=0;m.rst_n=0;m.d=0;m.eval();
  std::vector<Word> writes;
  unsigned input=1, errors=0, checks=0;
  long minage=1000000000,maxage=-1; int shift=-1;
  // Integer ps, exact 833ps period. Falling edges alternate 416/417ps.
  for(long t=0;t<833L*1200;t++) {
    if(t==833L*8 || t==833L*608) m.rst_n=1;
    if(t==833L*600) m.rst_n=0;
    bool fr=t%833==0, ff=t%833==416;
    bool rr=t>=phase&&(t-phase)%833==0;
    bool rf=t>=phase&&(t-phase)%833==416;
    if(ff)m.fclk=0;
    if(rf)m.clk=0;
    if(fr){m.fclk=1;writes.push_back({input,t});m.d=input++;}
    if(rr)m.clk=1;
    m.eval();
    if(rr&&m.ready) {
      checks++;
      auto it=std::find_if(writes.rbegin(),writes.rend(),[&](const Word&w){return w.value==m.q;});
      if(it==writes.rend()){if(errors++<4)printf("BAD_WORD t=%ld q=%u\n",t,(unsigned)m.q);continue;}
      long age=t-it->time;minage=std::min(minage,age);maxage=std::max(maxage,age);
      // Exact zero-phase source-edge-to-ring-output mapping, independently fixed.
      // WNEG: the ring writes on the falling fclk edge, 417 ps after the source edge = the rising-edge law at read phase
      // (phase-416) mod 833, 417 ps shorter.  Phase 0 sits on the half-period placement boundary: either side is legal.
      int ph1=(phase+833-416)%833; long want=wneg?((ph1<=416?3332:2499)+ph1-417):((phase<=416?3332:2499)+phase);
      if(wneg&&phase==0&&age==want+833)want=age;
      if(age!=want){if(errors++<4)printf("BAD_LAG t=%ld age=%ld q=%u\n",t,age,(unsigned)m.q);}
      if(m.fault){if(errors++<4)printf("FAULT t=%ld\n",t);}
    }
  }
  printf("phase=%d checks=%u errors=%u min_age_ps=%ld max_age_ps=%ld\n",phase,checks,errors,minage,maxage);
  return errors||checks<100?1:0;
}
