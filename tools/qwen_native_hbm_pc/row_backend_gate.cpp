#include "row_backend.hpp"
#include <iostream>
using namespace qwen_actual_phy;
Codeword declare_code(const Quarter&d){
 Codeword c{};
 for(unsigned lane=0;lane<4;lane++){
  uint64_t data=uint64_t(d[2*lane])|(uint64_t(d[2*lane+1])<<32);bool v[72]{};unsigned j=0;
  for(unsigned p=1;p<=71;p++)if(p&(p-1))v[p-1]=(data>>j++)&1;
  for(unsigned k=0;k<7;k++)for(unsigned p=1;p<=71;p++)if((p&(1u<<k))&&p!=(1u<<k))v[(1u<<k)-1]^=v[p-1];
  for(unsigned i=0;i<71;i++)v[71]^=v[i];
  for(unsigned i=0;i<72;i++)put(c.data(),lane*72+i,1,v[i]);
 }
 return c;
}
int main(int argc,char**argv){bool data_mut=argc>1&&std::string(argv[1])=="data_mut";bool map_mut=argc>1&&std::string(argv[1])=="map_mut";try{
 VerilatedContext ctx;ctx.commandArgs(argc,argv);RowBackend b(ctx,8191);
 std::vector<RowIdentity> identities;
 for(unsigned kind=0;kind<2;kind++)for(unsigned layer: {0u,17u,35u})identities.push_back({41,layer,8191,kind});
 std::map<uint64_t,RowBytes> expected;std::map<uint64_t,RowIdentity> requested;
 for(auto id:identities)for(unsigned q=0;q<4;q++){Quarter d{};for(unsigned j=0;j<8;j++)d[j]=(id.layer+1)*0x1020304u+id.kind*0x12345u+q*211+j;auto p=native_map({id,q});if(map_mut)p.bank^=1;b.enqueue_mapped_quarter({id,q},d,p);}
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
 // Declared prior DRAM image touches all128 actual controller instances.
 std::map<uint64_t,RowBytes> prior_expected;
 for(unsigned stack=0;stack<4;stack++)for(unsigned low=0;low<8;low++){
  RowIdentity id{40,17,128*stack+low,0};RowBytes row{};
  for(unsigned q=0;q<4;q++){Quarter d{};for(unsigned j=0;j<8;j++)row[8*q+j]=d[j]=0x12345678u+id.pos*977+q*37+j;b.declare_prior_quarter({id,q},declare_code(d));}
  auto ticket=b.request_row(id);prior_expected[ticket]=row;
 }
 if(data_mut)b.physical_backing(127).corrupt_read=true;
 bool issued=false;unsigned received=0,prior_received=0;uint64_t ack_count=0;
 for(unsigned n=0;n<30000;n++){
  b.advance_one_event();WriteAck ack;while(b.pop_write_ack(ack)){if(ack.identity.row.epoch!=41)throw std::runtime_error("ACK epoch identity");ack_count++;}
  if(!issued&&ack_count==24){issued=true;for(auto id:identities){auto ticket=b.request_row(id);RowBytes d{};for(unsigned q=0;q<4;q++)for(unsigned j=0;j<8;j++)d[8*q+j]=(id.layer+1)*0x1020304u+id.kind*0x12345u+q*211+j;expected[ticket]=d;requested[ticket]=id;}}
  RowReturn row;while(b.pop_row(row)){
   if(prior_expected.count(row.ticket)){if(row.data!=prior_expected.at(row.ticket)||row.identity.epoch!=40)throw std::runtime_error("prior DRAM row mismatch");prior_received++;continue;}
   if(row.data!=expected.at(row.ticket)||row.identity.epoch!=41||row.identity.layer!=requested.at(row.ticket).layer||row.identity.kind!=requested.at(row.ticket).kind)throw std::runtime_error("assembled actual row payload or identity mismatch");received++;
  }
  if(received==identities.size()&&prior_received==32){std::cout<<"PASS BACKEND128 map_checks=4096 actual_quarter_writes="<<b.write_issues<<" actual_WDONE_ack="<<b.write_acks<<" actual_quarter_reads="<<b.read_quarters<<" assembled_rows="<<b.row_returns<<" prior_declared_quarters="<<b.declared_preloads<<" all_PC_read_traffic=128<<" row_bytes=128 current_token_preload_refused=1 early_read_refused=1 ck="<<b.core_edges<<" hclk="<<b.hbm_edges<<"\n";if(data_mut||map_mut)throw std::runtime_error("mutant escaped observation");return 0;}
 }
 throw std::runtime_error("backend row progress missing");
 }catch(const std::exception&e){std::cout<<(data_mut||map_mut?"OBSERVED_FAIL BACKEND128 ":"FAIL BACKEND128 ")<<e.what()<<"\n";return (data_mut||map_mut)?0:1;}}
