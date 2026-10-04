import subprocess
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
FIELDS=[('identity47',47,0),('token17',17,47),('stage7',7,64),('rank2',2,71),('pair12',12,73),('phase10',10,85),('entry14',14,95),('reset_era',32,169),('batch',16,201),('request_id',10,217)]
CPP=r'''
#include "dsrom_vm_tag227_source_hook.hpp"
#include <cassert>
#include <iostream>
#include <string>
using namespace dsrom::component_tag227;
template<class F> void rejects(F f){bool threw=false;try{f();}catch(const std::exception&){threw=true;}assert(threw);}
int main(int argc,char**argv){
 std::string mode=argv[1];
 if(mode=="pack"){
  assert(argc==12);std::uint64_t x[10];for(int i=0;i<10;++i)x[i]=std::stoull(argv[i+2]);
  try{
   Envelope e{{x[0],x[1],x[2],x[3],x[4],x[5],x[6]},x[7],x[8],x[9]};auto t=pack(e);
   assert(pack(unpack(t))==t);
   for(auto word:t){std::cout<<word<<" ";}
   std::cout<<"\n";
  }catch(const std::exception&){return 2;}return 0;
 }
 auto c=experiment_context(80,3,2416,1023,16383);
 if(mode=="banks"){
  std::array<std::uint32_t,29> bus{};std::array<Tag227,4> tags;
  for(unsigned b=0;b<4;++b){tags[b]=pack({c,1,b,b+1});copy_bank_to(tags[b],b,bus);}
  for(unsigned b=0;b<4;++b)assert(read_bank_from(bus,b)==tags[b]);
  auto changed=pack({c,2,42,100});copy_bank_to(changed,1,bus);
  assert(read_bank_from(bus,1)==changed);
  for(unsigned b:{0u,2u,3u})assert(read_bank_from(bus,b)==tags[b]);
  std::array<std::uint32_t,8> rd{};copy_to(changed,rd);assert(read_from(rd)==changed);
  rejects([&]{copy_bank_to(changed,4,bus);});
  auto corrupted=changed;corrupted[4]|=1u<<13;rejects([&]{unpack(corrupted);});
  corrupted=changed;corrupted[7]|=8u;rejects([&]{unpack(corrupted);});
 }
 if(mode=="hook"){
  SourceOffer s{std::uint64_t{1}<<31,0,80,3,2416,1023,16383};SourceOfferHook h(s,1,0);
  auto first=h.tag_for_offer(s);assert(!h.on_backend_accept(true,false,s,first));
  assert(h.tag_for_offer(s)==first && h.outstanding()==0);
  rejects([&]{h.on_backend_accept(false,true,s,first);});assert(h.outstanding()==0);
  auto wrong=s;wrong.accepted_pair=2415;rejects([&]{h.tag_for_offer(wrong);});
  rejects([&]{h.on_backend_accept(true,true,wrong,first);});assert(h.outstanding()==0);
  assert(h.on_backend_accept(true,true,s,first));assert(h.outstanding()==1);
  rejects([&]{h.on_backend_accept(true,true,s,first);});assert(h.outstanding()==1);
  rejects([&]{h.next_batch();});auto e=unpack(first);e.reset_era=2;
  rejects([&]{h.on_qualified_retirement(pack(e));});assert(h.outstanding()==1);
  h.on_qualified_retirement(first);rejects([&]{h.on_qualified_retirement(first);});
  h.next_batch();assert(unpack(h.tag_for_offer(s)).batch==1);
 }
 if(mode=="limits"){
  AcceptedIdLedger l(c,1,0);
  for(unsigned i=0;i<1024;++i){auto t=l.offer_tag();assert(unpack(t).request_id==i);l.actual_accept(t);l.qualified_retire(t);}
  rejects([&]{l.offer_tag();});l.next_batch();assert(unpack(l.offer_tag()).request_id==0);
  assert(unpack(l.offer_tag()).batch==1);
  AcceptedIdLedger last(c,0xffffffffu,65535);rejects([&]{last.next_batch();});
  rejects([&]{last.reset_after_quiescence(0x100000000ull,true);});
  rejects([&]{last.reset_after_quiescence(0,false);});
  auto t=last.offer_tag();last.actual_accept(t);rejects([&]{last.reset_after_quiescence(0x100000000ull,true);});
  last.qualified_retire(t);
  AcceptedIdLedger reset(c,1,0);reset.reset_after_quiescence(2,true);assert(unpack(reset.offer_tag()).reset_era==2);
  rejects([&]{reset.reset_after_quiescence(2,true);});
 }
 std::cout<<"OK\n";
}
'''

@pytest.fixture(scope='module')
def binary(tmp_path_factory):
    p=tmp_path_factory.mktemp('tag227');src=p/'test.cpp';src.write_text(CPP)
    exe=p/'test'
    subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror','-I',str(ROOT/'tools/native'),str(src),'-o',str(exe)],check=True,capture_output=True,text=True)
    return exe

@pytest.mark.parametrize('values',[
 [1<<31,0,0,0,0,0,0,1,0,0],
 [(1<<47)-1,(1<<17)-1,80,3,2416,1023,16383,0xffffffff,65535,1023],
 [0x456789abcdef,0x13579,37,2,2400,622,12000,0x12345678,0xabcd,999],
])
def test_exact_bitpacking_against_independent_integer_oracle(binary,values):
    r=subprocess.run([str(binary),'pack',*map(str,values)],capture_output=True,text=True,check=True)
    expected=sum(v<<offset for v,(_,_,offset) in zip(values,FIELDS))
    assert list(map(int,r.stdout.split()))==[(expected>>(32*i))&0xffffffff for i in range(8)]

@pytest.mark.parametrize('field',range(10))
def test_field_overflow_rejects_without_truncation(binary,field):
    values=[1<<31,0,0,0,0,0,0,1,0,0];values[field]=1<<FIELDS[field][1]
    r=subprocess.run([str(binary),'pack',*map(str,values)],capture_output=True,text=True)
    assert r.returncode==2 and not r.stdout

@pytest.mark.parametrize('field,value',[(2,81),(4,2417)])
def test_source_stage_pair_bounds_not_legacy_expert9(binary,field,value):
    values=[1<<31,0,0,0,0,0,0,1,0,0];values[field]=value
    assert subprocess.run([str(binary),'pack',*map(str,values)],capture_output=True).returncode==2

@pytest.mark.parametrize('mode',['banks','hook','limits'])
def test_bank_segments_actual_acceptance_and_unique_id_lifetime(binary,mode):
    assert subprocess.run([str(binary),mode],check=True,capture_output=True,text=True).stdout=='OK\n'
