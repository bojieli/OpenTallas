// Simulation-only passive host observer. Compiled out unless explicitly enabled.
#pragma once
#ifndef QROM_OBSERVER
#define QROM_OBSERVER 0
#endif
#if QROM_OBSERVER
#include "Vdie___024root.h"
#include <cstdio>
#include <cstdlib>
#include <stdexcept>
struct QromObserver {
 struct RecordLock { FILE* f; explicit RecordLock(FILE* v):f(v){::flockfile(f);} ~RecordLock(){::funlockfile(f);} RecordLock(const RecordLock&)=delete; RecordLock& operator=(const RecordLock&)=delete; };
 FILE* file=nullptr; bool active[4]={}; unsigned last_flags[4]={255,255,255,255}; size_t last_stage[4]={37,37,37,37};
 QromObserver() {
  const char* path=std::getenv("RT_QROM_JOURNAL");
  if(!path) throw std::runtime_error("enabled observer needs exclusive RT_QROM_JOURNAL path");
  file=std::fopen(path,"wx"); if(!file) throw std::runtime_error("refusing existing/unwritable journal");
 }
 ~QromObserver(){if(file)std::fclose(file);}
 void dispatch(char kind,long edge,size_t stage,int rank,unsigned seg,unsigned base,unsigned long long desc){
  RecordLock record(file);
  std::fprintf(file,"%c %ld %zu %d %u %u %016llx\n",kind,edge,stage,rank,seg,base,desc);
 }
 void control(long edge,size_t stage,int rank,unsigned flags){
  RecordLock record(file);
  if(last_flags[rank]!=flags || last_stage[rank]!=stage){
   std::fprintf(file,"B %ld %zu %d %u\n",edge,stage,rank,flags);last_flags[rank]=flags;last_stage[rank]=stage;
  }
 }
 void issue(long edge,size_t stage,int rank,unsigned seg,unsigned base,unsigned pc,unsigned unit,const unsigned* fields){
  RecordLock record(file);
  std::fprintf(file,"I %ld %zu %d %u %u %u %u",edge,stage,rank,seg,base,pc,unit);
  if(unit==1)for(int i=0;i<24;++i)std::fprintf(file," %u",fields[i]);
  std::fputc('\n',file);
 }
 void write(long edge,size_t stage,int rank,unsigned address,unsigned value){
  RecordLock record(file);
  std::fprintf(file,"W %ld %zu %d %u %08x\n",edge,stage,rank,address,value);
 }
 void read(long edge,size_t stage,int rank,unsigned tile,unsigned group,unsigned address,const unsigned* values){
  RecordLock record(file);
  std::fprintf(file,"R %ld %zu %d %u %u %u",edge,stage,rank,tile,group,address);
  for(unsigned lane=0;lane<16;++lane)std::fprintf(file," %08x",values[lane]);
  std::fputc('\n',file);
 }
 template<class Values>void snapshot(long edge,size_t stage,int rank,const Values& kv){
  RecordLock record(file);
  // Actual committed FP32 host values, not reconstructed producer output.
  for(unsigned kind=0;kind<2;++kind)for(unsigned head=0;head<2;++head)for(unsigned dim=0;dim<128;++dim){
   unsigned a=kind?2097152+head*8192*128+dim:head*512*128*16+dim*16;
   std::fprintf(file,"K %ld %zu %d %u %08x\n",edge,stage,rank,a,unsigned(kv.at(a)));
  }
  if(std::fflush(file))throw std::runtime_error("journal flush failed");
 }
};
#endif
