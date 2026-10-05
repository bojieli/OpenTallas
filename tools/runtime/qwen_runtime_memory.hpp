#pragma once
#include <cstdint>
#include <vector>
#include <fstream>
#include <string>
#include <stdexcept>
#include <algorithm>
struct QwenRuntimeMemory {
 struct Read { uint32_t address; size_t response_slot; };
 struct Write { uint32_t address,value; };
 std::vector<uint32_t> words, response;
 struct Edge { std::vector<uint32_t> response;std::vector<Write> writes; };
 explicit QwenRuntimeMemory(size_t size,size_t slots=1):words(size),response(slots){}
 static uint32_t hex32(const std::string&s,size_t start,size_t count){return static_cast<uint32_t>(std::stoul(s.substr(start,count),nullptr,16));}
 // readmemh: @address counts packed words, least-significant element comes last.
 static std::vector<uint32_t> load_hex(const std::string& path,size_t words_per_line){
  std::ifstream f(path);if(!f)throw std::runtime_error("open "+path);
  std::vector<uint32_t> data;std::string line;size_t row=0;
  while(std::getline(f,line)){
   auto comment=line.find("//");if(comment!=std::string::npos)line.resize(comment);
   auto first=line.find_first_not_of(" \t\r");if(first==std::string::npos)continue;
   line=line.substr(first);line.resize(line.find_last_not_of(" \t\r")+1);
   if(line[0]=='@'){row=std::stoull(line.substr(1),nullptr,16);continue;}
   if(line.size()>words_per_line*8)throw std::runtime_error("wide hex row "+path);
   data.resize(std::max(data.size(),(row+1)*words_per_line));
   for(size_t i=0;i<words_per_line;i++){
    size_t end=line.size()>8*i?line.size()-8*i:0;
    data[row*words_per_line+i]=end?hex32(line,end>8?end-8:0,std::min(size_t(8),end)):0;
   }
   row++;
  }
  return data;
 }
 Edge capture(const std::vector<Read>&reads,const std::vector<Write>&ordered_writes)const{
  Edge edge{response,ordered_writes};
  // All reads see pre-edge state, including collisions with writes this edge.
  for(auto r:reads){if(r.address>=words.size()||r.response_slot>=response.size())throw std::out_of_range("memory read");edge.response[r.response_slot]=words[r.address];}
  for(auto w:ordered_writes)if(w.address>=words.size())throw std::out_of_range("memory write");
  return edge;
 }
 void commit_after_rtl_edge(const Edge&edge){
  response=edge.response;
  // Existing TB NBA priority: increasing ME group/lane, MX, SU, RD, TP write.
  for(auto w:edge.writes)words[w.address]=w.value;
 }
};
