import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import uarch_model as U
BASE=ROOT/'results/uarch/dsrom_s81_native_he_bootstrap_20261004'
API=BASE/'source_factory_interfaces'


def test_corrected_source_model_and_historical_component_retained():
 new=U.dsrom_s81_native_he_bootstrap_source()
 assert new['PF']['raw_FP32_words']==[0x3f800000,0,0,0]
 assert U.dsrom_s81_native_he_bootstrap()['PF']['raw_FP32_words']==[0x3f800000]*4
 assert new['adapter']['raw_cached_H_bytes']==81920
 assert new['adapter']['scalar_serial_read_service_edges_model']==122880
 assert new['adapter']['raw_H_cache_register_floor_mm2']>0
 assert new['corrected_source_factory_symbol']=='dsrom_s81_bind_minimum_he_bootstrap'
 assert new['combined_single_user_added_us'] is None


def test_actual_factory_symbol_and_reserved_tag_dependency(tmp_path):
 obj=tmp_path/'provider.o'
 subprocess.run(['g++','-std=c++17','-c','-I'+str(API),'-I'+str(ROOT/'tools/runtime/dsrom'),
                 str(ROOT/'tools/runtime/dsrom/s81_minimum_he_bootstrap_provider.cpp'),'-o',str(obj)],check=True)
 symbols=subprocess.check_output(['nm','-C',str(obj)],text=True)
 assert ' T dsrom_s81_bind_minimum_he_bootstrap(' in symbols
 assert ' U dsrom_s81_reserve_native_scalar_tag(' in symbols
 assert ' U s81_native_he_bootstrap_rise' in symbols
 assert ' U s81_native_he_bootstrap_fall' in symbols
 assert ' U s81_native_he_bootstrap_eval' not in symbols


def test_shared_edge_and_arm_controls_executable(tmp_path):
 # Protocol-only controls. These test callbacks never implement FP arithmetic
 # and provide no native numeric qualification; actual leaf runs are separate.
 source=r'''
#include "s81_native_he_bootstrap_source.hpp"
#include <cassert>
static unsigned rises=0,falls=0,evals=0,valids=0,admissions=0;
static unsigned observed_reset=0;
extern "C" void* s81_native_he_bootstrap_create(){return reinterpret_cast<void*>(1);}
extern "C" void s81_native_he_bootstrap_destroy(void*){}
extern "C" void s81_native_he_bootstrap_eval(void*,const S81NativeHeBootstrapInput*,S81NativeHeBootstrapOutput*){++evals;}
extern "C" void s81_native_he_bootstrap_rise(void*,const S81NativeHeBootstrapInput*i,S81NativeHeBootstrapOutput*o){
 ++rises;observed_reset=i->reset_n;if(i->reset_n&&i->ssx_valid)++valids;*o={};
 // An injected raw output tests control/publication only, never arithmetic.
 if(valids==80){o->ssx_we=1;o->ssx_addr=40960;o->ssx_data=0x12345678;valids++;}
}
extern "C" void s81_native_he_bootstrap_fall(void*,const S81NativeHeBootstrapInput*,S81NativeHeBootstrapOutput*){++falls;}
int main(){
 DsromS81NativeHeBootstrapSourcePorts p;
 p.H_visible=[](auto){return true;};p.H_read=[](auto,auto){return std::optional<std::array<uint32_t,256>>(std::array<uint32_t,256>{});};
 p.inputs_ready=[](const auto&){return false;};p.bootstrap_accepted=[](){++admissions;};
 p.memory_prepare=[](auto,const auto&,auto&){};p.fault=[](){return false;};
 std::vector<std::pair<uint32_t,uint32_t>> scalars;
 p.scalar_offer=[&](auto,auto a,auto d){scalars.push_back({a,d});return true;};
 p.scalar_visible=[](auto,auto,auto){return true;};
 p.HE_offer=[](auto,auto,auto,const auto&){return false;};p.HE_visible=p.HE_offer;
 DsromS81NativeHeBootstrapSource native(1,p);auto b=native.participant();auto h=native.engine();
 bool rejected=false;try{native.arm();}catch(const std::runtime_error&){rejected=true;}assert(rejected);
 b.prepare({});b.rising(false);b.falling(false);
 for(unsigned n=0;n<3;n++){b.prepare({});b.rising(true);b.falling(true);h.participant.prepare({});h.participant.rising(true);h.participant.falling(true);}
 assert(valids==0&&evals==0&&rises==4&&falls==4);
 native.arm();rejected=false;try{native.arm();}catch(const std::runtime_error&){rejected=true;}assert(rejected);
 for(unsigned n=0;n<86;n++){b.prepare({});b.rising(true);b.falling(true);}
 assert(admissions==1&&evals==0&&scalars.size()==5);
 assert(scalars[0]==std::make_pair(40960u,0x12345678u));
 for(unsigned n=0;n<4;n++)assert(scalars[n+1]==std::make_pair(41152u+n,n==0?0x3f800000u:0u));
 assert(native.cold_visible());assert(!h.inputs_ready(DsromS81PrefixOperation{}));
}
'''
 p=tmp_path/'control.cpp';p.write_text(source);binary=tmp_path/'control'
 subprocess.run(['g++','-std=c++17','-I'+str(API),'-I'+str(ROOT/'tools/runtime/dsrom'),str(p),'-o',str(binary)],check=True)
 subprocess.run([str(binary)],check=True)


def test_source_interface_archive_byte_pins():
 pins=json.loads((API/'manifest.json').read_text())
 for path,pin in pins.items():assert hashlib.sha256((API/path).read_bytes()).hexdigest()==pin['sha256']
