#include "row_backend.hpp"
#include <iostream>
using namespace qwen_actual_phy;
int main(int argc,char**argv){try{
 VerilatedContext ctx;ctx.commandArgs(argc,argv);RowBackend b(ctx,8191);
 std::vector<RowIdentity> identities;
 for(unsigned kind=0;kind<2;kind++)for(unsigned layer: {0u,17u,35u})identities.push_back({41,layer,8191,kind});
 std::map<uint64_t,RowBytes> expected;std::map<uint64_t,RowIdentity> requested;
 for(auto id:identities)for(unsigned q=0;q<4;q++){Quarter d{};for(unsigned j=0;j<8;j++)d[j]=(id.layer+1)*0x1020304u+id.kind*0x12345u+q*211+j;b.enqueue_quarter({id,q},d);}
 bool premature=false;try{b.request_row(identities[0]);}catch(const std::runtime_error&){premature=true;}
 if(!premature)throw std::runtime_error("current row read admitted before ACK");
 bool preload_rejected=false;try{b.declare_prior_quarter({identities[0],0},Codeword{});}catch(const std::runtime_error&){preload_rejected=true;}
 if(!preload_rejected)throw std::runtime_error("current token preload admitted");
 // Independent explicit map probes span every PC and stack, layer/kind bounds.
 for(unsigned t=0;t<512;t++)for(unsigned q=0;q<4;q++)for(unsigned kind=0;kind<2;kind++){
  QuarterIdentity id{{41,35,t,kind},q};auto p=native_map(id);
  unsigned sec=(35<<11)|(kind<<10)|(((t>>6)&1)<<8)|((t>>9)<<3)|((t>>3)&7);
  unsigned bank=(((sec>>8)&7)<<2)|(sec&3),col=(sec>>2)&31;
  if(p.stack!=((t>>7)&3)||p.pc!=8*q+(t&7)||p.bank!=bank||p.col!=col||p.row!=99)throw std::runtime_error("mapped quarter mismatch");
 }
 bool issued=false;unsigned received=0;uint64_t ack_count=0;
 for(unsigned n=0;n<30000;n++){
  b.advance_one_event();WriteAck ack;while(b.pop_write_ack(ack)){if(ack.identity.row.epoch!=41)throw std::runtime_error("ACK epoch identity");ack_count++;}
  if(!issued&&ack_count==24){issued=true;for(auto id:identities){auto ticket=b.request_row(id);RowBytes d{};for(unsigned q=0;q<4;q++)for(unsigned j=0;j<8;j++)d[8*q+j]=(id.layer+1)*0x1020304u+id.kind*0x12345u+q*211+j;expected[ticket]=d;requested[ticket]=id;}}
  RowReturn row;while(b.pop_row(row)){
   if(row.data!=expected.at(row.ticket)||row.identity.epoch!=41||row.identity.layer!=requested.at(row.ticket).layer||row.identity.kind!=requested.at(row.ticket).kind)throw std::runtime_error("assembled actual row payload or identity mismatch");received++;
  }
  if(received==identities.size()){std::cout<<"PASS BACKEND128 map_checks=4096 actual_quarter_writes="<<b.write_issues<<" actual_WDONE_ack="<<b.write_acks<<" actual_quarter_reads="<<b.read_quarters<<" assembled_rows="<<b.row_returns<<" row_bytes=128 current_token_preload_refused=1 early_read_refused=1 ck="<<b.core_edges<<" hclk="<<b.hbm_edges<<"\n";return 0;}
 }
 throw std::runtime_error("backend row progress missing");
 }catch(const std::exception&e){std::cout<<"FAIL BACKEND128 "<<e.what()<<"\n";return 1;}}
