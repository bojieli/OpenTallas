from pathlib import Path
import importlib.util,json,subprocess
ROOT=Path(__file__).resolve().parents[1]
CPP=r'''
#include "dsrom_sun256_prefetch.hpp"
#include <cassert>
using namespace dsrom::sun256;
template<class F>void reject(F f){bool threw=false;try{f();}catch(const std::exception&){threw=true;}assert(threw);}
int main(){
 auto tag=dsrom::component_tag227::pack({dsrom::component_tag227::experiment_context(0,0,0,0,0),1,0,0});
 std::optional<ReadRequest> driven;std::optional<ReadAccepted> accept;std::optional<ReadReply> reply;bool lease=true;
 auto mk=[&](){return VmReadPort{[&](auto r){driven=r;},[&](){auto a=accept;accept.reset();return a;},[&](){auto r=reply;reply.reset();return r;},[&](){return lease;},[](){return false;}};};
 OperandStage s(mk(),[&](){return tag;});s.begin({64});s.prepare();assert(driven&&driven->scalar_base==64&&!s.ready());
 s.prepare();assert(driven->owner==tag);reject([&]{s.read(64);});
 accept=ReadAccepted{*driven,10};s.prepare();assert(!driven&&!s.ready());
 ReadReply r{64,tag,{},14};for(unsigned i=0;i<64;++i)r.words[i]=0x81234500u|i;
 reply=r;s.prepare();assert(s.ready()&&s.read(65)==0x81234501u);
 reject([&]{s.read(0);});lease=false;reject([&]{s.read(64);});lease=true;
 s.finish_after_native_drain();
 OperandStage early(mk(),[&](){return tag;});early.begin({64});early.prepare();accept=ReadAccepted{*driven,20};early.prepare();r.source_postNBA_edge=23;reply=r;reject([&]{early.prepare();});assert(early.fault());
 OperandStage stale(mk(),[&](){return tag;});stale.begin({64});stale.prepare();accept=ReadAccepted{*driven,30};stale.prepare();r.source_postNBA_edge=34;r.owner[0]^=1;reply=r;reject([&]{stale.prepare();});assert(stale.fault());
 OperandStage bounded(mk(),[&](){return tag;});reject([&]{bounded.begin(std::vector<std::uint32_t>(321,64));});reject([&]{bounded.begin({64,64});});
 OutputStage out;out.capture(46464,0x12345678,false);out.capture(51616,0xabcdef00,true);
 reject([&]{out.qualified_visible({51616,0xabcdef00,true});});assert(out.held().size()==2);
 out.qualified_visible({46464,0x12345678,false});out.qualified_visible({51616,0xabcdef00,true});assert(out.empty());
}
'''
def test_actual_prefetch_response_latency_identity_hold_and_publication(tmp_path):
 s=tmp_path/'test.cpp';s.write_text(CPP);b=tmp_path/'test'
 subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror','-I',str(ROOT/'tools/native'),str(s),'-o',str(b)],check=True,capture_output=True)
 subprocess.run([str(b)],check=True)

def test_prefix_model_fullshape_extents_and_positive_staging_cost():
 spec=importlib.util.spec_from_file_location('su_model',ROOT/'tools/dsrom_sun256_native_prefix_model.py')
 m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);d=m.generate()
 assert json.loads((m.E/'model.json').read_text())==d
 assert d['parameters']['N']==256 and d['parameters']['LV']==7 and d['parameters']['M']==64
 assert d['capacity_check']['selected_vectors']==20 and d['capacity_check']['rejected_N16_vectors']==320
 assert max(r['staged_words'] for r in d['prefix_operations'])==10368
 assert sum(r['raw_only_prefetch_elapsed_edges_no_stall'] for r in d['prefix_operations'])==3426
 assert d['extra_staging']['payload_bits']>0 and d['extra_staging']['output_collect_data_address_bits']>0
 assert not d['hardware_or_rate_admission']
