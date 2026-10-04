from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[1]
CPP=r'''
#include "dsrom_vm_tag227_accept_mapping.hpp"
#include <cassert>
using namespace dsrom::component_tag227;
template<class F>void reject(F f){bool x=false;try{f();}catch(const std::exception&){x=true;}assert(x);}
struct Word {unsigned address,mask;Tag227 owner;};
struct Source {unsigned element_address;std::uint64_t identity;unsigned phase;};
struct MacroWrite {Word word;Source source;};
int main(){
 SourceOffer s{1ull<<31,0,80,3,2416,1023,16383};PlannedTagReservations p(1,0);
 std::vector<PlannedTagReservations::Plan> plans;
 for(unsigned i=0;i<16;++i)plans.push_back({s,PlannedTagReservations::Kind::ScalarWrite,i});
 auto tags=p.reserve(plans);assert(p.actual_accepted_count()==0&&p.planned_count()==16);
 for(unsigned i=0;i<16;++i){assert(unpack(tags[i]).request_id==i);for(unsigned j=0;j<i;++j)assert(tags[i]!=tags[j]);}
 reject([&]{p.qualified_retire(tags[0]);});reject([&]{p.next_batch();});
 auto read=p.reserve({{s,PlannedTagReservations::Kind::Read64,64}});assert(unpack(read[0]).request_id==16);
 reject([&]{p.reserve({{s,PlannedTagReservations::Kind::ScalarWrite,100}});});assert(p.actual_accepted_count()==0);
 // Actual bank order intentionally differs from scalar/lane order.
 for(unsigned bank=0;bank<4;++bank)for(unsigned lane=0;lane<4;++lane){unsigned i=lane*4+bank;
  auto actual=PlannedTagReservations::Actual{tags[i],PlannedTagReservations::Kind::ScalarWrite,i,10};
  reject([&]{p.actual_accept(actual,s,false);});
  auto wrong=actual;wrong.scalar_address=100;reject([&]{p.actual_accept(wrong,s,true);});
  auto changed=s;changed.accepted_pair=2415;reject([&]{p.actual_accept(actual,changed,true);});
  p.actual_accept(actual,s,true);reject([&]{p.actual_accept(actual,s,true);});
 }
 assert(p.actual_accepted_count()==16);assert(unpack(p.actual_accept_order()[1].owner).request_id==4);
 p.actual_accept({read[0],PlannedTagReservations::Kind::Read64,64,11},s,true);
 for(auto& t:tags){p.qualified_retire(t);}
 p.qualified_retire(read[0]);assert(p.batch_retired());
 p.next_batch();auto t=p.reserve({{s,PlannedTagReservations::Kind::ScalarWrite,0}})[0];assert(unpack(t).batch==1);
 reject([&]{p.actual_accept({tags[0],PlannedTagReservations::Kind::ScalarWrite,0,12},s,true);});
 PlannedAcceptMapping map(1,0);auto sealed=map.reserve(plans);
 for(unsigned i=0;i<16;++i){auto record=MacroWrite{{i>>4,1u<<(i&15),sealed[i]},{i,s.identity47,unsigned(s.accepted_phase)}};
  auto wrong=record;wrong.word.mask=0;reject([&]{map.scalar((i>>4)&3,wrong,20);});
  map.scalar((i>>4)&3,record,20);
 }
 auto rd=map.reserve({{s,PlannedTagReservations::Kind::Read64,64}})[0];
 reject([&]{map.read(4,rd,21);});map.read(64,rd,21);assert(map.actual_accepted_count()==17);
 PlannedAcceptMapping arbitrary(1,0);
 auto unaligned=arbitrary.reserve({{s,PlannedTagReservations::Kind::ReadElement,65}})[0];
 reject([&]{arbitrary.read(64,unaligned,1);});arbitrary.read(65,unaligned,1);
 // Invalid multi-command construction does not leave a partial reservation.
 PlannedTagReservations q(1,0);auto bad=s;bad.accepted_pair=2417;
 reject([&]{q.reserve({{s,PlannedTagReservations::Kind::ScalarWrite,0},{bad,PlannedTagReservations::Kind::ScalarWrite,1}});});
 assert(q.planned_count()==0&&q.actual_accepted_count()==0);
}
'''
def test_planned_reservation_is_distinct_from_actual_bank_acceptance(tmp_path):
 s=tmp_path/'test.cpp';s.write_text(CPP);b=tmp_path/'test'
 subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror','-I',str(ROOT/'tools/native'),str(s),'-o',str(b)],check=True,capture_output=True)
 subprocess.run([str(b)],check=True)
