#include "verilated.h"
#include "VDsromL20WoaDecode.h"
#include "s81_L20_native_me_matrix.hpp"
#include <iostream>
int main(){
 VerilatedContext context;
 bool poison=false;
 DsromL20MeNativeConversion<VDsromL20WoaDecode> converter(&context,
   [&](unsigned,unsigned){std::array<uint32_t,9> raw{};
     for(unsigned i=0;i<8;++i)raw[i]=poison?0x7f7f7f7f:0x7f387f38;
     return raw;});
 auto p=converter.participant();p.prepare({});p.rising(false);p.falling(false);
 converter.request(1,17);if(converter.ready())return 1;
 try{converter.read(1,17);return 2;}catch(const std::runtime_error&){}
 p.prepare({});p.rising(true);p.falling(true);
 auto out=converter.read(1,17);
 for(unsigned i=0;i<8;++i)if(out[i]!=0x3f803f80)return 3;
 if(out[8]||p.fault())return 4;
 converter.retire(1,17);poison=true;converter.request(1,18);
 p.prepare({});p.rising(true);p.falling(true);
 if(!p.fault()||converter.ready())return 5;
 try{converter.read(1,18);return 6;}catch(const std::runtime_error&){}
 DsromL20MeConvertedMatrix<VDsromL20WoaDecode> image(&context,
   [](unsigned,unsigned){std::array<uint32_t,9> raw{};for(unsigned i=0;i<8;++i)raw[i]=0x7f387f38;return raw;},2);
 auto ip=image.participant();ip.prepare({});ip.rising(false);ip.falling(false);
 try{image.seal();return 7;}catch(const std::runtime_error&){}
 for(unsigned row=0;row<2;++row){image.request(0,row);ip.prepare({});ip.rising(true);ip.falling(true);image.materialize();}
 image.seal();if(image.read(0,1)[0]!=0x3f803f80)return 8;
 try{image.request(0,2);return 9;}catch(const std::runtime_error&){}
 try{image.read(0,2);return 10;}catch(const std::runtime_error&){}
 std::cout<<"ACTUAL_NATIVE_16_LANES_PASS completed=16 poison=16 no_private_tick=1\n";
}
