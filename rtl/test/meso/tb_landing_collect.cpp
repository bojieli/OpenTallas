#include "Vtb_landing_collect.h"
#include "verilated.h"
#include <cstdio>
// Cycle model of tb_landing_collect: u_a (direct children, 2 status cycles to the root) and u_b behind the
// same-region face flops (3 status cycles). Random phase = exact register model; handshake phase = ready/fault
// arrival cycles after a reset release (DIE-S81-29 +1 status cycle on the face branch only).
struct Ref{bool fr=0,ff=0,ar=0,af=0,br=0,bf=0,orr=0,of=0;
    void edge(bool rst,unsigned r,unsigned f){
        bool nfr=(r>>2)&1,nff=(f>>2)&1;
        if(!rst){ar=af=br=bf=orr=of=0;}
        else{bool o=ar&&br,fo=af||bf;ar=(r&3)==3;af=(f&3)!=0;br=fr;bf=ff;orr=o;of=fo;}
        fr=nfr;ff=nff;}};
int main(int argc,char**argv){
    Verilated::commandArgs(argc,argv);Vtb_landing_collect m;Ref ref;
    unsigned errors=0,checks=0,n=0;
    auto step=[&](bool rst,unsigned r,unsigned f){
        m.clk=0;m.rst_n=rst;m.ready_i=r;m.fault_i=f;m.eval();m.clk=1;m.eval();ref.edge(rst,r,f);checks++;
        if(m.ready_o!=ref.orr||m.fault_o!=ref.of){if(errors++<4)printf("DIFF n=%u got=%d/%d expected=%d/%d\n",n,m.ready_o,m.fault_o,ref.orr,ref.of);}
        n++;};
    for(unsigned k=0;k<512;k++){bool rst=k>=4&&!(k>=250&&k<256);step(rst,(k*5)&7,(k*3+1)&7);}
    // handshake: senders are reset with the receiver (ready 0). The direct children report ready first; the
    // same-region child's ready (bit 2, behind the face flop) rises last -> ready_o high 3 edges after it
    // (face 1 + u_b 2 + root 3; without the face flop: 2). Reverse order: bit 2 first, direct last -> 2 edges.
    for(int k=0;k<4;k++)step(false,0,0);for(int k=0;k<4;k++)step(true,3,0);
    int rise=-1;for(int k=0;k<8;k++){step(true,7,0);if(rise<0&&m.ready_o)rise=k+1;}
    printf("handshake ready rise after face-branch ready edge=%d (expect 3)\n",rise);if(rise!=3)errors++;
    for(int k=0;k<4;k++)step(false,0,0);for(int k=0;k<4;k++)step(true,4,0);
    int rise2=-1;for(int k=0;k<8;k++){step(true,7,0);if(rise2<0&&m.ready_o)rise2=k+1;}
    printf("handshake ready rise after direct ready edge=%d (expect 2)\n",rise2);if(rise2!=2)errors++;
    // fault on the face branch reaches the root 3 edges later, on a direct child 2 edges later
    int fz=-1;for(int k=0;k<6;k++){step(true,7,4);if(fz<0&&m.fault_o)fz=k+1;}
    printf("face-branch fault edge=%d (expect 3)\n",fz);if(fz!=3)errors++;
    for(int k=0;k<4;k++)step(false,7,0);for(int k=0;k<6;k++)step(true,7,0);
    int fd=-1;for(int k=0;k<6;k++){step(true,7,1);if(fd<0&&m.fault_o)fd=k+1;}
    printf("direct-branch fault edge=%d (expect 2)\n",fd);if(fd!=2)errors++;
    // a face-branch ready drop removes root ready 3 edges later
    for(int k=0;k<4;k++)step(true,7,0);int dz=-1;
    for(int k=0;k<6;k++){step(true,3,0);if(dz<0&&!m.ready_o)dz=k+1;}
    printf("face-branch ready drop edge=%d (expect 3)\n",dz);if(dz!=3)errors++;
    printf("collector checks=%u errors=%u\n",checks,errors);return errors?1:0;
}
