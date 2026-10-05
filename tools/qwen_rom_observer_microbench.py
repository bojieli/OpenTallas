#!/usr/bin/env python3
import pathlib,sys,json,re,time,subprocess,os
import argparse
ap=argparse.ArgumentParser(description='Fixture-only passive observer overhead measurement; not an RTL run');ap.add_argument('--read-samples',type=int,default=0);ap.add_argument('--prepared',type=pathlib.Path,required=True);ap.add_argument('--workdir',type=pathlib.Path,required=True);ap.add_argument('--result',type=pathlib.Path,required=True);a=ap.parse_args()
root=pathlib.Path(__file__).resolve().parents[1];out=a.workdir;out.mkdir(exist_ok=False)
prep=a.prepared;meta=json.loads((prep/'preparation.json').read_text())
access=re.search(r'#if QROM_OBSERVER\nstatic void qrom_pre.*?\n#endif', (prep/'qwen_rom_rt_observed.cpp').read_text(),re.S).group()
fields='\n'.join('volatile unsigned '+n+'=0;' for n in meta['generated_root_endpoints'])
(out/'Vdie___024root.h').write_text('#pragma once\nstruct Root{'+fields+'};\n')
header=root/'rtl/test/qwen_rom_runtime/observer/qwen_rom_observer.hpp'
cpp=f'''#define QROM_OBSERVER 1
#include "{header}"
#include <chrono>
#include <cstdio>
struct Vdie{{Root* rootp;unsigned prog_base=0;unsigned long long desc_q=0;}};
{access}
struct Values{{unsigned at(unsigned)const{{return 0;}}}};
int main(){{QromObserver o;Root r;Vdie d{{&r}};unsigned f[24]={{}};
auto a=std::chrono::steady_clock::now();for(int i=0;i<1000000;++i)qrom_pre(o,d,i,0,0);auto b=std::chrono::steady_clock::now();
unsigned values[16]={{}};for(int i=0;i<{a.read_samples};++i)o.read(i,0,0,0,0,0,values);
for(int i=0;i<3744;++i)o.issue(i,0,0,0,0,i,1,f);
for(int i=0;i<73728;++i)o.write(i,0,0,i,0);
for(int i=0;i<144;++i)o.snapshot(i,0,0,Values{{}});
auto c=std::chrono::steady_clock::now();std::printf("%.9f %.9f\\n",std::chrono::duration<double>(b-a).count(),std::chrono::duration<double>(c-b).count());}}
'''
(out/'bench.cpp').write_text(cpp)
t=time.monotonic();subprocess.run(['/usr/bin/time','-f','%M','-o',str(out/'compile.rss'),'g++','-std=c++20','-O2','-I'+str(out),str(out/'bench.cpp'),'-o',str(out/'bench')],check=True,capture_output=True);build=time.monotonic()-t
p=subprocess.run([str(out/'bench')],env=dict(os.environ,RT_QROM_JOURNAL=str(out/'fixture-format.raw')),text=True,capture_output=True,check=True);idle,formatted=map(float,p.stdout.split())
r={'status':'PASS_OBSERVER_MICROBENCH_FIXTURE_ONLY','idle_samples':1000000,'idle_sample_seconds':idle,'formatted_record_seconds':formatted,'formatted_records':3744+73728*2+1+a.read_samples,'read_samples':a.read_samples,'formatted_bytes':(out/'fixture-format.raw').stat().st_size,'native_fixture_compile_seconds':build,'native_fixture_compile_RSS_KiB':int((out/'compile.rss').read_text()),'actual_RTL_runtime_measured':False,'benchmark_is_actual_journal':False,'source_cpp_sha256':__import__('hashlib').sha256(cpp.encode()).hexdigest()}
with a.result.open('x') as f:f.write(json.dumps(r,sort_keys=True,indent=2)+'\n')
print(json.dumps({k:v for k,v in r.items() if k!='source_cpp_sha256'}))
