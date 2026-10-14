#include "include/qkd_host_board_router_fixture.hpp"
#include <iostream>
using namespace qkd_host_fixture;
struct Pins {
 bool rst_n=true,host_rst_n=true,core_rx_v=false,core_rx_cr=false,core_tx_v=false,core_tx_cr=false,phy_rx_v=false,phy_tx_v=false;
 Word528 core_rx_d{},core_tx_d{};Flit1043 phy_rx_flit{},phy_tx_flit{};
};
void check(bool ok,const char* why){if(!ok)throw std::runtime_error(why);}
int main(){try {
 Router router;std::array<Pins,8> b{},h{};std::array<Pins*,8> bp{},hp{};
 for(unsigned i=0;i<8;++i){bp[i]=&b[i];hp[i]=&h[i];}
 Payload status1{},status2{};status1[0]=0x01010121;status2[0]=0x01020121;
 b[1].core_rx_v=b[2].core_rx_v=true;b[1].core_rx_d=packet(1,status1);b[2].core_rx_d=packet(1,status2);
 router.sample_core(bp);router.drive_core(bp);
 check(b[1].core_rx_cr&&b[2].core_rx_cr,"real fixture receive reservation");
 check(b[0].core_tx_v&&b[0].core_tx_d[0]==status1[0],"first ordered CTRL destination");
 for(auto& p:b)p.core_rx_v=false;
 Payload credit{};credit[0]=0x100;b[0].core_rx_v=true;b[0].core_rx_d=packet(7,credit);b[0].core_tx_cr=true;
 router.sample_core(bp);router.drive_core(bp);
 check(b[0].core_tx_v&&b[0].core_tx_d[0]==status2[0],"second ordered CTRL destination");
 check(b[1].core_tx_v&&b[1].core_tx_d[16]==0x7000&&b[1].core_tx_d[0]==0x100,"destination credit returned only to original source1");
 check(!b[2].core_tx_v,"source2 not credited from source1 completion");
 router.sample_core(bp);router.drive_core(bp);
 check(b[2].core_tx_v&&b[2].core_tx_d[0]==0x100,"second owner returned to source2");
 bool caught=false;try{router.sample_core(bp);}catch(const std::runtime_error&){caught=true;}
 check(caught,"duplicate destination credit rejected");
 router.reset_all();for(auto& p:b){p=Pins{};}
 router.pause_ctrl_destination(7,true);check(router.enqueue(7,1,status1),"delayed peer enqueue");
 for(unsigned i=0;i<1000;++i){router.sample_core(bp);router.drive_core(bp);check(!b[7].core_tx_v,"paused peer cannot consume delayed request");}
 router.pause_ctrl_destination(7,false);router.drive_core(bp);check(b[7].core_tx_v,"genuine peer reservation after release");
 router.reset_all();for(auto& p:b)p=Pins{};
 Payload ingest{};for(unsigned n=0;n<64;++n)check(router.enqueue(0,4,ingest),"bounded independent ING reservation");
 check(!router.enqueue(0,4,ingest),"ING capacity cannot grow unbounded");
 b[1].core_rx_v=true;b[1].core_rx_d=packet(1,status1);router.sample_core(bp);
 check(b[1].core_rx_cr,"full ING cannot exclude actual CTRL receive reservation");
 b[1].core_rx_v=false;
 for(unsigned n=0;n<17;++n){router.drive_core(bp);if(n<16)check((b[0].core_tx_d[16]>>12)==4,"initial ING real logical window");else check(b[0].core_tx_v&&b[0].core_tx_d[0]==status1[0],"stalled ING cannot block independent CTRL");b[0].core_tx_cr=true;router.sample_core(bp);}
 router.reset_all();for(auto& p:b)p=Pins{};
 Payload write{};write[0]=0x0114;put64(write,1,0x800);put64(write,3,0xdeadbeef87654321ull);write[5]=15;
 router.store64(0x800,0xaabbccdd11223344ull);b[0].core_rx_v=true;b[0].core_rx_d=packet(0,write);router.sample_core(bp);
 check(router.load64(0x800)==0xaabbccdd87654321ull&&router.dma_writes()==1,"actual DMA byte mask");
 router.fmt1_descriptor(0x100,0x400,{0x22222,0x15555,0x23333},1);
 check(router.load64(0x100)==0x00010003cafe0101ull,"original FMT1 descriptor");
 check(router.load64(0x400)==0x0001555500022222ull&&router.load64(0x408)==0x23333,"actual FMT1 prompt32 fields");
 router.reset_all();for(auto& p:b)p=Pins{};
 h[0].phy_tx_v=true;h[0].phy_tx_flit[0]=0x12345678;h[0].phy_tx_flit[32]=0x40000;
 router.step_phy(hp,bp);check(!b[0].phy_rx_v,"first real link stage");h[0].phy_tx_v=false;
 for(unsigned i=1;i<223;++i){router.step_phy(hp,bp);check(!b[0].phy_rx_v,"FDI delay not shortened");}
 router.step_phy(hp,bp);check(b[0].phy_rx_v&&b[0].phy_rx_flit[0]==0x12345678&&b[0].phy_rx_flit[32]==0x40000,"all actual1043 FDI bits retained after223 stages");
 std::cout<<"PASS BOARD_ROUTER_FIXTURE ownership/destination-credit/duplicate/delayedpeer7/DMA/FMT1/FDI223; PIN_FIXTURE_ONLY\n";
 return 0;
 }catch(const std::exception& e){std::cerr<<e.what()<<"\n";return 1;}}
