// Production core differential gate: actual 36 SRAMs vs unchanged flop tiles.
// External twelve-group counts exercise the die-distributed return interface.
#include <cstdio>
#include <cstdint>
#include <cstring>
#include <deque>
#include "Vref.h"
#include "Vdut.h"
#include "verilated.h"

struct Stim {
    uint8_t reset=0, go=0, np=0, rv=0;
    uint16_t ph=0;
    uint64_t pq0=0,pq1=0,sq=0;
    uint32_t x[64]={},ga[6]={};
};
template<class M> void drive(M& m,const Stim& s) {
    m.rst_n=s.reset;m.go=s.go;m.i_np=s.np;m.i_ph=s.ph;
    m.i_xbase=64;m.i_xps=8192;m.i_obase=98304;m.i_ops=2048;m.i_fmt=0;
    m.x_rv=s.rv;m.f_fault=0;m.q2f_i=0;m.rom_pq0=s.pq0;m.rom_pq1=s.pq1;m.rom_sq=s.sq;
    for(int i=0;i<64;i++)m.x_q[i]=s.x[i];
    for(int i=0;i<6;i++)m.ga_i[i]=s.ga[i];
}
template<class M> void tick(M& m) {
    m.ck_ctl=m.ck_qb=m.ck_fault=0;m.ck_aq=m.ck_ix=m.ck_bc=0;m.eval();
    m.ck_ctl=m.ck_qb=m.ck_fault=1;m.ck_aq=3;m.ck_ix=m.ck_bc=15;m.eval();
}
static uint32_t bits(const uint32_t* p,int bit,int n) {
    uint64_t x=p[bit/32]>>(bit%32);
    if(bit%32+n>32)x|=uint64_t(p[bit/32+1])<<(32-bit%32);
    return x&((1ull<<n)-1);
}
int main(int argc,char**argv) {
    Verilated::commandArgs(argc,argv);
    uint64_t compared=0,qbeats=0,bbeats=0,reads=0,counts=0,qualified_q=0,qualified_b=0,speculative_q=0,speculative_b=0;
    for(int test=0;test<4;test++) {
        Vref r;Vdut d;Stim s;
        int fam=test&1,np=(test>>1),phase=257+test*37;
        uint64_t prom[1024]={},srom[2048]={};
        int nb=192,base=test*256;
        prom[2*phase]=uint64_t(fam)|(6144ull<<1)|(uint64_t(nb)<<14)|(uint64_t(base)<<30)|(32ull<<46);
        prom[2*phase+1]=0;
        for(int k=0;k<nb;k++) {
            uint64_t w=1;
            if(fam) {
                w|=uint64_t(k%8)<<1;w|=15ull<<4;
                for(int g=0;g<4;g++)w|=uint64_t((k+13*g)%48)<<(8*(g+1));
            } else {
                w|=uint64_t((k/8)%12)<<1;w|=uint64_t(k%8)<<9;w|=3ull<<12;
                for(int g=2;g<5;g++)w|=uint64_t((k/8)%12)<<(8*g);
            }
            srom[base+k]=w;
        }
        uint16_t pa0=0,pa1=0,sa=0;
        uint64_t p0delay=0,p1delay=0,sdelay=0;
        std::deque<std::pair<int,uint32_t>> pending;
        struct Return {int at, tag, total;};
        std::deque<Return> returns;
        int issued=0,seen_go=0,last_issue=-100,idles=0;
        bool finished=false;
        for(int c=0;c<30000;c++) {
            s.reset=c>=16;s.go=0;s.rv=0;
            std::memset(s.ga,0,sizeof(s.ga));
            if(c>=32&&issued<4&&r.ready&&c-last_issue>8){s.go=1;s.ph=phase;s.np=np;issued++;last_issue=c;}
            if(!pending.empty()&&pending.front().first==c) {
                auto addr=pending.front().second;pending.pop_front();s.rv=1;
                for(int i=0;i<64;i++) {
                    uint32_t h=(addr+uint32_t(i)*0x9e3779b9u+test*131u)*0x85ebca6bu;
                    h^=h>>13;h*=0xc2b2ae35u;h^=h>>16;
                    s.x[i]=(h&0x807fffffu)|((96u+(h>>23)%64u)<<23);
                }
            }
            if(!returns.empty()&&returns.front().at==c) {
                auto row=returns.front();returns.pop_front();
                int total=row.total,tag=row.tag;
                for(int g=0;g<12;g++) {
                    int n=(total+11-g)/12;
                    int bit=16*g+4*tag;
                    s.ga[bit/32]|=uint32_t(n)<<(bit%32);counts+=n;
                }
            }
            s.pq0=p0delay;s.pq1=p1delay;s.sq=sdelay;
            p0delay=prom[pa0];p1delay=prom[pa1];sdelay=srom[sa];
            drive(r,s);drive(d,s);tick(r);tick(d);
            pa0=r.rom_pa0;pa1=r.rom_pa1;sa=r.rom_sa;
            if(c>=32) {
                compared++;
                qualified_q+=(d.read_consumed&1)!=0;qualified_b+=(d.read_consumed&2)!=0;
                speculative_q+=(d.read_speculative&1)!=0;speculative_b+=(d.read_speculative&2)!=0;
                bool mismatch=r.ready!=d.ready||r.idle!=d.idle||r.x_re!=d.x_re||r.x_addr!=d.x_addr||r.fault!=d.fault
                    ||r.phase_cycles!=d.phase_cycles||r.ev_go!=d.ev_go||r.ev_end!=d.ev_end||r.ev_tag!=d.ev_tag
                    ||r.rom_pa0!=d.rom_pa0||r.rom_pa1!=d.rom_pa1||r.rom_sa!=d.rom_sa
                    ||std::memcmp(r.mdr_o.data(),d.mdr_o.data(),15*4);
                // Payload has meaning under its own family-valid bit. The
                // other-family aliases disappear in the production union lane.
                for(int bit=0;bit<1633;bit++) {
                    if(bit<1024&&!bits(r.f_bus.data(),1063,1))continue;
                    if(bit>=1070&&bit<=1601&&!bits(r.f_bus.data(),1615,1))continue;
                    if(bits(r.f_bus.data(),bit,1)!=bits(d.f_bus.data(),bit,1))mismatch=true;
                }
                if(mismatch){std::printf("PQ_NATIVE_CORE FAIL test=%d cycle=%d mismatch\n",test,c);return 1;}
                if(r.fault){std::printf("PQ_NATIVE_CORE FAIL test=%d cycle=%d unexpected fault\n",test,c);return 1;}
                if(r.x_re){pending.push_back({c+6,r.x_addr});reads++;}
                if(bits(r.f_bus.data(),1615,1))qbeats++;
                if(bits(r.f_bus.data(),1063,1))bbeats++;
                if(bits(r.f_bus.data(),1619,1)) {
                    seen_go++;int tag=bits(r.f_bus.data(),1616,2);
                    returns.push_back({c+40,tag,32*(np+1)});
                }
                if(issued==4&&seen_go==4&&r.idle&&pending.empty()&&returns.empty())idles++;else idles=0;
                if(idles>=32){finished=true;break;}
            }
        }
        if(!finished){std::printf("PQ_NATIVE_CORE FAIL test=%d did not retire seen_go=%d issued=%d\n",test,seen_go,issued);return 1;}
    }
    if(!qbeats||!bbeats||reads<1536||counts!=768||!qualified_q||!qualified_b||!speculative_q||!speculative_b){std::printf("PQ_NATIVE_CORE FAIL coverage q=%llu bf=%llu reads=%llu counts=%llu\n",
        (unsigned long long)qbeats,(unsigned long long)bbeats,(unsigned long long)reads,(unsigned long long)counts);return 1;}
    std::printf("PQ_NATIVE_CORE PASS compared=%llu q=%llu bf=%llu reads=%llu counts=%llu consumed_q=%llu consumed_b=%llu speculative_q=%llu speculative_b=%llu KMAX=6144 PHW=9 SAW=11 R=128 macros=36 return_groups=12\n",
        (unsigned long long)compared,(unsigned long long)qbeats,(unsigned long long)bbeats,(unsigned long long)reads,(unsigned long long)counts,
        (unsigned long long)qualified_q,(unsigned long long)qualified_b,(unsigned long long)speculative_q,(unsigned long long)speculative_b);
    return 0;
}
