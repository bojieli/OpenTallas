import subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def test_actual_host_workspace_carry_holds_source_and_partial_writes(tmp_path):
    source=tmp_path/'workspace.cpp'
    source.write_text(r'''
#include <cassert>
#include <array>
#include <tuple>
#include "dsrom_s81_workspace.hpp"
struct Source {
 int reads=0;
 uint32_t vm_word(int address) {
  assert(address>=100 && address<103);reads++;
  uint32_t x[3]={0x80000000u,0x7f800000u,0x7fc00001u};return x[address-100];
 }
};
struct Target {
 bool allow=false;std::vector<std::tuple<uint64_t,uint32_t,uint32_t>> writes;
 bool c8_workspace_write(uint64_t identity,uint32_t address,uint32_t raw) {
  if(!allow)return false;
  writes.emplace_back(identity,address,raw);allow=false;return true;
 }
};
int main() {
 const uint64_t s=(17ull<<31)|(3ull<<21)|100;
 const uint64_t t=(18ull<<31)|(3ull<<21)|100;
 DsromS81Workspace w(12,s,100,148,t,600,3);Source src;Target dst;bool visible=false;
 auto visibility=[&](int die,uint64_t id,uint32_t address,size_t count) {
  assert(die==12 && id==s && address==100 && count==3);return visible;
 };
 assert(!w.capture(src,12,visibility) && src.reads==0);
 assert(w.load(dst,148,3)==0 && !w.setup_complete());
 visible=true;assert(w.capture(src,12,visibility) && src.reads==3);
 assert(w.capture(src,12,visibility) && src.reads==3);
 assert(w.load(dst,148,3)==0);
 for(int i=0;i<3;i++){dst.allow=true;assert(w.load(dst,148,3)==1);}
 assert(w.setup_complete() && w.identity()==t && dst.writes.size()==3);
 uint32_t expected[3]={0x80000000u,0x7f800000u,0x7fc00001u};
 for(int i=0;i<3;i++){assert(std::get<0>(dst.writes[i])==t);assert(std::get<1>(dst.writes[i])==600u+i);assert(std::get<2>(dst.writes[i])==expected[i]);}
 bool rejected=false;try {w.load(dst,147,1);}catch(const std::runtime_error&){rejected=true;}assert(rejected);
 rejected=false;try {DsromS81Workspace bad(12,s,0,148,1ull<<47,0,1);}catch(const std::runtime_error&){rejected=true;}assert(rejected);
 rejected=false;try {DsromS81Workspace bad(12,s,0,148,t,(1u<<19)-1,2);}catch(const std::runtime_error&){rejected=true;}assert(rejected);
}
''')
    exe=tmp_path/'workspace'
    subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror',
                    '-I'+str(ROOT/'rtl/test/v41_runtime/s81_selected'),
                    '-I'+str(ROOT/'rtl/test/v41_runtime'),str(source),'-o',str(exe)],check=True)
    subprocess.run([str(exe)],check=True)
