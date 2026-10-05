from pathlib import Path
import subprocess,os
ROOT=Path(__file__).resolve().parents[1]
CPP=r'''
#include "s81_minimum_source_tags_component.hpp"
#include "dsrom_vm_tag227.hpp"
#include <cassert>
#include <cstdlib>
using namespace dsrom_s81_minimum;
template<class F>void reject(F f){bool x=false;try{f();}catch(const std::exception&){x=true;}assert(x);}
int main(int argc,char**argv){assert(argc==2);setenv("DSROM_S81_MINIMUM_SELECTED_DIR",argv[1],1);
 DsromS81MinimumRuntime r{};r.stage=0;r.rank=0;r.pair=0;r.cycle=[](){return 1;};
 auto tags=dsrom_s81_bind_minimum_source_tags(r,1ull<<31);reject([&]{dsrom_s81_bind_minimum_source_tags(r,1ull<<31);});
 S81EmbeddingOutput out{};out.vm_valid=1;out.vm_identity=1ull<<31;out.vm_address=1;
 for(unsigned i=0;i<16;++i)out.vm_data[i]=0xabcdef00u+i;
 std::array<MacroWrite,16> held;
 for(unsigned i=0;i<16;++i){held[i]=tags.record(out,i);assert(held[i].word.owner==tags.record(out,i).word.owner);
  for(unsigned j=0;j<i;++j)assert(held[i].word.owner!=held[j].word.owner);}
 // Bank1 accepts scalar16 before the bank0 scalars1..15; no lane-order assumption.
 tags.scalar_accept(1,held[15]);
 for(unsigned i=0;i<15;++i){auto bad=held[i];bad.word.data[(i+1)&15]^=1;reject([&]{tags.scalar_accept(0,bad);});tags.scalar_accept(0,held[i]);}
 reject([&]{tags.scalar_accept(0,held[0]);});
 auto read=tags.read_owner(1ull<<31,65);reject([&]{tags.read_accept(64,read);});tags.read_accept(65,read);reject([&]{tags.read_accept(65,read);});
 auto native=dsrom_s81_reserve_native_scalar_tag(r,1ull<<31,6,46464,0x81234567);
 tags.scalar_accept((46464>>4)&3,native);
 auto newer=dsrom_s81_reserve_native_scalar_tag(r,1ull<<31,3,46464,0x81234567);
 assert(newer.word.owner!=native.word.owner);tags.scalar_accept((46464>>4)&3,newer);
 ReturnPhaseBinding b{};b.stage=0;b.rank=0;b.pair=0;b.phase=0;b.root=0;b.identity=1ull<<31;b.emitted_key="0";
 CaptureOwner c{1ull<<31,0,0,0,0,51680};
 auto rt=tags.root_owner(b,c);MacroWrite root{};root.source=c;root.word.address=51680>>4;root.word.mask=1;root.word.owner=rt;
 tags.scalar_accept((51680>>4)&3,root);
 b.pair=1;reject([&]{tags.root_owner(b,c);});r.stage=1;reject([&]{tags.read_owner(1ull<<31,65);});
}
'''
def test_real_cicero_binding_signature_all_writer_tags_and_actual_acceptance(tmp_path):
 headers=ROOT/'results/uarch/dsrom_minimum_source_tags_20261004/interface'
 legacy=headers
 p=tmp_path/'test.cpp';p.write_text(CPP);exe=tmp_path/'test'
 subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror','-I',str(ROOT/'tools/runtime/dsrom'),'-I',str(headers),'-I',str(legacy),'-I',str(ROOT/'tools/native'),str(p),str(ROOT/'tools/runtime/dsrom/s81_minimum_source_tags_component.cpp'),'-o',str(exe)],check=True,capture_output=True)
 selected=tmp_path/'selected';selected.mkdir();(selected/'spine_phase.hex').write_text(f'{22517998140008448:x}\n0\n');(selected/'e0.cfg.hex').write_text('0\n')
 subprocess.run([str(exe),str(selected)],check=True)
