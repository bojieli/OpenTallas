#include "VDsromS81IndexWriter.h"
#include "VDsromS81IndexHbm.h"
#include "svdpi.h"
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <array>
#include <cstdint>
static void need(bool v,const char*s){if(!v)throw std::runtime_error(s);}
template<class T> void put(T& x,unsigned off,unsigned width,uint32_t v){for(unsigned b=0;b<width;++b){auto &w=x[(off+b)/32];unsigned k=(off+b)%32;w=(w&~(1u<<k))|(((v>>b)&1u)<<k);}}
int main(int argc,char**argv){try{
 need(argc==4,"corrected prior dir / actual I35 input / comparison-only raw boundary sectors required");
 VerilatedContext ctx;ctx.threads(1);
 VDsromS81IndexWriter w(&ctx,"writer");VDsromS81IndexHbm m(&ctx,"backend");
 w.clk=m.clk=0;w.rst_n=m.rst_n=0;w.su_go=0;w.kv_we={};w.kv_waddr={};w.kv_wdata={};
 w.cfg_ik_base=0;w.i_user_base_sec=0;w.i_dst=3;w.i_obase=0;w.i_orow=1048575;w.i_nout=1;w.i_kdim=128;
 m.w_v=0;m.r_v={};m.r_addr={};m.r_len={};m.r_tag={};for(unsigned j=0;j<4;++j)m.r_rsp_rdy[j]=~0u;
 uint64_t cycles=0;unsigned record_accepts=0;
 auto join=[&](){m.w_v=w.w_v;m.w_csec=w.w_v?w.w_csec-786432:0;m.w_ssec=w.w_ssec;
  m.w_codes=w.w_codes;m.w_scales=w.w_scales;m.w_sslot=w.w_sslot;m.eval();w.w_rdy=m.w_rdy;w.eval();};
 auto low=[&](){m.clk=w.clk=0;m.eval();w.eval();join();join();};
 auto tick=[&](){low();if(m.w_v&&m.w_rdy)++record_accepts;m.clk=w.clk=1;m.eval();w.eval();ctx.timeInc(1);++cycles;
  need(!m.fault&&!w.fault,"actual native writer/backend fault");low();};
 tick();tick();
 auto scope=svGetScopeFromName("backend.DsromS81IndexHbm");need(scope,"actual backend preload scope missing");svSetScope(scope);
 VDsromS81IndexHbm::s81_index_preload_ring(argv[1]);m.eval();need(m.history_ready,"history not ready");
 w.rst_n=m.rst_n=1;tick();
 std::array<uint32_t,128> input{};std::ifstream f(argv[2],std::ios::binary);f.read((char*)input.data(),512);need(f.gcount()==512&&f.peek()==EOF,"actual I35 extent");
 for(auto v:input)need((v&65535)==0,"I35 needs native SU rounding; cannot bypass arithmetic");
 // Actual I36 is IND store; these actual BF16 words are unchanged by its BF16 store.
 w.su_go=1;tick();w.su_go=0;
 const uint32_t base=(1048575u>>4)*128u*16u+(1048575u&15u);
 for(unsigned j=0;j<128;++j){put(w.kv_we,j,1,1);put(w.kv_waddr,j*30,30,base+j*16);w.kv_wdata[j]=input[j];}
 tick();w.kv_we={};
 while(!(record_accepts==1&&w.dbg_keys==1&&!w.w_v&&!m.busy&&m.dbg_migrations==1&&m.dbg_copied_sectors==102))tick();
 const auto append_end=cycles;
 std::ifstream expected(argv[3]);need(bool(expected),"comparison-only boundary payload unavailable");
 unsigned stack,address,count=0;std::string hex;
 while(expected>>stack>>address>>hex){need(stack<3&&hex.size()==64,"comparison sector shape");
  unsigned pc=stack*32+(((address>>2)^(address>>7)^(address>>12))&31);
  put(m.r_addr,pc*30,30,address);put(m.r_len,pc*4,4,1);put(m.r_tag,pc*16,16,1);put(m.r_v,pc,1,1);
  low();while(!((m.r_rdy[pc/32]>>(pc%32))&1u))tick();tick();put(m.r_v,pc,1,0);low();
  while(!((m.r_rsp_v[pc/32]>>(pc%32))&1u))tick();
  need(((m.r_rsp_tag[pc/2]>>(16*(pc%2)))&65535)==1,"native readback tag");
  for(unsigned j=0;j<8;++j){auto v=std::stoul(hex.substr(56-8*j,8),nullptr,16);need(m.r_rsp_data[pc*8+j]==v,"postappend boundary payload mismatch");}
  ++count;tick();
 }
 need(count==102&&record_accepts==1,"exact six migration group scope");
 std::cout<<"PASS_NATIVE_APPEND_48_BOUNDARY_KEY_PAYLOADS cycles="<<cycles<<" append_end="<<append_end
  <<" records="<<record_accepts<<" migrations="<<m.dbg_migrations<<" copied_sectors="<<m.dbg_copied_sectors
  <<" checked_sectors="<<count<<" score_arithmetic_not_rerun=1 actual_I35_store_boundary=1\n";
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
