// s81-die-rtl-bind 2026-10-14: die-name PQ slot dsfd_sp_pq_n (native core + ROM macro ties + x-lane leaf) in
// lockstep with the bare production core ot_s81_pq_core_native, same stimulus as tb_s81_pq_core_native.cpp.
//   reference: the bench's two-cycle ROM model (word of address(t) at edge t + 2) on the core's rom_* pins
//   die model: a ONE-cycle macro model (ot_rom_4096x72_m8: rd_out <= word(addr_in) at the edge) on ra*/rq*:
//              address from a core flop at t, macro at t + 1, core capture at t + 2 = the same two cycles
// Every cycle: issuer status, x read request, mdr, ROM addresses equal the reference; the lane words xw / xe one cycle
// after f_bus equal the die-lane encoding of the reference f_bus written HERE independently
// (x0 = {qv, sv, qp, p, qb, e0, q0}, x1 = {e1, q1}, cc = {np, 0, ph, cfg, go}, valid = qv | go | cfg).
#include <cstdio>
#include <cstdint>
#include <cstring>
#include <deque>
#include <vector>
#include "Vcore.h"
#include "Vdie.h"
#include "verilated.h"

struct Stim {
    uint8_t reset=0, go=0, np=0, rv=0;
    uint16_t ph=0;
    uint64_t pq0=0,pq1=0,sq=0;
    uint32_t x[64]={},ga[6]={};
};
static void setb(uint32_t* p,int bit,int n,uint64_t v){for(int i=0;i<n;i++){int b=bit+i;if((v>>i)&1)p[b/32]|=1u<<(b%32);else p[b/32]&=~(1u<<(b%32));}}
static uint64_t bits(const uint32_t* p,int bit,int n){uint64_t x=0;for(int i=0;i<n;i++){int b=bit+i;x|=uint64_t((p[b/32]>>(b%32))&1)<<i;}return x;}
static void drive_core(Vcore& m,const Stim& s){
    m.rst_n=s.reset;m.go=s.go;m.i_np=s.np;m.i_ph=s.ph;
    m.i_xbase=64;m.i_xps=8192;m.i_obase=98304;m.i_ops=2048;m.i_fmt=0;
    m.x_rv=s.rv;m.f_fault=0;m.q2f_i=0;m.rom_pq0=s.pq0;m.rom_pq1=s.pq1;m.rom_sq=s.sq;
    for(int i=0;i<64;i++)m.x_q[i]=s.x[i];
    for(int i=0;i<6;i++)m.ga_i[i]=s.ga[i];
}
static void drive_die(Vdie& m,const Stim& s,uint64_t q0,uint64_t q1,uint64_t q2){
    m.rst=s.reset;
    uint32_t* f=m.f_iss.data();std::memset(f,0,sizeof(uint32_t)*3);
    setb(f,0,1,s.go);setb(f,1,9,s.ph);setb(f,10,3,s.np);setb(f,13,19,64);setb(f,32,19,8192);setb(f,51,19,98304);
    setb(f,70,19,2048);setb(f,89,2,0);setb(f,91,1,0);
    uint32_t* v=m.f_vm.data();v[0]=s.rv;
    for(int i=0;i<64;i++){setb(v,1+32*i,32,s.x[i]);}
    uint32_t* c=m.f_cnt.data();std::memset(c,0,sizeof(uint32_t)*7);
    for(int i=0;i<6;i++)setb(c,32*i,32,s.ga[i]);
    m.rq0=q0;m.rq1=q1;m.rq2=q2;m.xws=3;m.xes=3;
}
template<class M> void clk(M& m,int v){
    m.ck_ctl=m.ck_qb=m.ck_fault=v;m.ck_aq=v?3:0;m.ck_ix=v?15:0;m.ck_bc=v?(sizeof(m.ck_bc)>1?65535:15):0;
    if constexpr(requires {m.ck_ix_read;}) m.ck_ix_read=v?0xffffffffU:0;
    if constexpr(requires {m.ck_aq_aux;}) m.ck_aq_aux=v?65535:0;
    if constexpr(requires {m.ck_qb_aux;}) m.ck_qb_aux=v?15:0;
    if constexpr(requires {m.ck_lane;}) m.ck_lane=v;
}
template<class M> void tick(M& m){clk(m,0);m.eval();clk(m,1);m.eval();}
// die lane word of a 1,633-b native broadcast
static void encode(const uint32_t* fb,uint32_t* w){
    std::memset(w,0,sizeof(uint32_t)*18);
    uint64_t cfg=bits(fb,1632,1),ph=bits(fb,1623,9),np=bits(fb,1620,3),go=bits(fb,1619,1),qv=bits(fb,1615,1),p=bits(fb,1607,8),
             qb=bits(fb,1604,3),sv=bits(fb,1602,2),e0=bits(fb,1336,10),e1=bits(fb,1070,10),qp=bits(fb,1067,3);
    setb(w,0,1,qv|go|cfg);
    for(int i=0;i<256;i++)setb(w,1+i,1,bits(fb,1346+i,1));        // x0.q0
    setb(w,257,10,e0);setb(w,267,3,qb);setb(w,270,8,p);setb(w,278,3,qp);setb(w,281,2,sv);setb(w,283,1,qv);
    for(int i=0;i<256;i++)setb(w,284+i,1,bits(fb,1080+i,1));      // x1.q1
    setb(w,540,10,e1);
    setb(w,550,1,go);setb(w,551,1,cfg);setb(w,552,9,ph);setb(w,561,1,0);setb(w,562,3,np);
}
int main(int argc,char**argv){
    Verilated::commandArgs(argc,argv);
    uint64_t compared=0,lane_words=0,lane_q=0,lane_go=0,lane_cfg=0,reads=0;
    for(int test=0;test<4;test++){
        Vcore r;Vdie d;Stim s;
        int fam=test&1,np=(test>>1),phase=257+test*37;
        static uint64_t prom[4096],srom[4096];
        std::memset(prom,0,sizeof(prom));std::memset(srom,0,sizeof(srom));
        int nb=192,base=test*512;
        prom[2*phase]=uint64_t(fam)|(6144ull<<1)|(uint64_t(nb)<<14)|(uint64_t(base)<<30)|(32ull<<46);
        for(int k=0;k<nb;k++){
            uint64_t w=1;
            if(fam){w|=uint64_t(k%8)<<1;w|=15ull<<4;for(int g=0;g<4;g++)w|=uint64_t((k+13*g)%48)<<(8*(g+1));}
            else{w|=uint64_t((k/8)%12)<<1;w|=uint64_t(k%8)<<9;w|=3ull<<12;for(int g=2;g<5;g++)w|=uint64_t((k/8)%12)<<(8*g);}
            srom[base+k]=w;
        }
        uint16_t pa0=0,pa1=0,sa=0;uint64_t p0delay=0,p1delay=0,sdelay=0;
        uint64_t m0=0,m1=0,m2=0;           // die macros' outputs (data of the address registered at the last edge)
        std::deque<std::pair<int,uint32_t>> pending;
        struct Return{int at,tag,total;};std::deque<Return> returns;
        int issued=0,seen_go=0,last_issue=-100,idles=0;bool finished=false;
        uint32_t prev_enc[18];bool have_prev=false;
        for(int c=0;c<30000;c++){
            s.reset=c>=16;s.go=0;s.rv=0;std::memset(s.ga,0,sizeof(s.ga));
            if(c>=32&&issued<4&&r.ready&&c-last_issue>8){s.go=1;s.ph=phase;s.np=np;issued++;last_issue=c;}
            if(!pending.empty()&&pending.front().first==c){
                auto addr=pending.front().second;pending.pop_front();s.rv=1;
                for(int i=0;i<64;i++){uint32_t h=(addr+uint32_t(i)*0x9e3779b9u+test*131u)*0x85ebca6bu;h^=h>>13;h*=0xc2b2ae35u;h^=h>>16;
                    s.x[i]=(h&0x807fffffu)|((96u+(h>>23)%64u)<<23);}
            }
            if(!returns.empty()&&returns.front().at==c){
                auto row=returns.front();returns.pop_front();
                for(int g=0;g<12;g++){int n=(row.total+11-g)/12;int bit=16*g+4*row.tag;s.ga[bit/32]|=uint32_t(n)<<(bit%32);}
            }
            s.pq0=p0delay;s.pq1=p1delay;s.sq=sdelay;p0delay=prom[pa0];p1delay=prom[pa1];sdelay=srom[sa];
            uint32_t a0=d.ra0,a1=d.ra1,a2=d.ra2;
            drive_core(r,s);drive_die(d,s,m0,m1,m2&0xffffffffffffull);
            tick(r);tick(d);
            m0=prom[a0&4095];m1=prom[a1&4095];m2=srom[a2&4095];
            pa0=r.rom_pa0;pa1=r.rom_pa1;sa=r.rom_sa;
            if(c>=32){
                compared++;
                const uint32_t* ti=d.t_iss.data();
                bool mm=bits(ti,0,1)!=r.ready||bits(ti,1,1)!=r.idle||bits(ti,2,1)!=r.fault||bits(ti,3,32)!=r.phase_cycles
                    ||bits(ti,35,1)!=r.ev_go||bits(ti,36,1)!=r.ev_end||bits(ti,37,2)!=r.ev_tag
                    ||(d.t_vm&1)!=r.x_re||((d.t_vm>>1)&0x7ffff)!=r.x_addr
                    ||(d.ra0&1023)!=r.rom_pa0||(d.ra1&1023)!=r.rom_pa1||(d.ra2&2047)!=r.rom_sa||(d.ra0>>10)||(d.ra1>>10)||(d.ra2>>11)
                    ||!d.rc0||!d.rc1||!d.rc2||std::memcmp(r.mdr_o.data(),d.t_cnt.data(),14*4)||bits(r.mdr_o.data(),448,10)!=bits(d.t_cnt.data(),448,10);
                if(mm){std::printf("PQ_DIE_N FAIL test=%d cycle=%d core-port mismatch\n",test,c);return 1;}
                if(have_prev){
                    for(int i=0;i<565;i++){
                        uint64_t e=bits(prev_enc,i,1);
                        if(bits(d.xw.data(),i,1)!=e||bits(d.xe.data(),i,1)!=e){
                            std::printf("PQ_DIE_N FAIL test=%d cycle=%d lane bit %d expected %llu xw %llu xe %llu\n",test,c,i,(unsigned long long)e,
                                (unsigned long long)bits(d.xw.data(),i,1),(unsigned long long)bits(d.xe.data(),i,1));return 1;}
                    }
                    if(bits(prev_enc,0,1)){lane_words++;lane_q+=bits(prev_enc,283,1);lane_go+=bits(prev_enc,550,1);lane_cfg+=bits(prev_enc,551,1);}
                }
                encode(r.f_bus.data(),prev_enc);have_prev=true;
                if(r.fault){std::printf("PQ_DIE_N FAIL test=%d cycle=%d unexpected fault\n",test,c);return 1;}
                if(r.x_re){pending.push_back({c+6,r.x_addr});reads++;}
                if(bits(r.f_bus.data(),1619,1)){seen_go++;int tag=bits(r.f_bus.data(),1616,2);returns.push_back({c+40,tag,32*(np+1)});}
                if(issued==4&&seen_go==4&&r.idle&&pending.empty()&&returns.empty())idles++;else idles=0;
                if(idles>=32){finished=true;break;}
            }
        }
        if(!finished){std::printf("PQ_DIE_N FAIL test=%d did not retire\n",test);return 1;}
    }
    if(!lane_q||lane_go!=16||!reads){std::printf("PQ_DIE_N FAIL coverage words=%llu q=%llu go=%llu reads=%llu\n",
        (unsigned long long)lane_words,(unsigned long long)lane_q,(unsigned long long)lane_go,(unsigned long long)reads);return 1;}
    std::printf("PQ_DIE_N PASS compared=%llu lane_words=%llu q_beats=%llu gos=%llu cfg=%llu x_reads=%llu\n",(unsigned long long)compared,
        (unsigned long long)lane_words,(unsigned long long)lane_q,(unsigned long long)lane_go,(unsigned long long)lane_cfg,(unsigned long long)reads);
    return 0;
}
