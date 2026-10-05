#!/usr/bin/env python3
"""Fabricated concurrent formatter regression; no DUT/provider evidence."""
import argparse,hashlib,json,os,re,subprocess,time
from pathlib import Path

HEADER=re.compile(rb'R (\d+) (\d+) (\d+) (\d+) (\d+) (\d+)')

def probe(header,work):
 work.mkdir(exist_ok=False);(work/'Vdie___024root.h').write_text('#pragma once\n')
 code='''#define QROM_OBSERVER 1
#include "HEADER"
#include <thread>
#include <atomic>
#include <vector>
int main(){QromObserver o;std::atomic<unsigned> ready{0};std::vector<std::thread> ts;
for(unsigned t=0;t<16;++t)ts.emplace_back([&,t]{ready.fetch_add(1);while(ready.load()!=16)std::this_thread::yield();
for(unsigned i=0;i<512;++i){unsigned a=t*1024+i,v[16];for(unsigned l=0;l<16;++l)v[l]=a*16+l;o.read(i,0,0,t,i%4,a,v);}});
for(auto& t:ts)t.join();}
'''.replace('HEADER',str(header.resolve()))
 (work/'probe.cpp').write_text(code)
 subprocess.run(['g++','-std=c++20','-O2','-pthread','-I'+str(work),str(work/'probe.cpp'),'-o',str(work/'probe')],check=True,capture_output=True)
 started=time.monotonic();subprocess.run([str(work/'probe')],env=dict(os.environ,RT_QROM_JOURNAL=str(work/'fixture.raw')),check=True,capture_output=True);elapsed=time.monotonic()-started
 raw=(work/'fixture.raw').read_bytes();seen=set();bad=0
 for line in raw.splitlines():
  a=line.split()
  try:
   if len(a)!=23 or a[0]!=b'R':raise ValueError('record width')
   edge,stage,rank,tile,group,address=map(int,a[1:7])
   if (stage,rank,group,address)!=(0,0,edge%4,tile*1024+edge) or not 0<=tile<16 or not 0<=edge<512:raise ValueError('identity')
   if [int(v,16) for v in a[7:]]!=[address*16+l for l in range(16)]:raise ValueError('mixed payload')
   if (tile,edge) in seen:raise ValueError('duplicate')
   seen.add((tile,edge))
  except ValueError:bad+=1
 headers=[tuple(map(int,m.groups())) for m in HEADER.finditer(raw)]
 expected={(i,0,0,t,i%4,t*1024+i) for t in range(16) for i in range(512)}
 return {'status':'PASS_ALL8192_CONCURRENT_RECORDS' if bad==0 and len(seen)==8192 else 'FAIL_INTERLEAVED_CONCURRENT_RECORDS','malformed_lines':bad,'valid_records':len(seen),'whole_atomic_headers_recovered':len(headers)==8192 and set(headers)==expected,'header_count':len(headers),'formatted_bytes':len(raw),'seconds':elapsed,'header_sha256':hashlib.sha256(header.read_bytes()).hexdigest(),'fixture_source_sha256':hashlib.sha256(code.encode()).hexdigest(),'raw_sha256':hashlib.sha256(raw).hexdigest(),'DUT_or_provider_run':False}

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--header',type=Path,required=True);p.add_argument('--workdir',type=Path,required=True);p.add_argument('--receipt',type=Path,required=True);a=p.parse_args()
 result=probe(a.header,a.workdir)
 with a.receipt.open('x') as f:json.dump(result,f,sort_keys=True,indent=2);f.write('\n')
 print(json.dumps(result,sort_keys=True))

if __name__=='__main__':main()
