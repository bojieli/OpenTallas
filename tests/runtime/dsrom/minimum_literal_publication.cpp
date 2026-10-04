#include "s81_prefix_publication.hpp"
#include <cassert>
using namespace dsrom_s81_minimum;
template<class F>void reject(F f){bool bad=false;try{f();}catch(const std::exception&){bad=true;}assert(bad);}
int main(){
 PrefixPublication pub(17);
 pub.enroll_literal(29,{{41120,16}});assert(!pub.complete(29));
 pub.begin(17,29);assert(!pub.complete(29));
 for(unsigned a=41120;a<41136;++a){
  MacroWrite w{};w.source.identity=17;w.source.element_address=a;
  w.word.address=a>>4;w.word.mask=1u<<(a&15);w.word.owner[0]=a;w.word.data[a&15]=0x3f800000;
  pub.native_scalar(29,w,true);assert(!pub.source_span_lease(17,a,1));
  VmReceipt r{};r.address=w.word.address;r.mask=w.word.mask;r.owner=w.word.owner;
  pub.on_prefix_scalar_ack(w,r);assert(pub.source_span_lease(17,a,1));
 }
 assert(pub.complete(29));
 // Enrolling a rewrite does not publish it; real GO revokes old version.
 pub.enroll_literal(30,{{41120,16}});assert(pub.source_span_lease(17,41120,16));
 pub.begin(17,30);assert(!pub.source_span_lease(17,41120,1)&&!pub.complete(30));
 PrefixPublication malformed(17);reject([&]{malformed.enroll_literal(7,{{10,1}});});
 reject([&]{malformed.enroll_literal(31,{{10,2},{11,1}});});
 reject([&]{malformed.enroll_literal(31,{{(1u<<19)-1,2}});});
}
