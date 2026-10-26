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
    if constexpr(requires {m.ck_qb_align;}) m.ck_qb_align=0;
    m.ck_ctl=m.ck_qb=m.ck_fault=0;m.ck_aq=m.ck_ix=m.ck_bc=0;
    if constexpr(requires {m.ck_ix_read;}) m.ck_ix_read=0;
    if constexpr(requires {m.ck_aq_aux;}) m.ck_aq_aux=0;
    if constexpr(requires {m.ck_qb_aux;}) m.ck_qb_aux=0;
    m.eval();
    if constexpr(requires {m.ck_qb_align;}) m.ck_qb_align=1;
    m.ck_ctl=m.ck_qb=m.ck_fault=1;m.ck_aq=3;m.ck_ix=15;m.ck_bc=(sizeof(m.ck_bc)>1 ? 65535 : 15);
    if constexpr(requires {m.ck_ix_read;}) m.ck_ix_read=0xffffffffU;
    if constexpr(requires {m.ck_aq_aux;}) m.ck_aq_aux=65535;
    if constexpr(requires {m.ck_qb_aux;}) m.ck_qb_aux=15;
    m.eval();
}
static uint32_t bits(const uint32_t* p,int bit,int n) {
    uint64_t x=p[bit/32]>>(bit%32);
    if(bit%32+n>32)x|=uint64_t(p[bit/32+1])<<(32-bit%32);
    return x&((1ull<<n)-1);
}
#include <array>
#include <vector>
#include <cstdlib>
struct Result {std::vector<std::array<uint32_t,52>> packets;unsigned cycles=0,phase_cycles=0;};
template<class M> Result simulate(int test) {
    uint64_t compared=0,qbeats=0,bbeats=0,reads=0,counts=0,qualified_q=0,qualified_b=0,speculative_q=0,speculative_b=0;
    unsigned kmin=16383,kmax=0,phmin=511,phmax=0,saddrmax=0;
    uint64_t aq_requests=0,aq0_results=0,aq1_results=0;
    uint64_t qbdual=0,qbsame=0,qbdiff=0,qbbankdiff=0;
        M m;Stim s;Result result;
        int fam=test&1,np=(test>>1),phase=257+test*37;
        uint64_t prom[1024]={},srom[2048]={};
        int nb=192,base=test*512;
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
        unsigned tagmask=0;int active_tag=0;int emitted[4]={};
        bool ring_written[2][128]={},ring_read[2][128]={};
        for(int c=0;c<30000;c++) {
            s.reset=c>=16;s.go=0;s.rv=0;
            std::memset(s.ga,0,sizeof(s.ga));
            if(c>=32&&issued<4&&m.ready&&c-last_issue>8){s.go=1;s.ph=phase;s.np=np;issued++;last_issue=c;}
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
            drive(m,s);tick(m);
            pa0=m.rom_pa0;pa1=m.rom_pa1;sa=m.rom_sa;
            if(c>=32) {
                compared++;
                if(m.rom_sa>saddrmax)saddrmax=m.rom_sa;
                if(m.observed_load_active) {
                    if(m.observed_k<kmin)kmin=m.observed_k;
                    if(m.observed_k>kmax)kmax=m.observed_k;
                    if(m.observed_k!=6144){std::printf("PQ_NATIVE_CORE FAIL runtime K=%u\n",unsigned(m.observed_k));std::exit(1);}
                }
                if(s.go){if(s.ph<phmin)phmin=s.ph;if(s.ph>phmax)phmax=s.ph;}
                aq_requests+=m.aq_request;aq0_results+=m.aq_results&1;aq1_results+=(m.aq_results>>1)&1;
                ring_written[0][m.aq0_write_row]=true;ring_written[1][m.aq1_write_row]=true;
                ring_read[0][m.aq0_read_row]=true;ring_read[1][m.aq1_read_row]=true;
                qualified_q+=(m.read_consumed&1)!=0;qualified_b+=(m.read_consumed&2)!=0;
                speculative_q+=(m.read_speculative&1)!=0;speculative_b+=(m.read_speculative&2)!=0;
                if(m.qb_pair_valid==3){
                    ++qbdual;
                    unsigned a=m.qb_q0_index,b=m.qb_q1_index;
                    unsigned ra=((a>>4)<<2)|((a>>1)&3),rb=((b>>4)<<2)|((b>>1)&3);
                    if(ra==rb)++qbsame;else++qbdiff;
                    if((((a>>3)&1)<<1|(a&1))!=(((b>>3)&1)<<1|(b&1)))++qbbankdiff;
                }
                if(bits(m.f_bus.data(),1615,1)||bits(m.f_bus.data(),1063,1)||bits(m.f_bus.data(),1619,1)) {
                    std::array<uint32_t,52> packet{};
                    for(int bit=0;bit<1633;bit++) {
                        if(bit<1024&&!bits(m.f_bus.data(),1063,1))continue;
                        if(bit>=1070&&bit<=1601&&!bits(m.f_bus.data(),1615,1))continue;
                        packet[bit/32]|=bits(m.f_bus.data(),bit,1)<<(bit%32);
                    }
                    result.packets.push_back(packet);
                }
                if(m.fault){std::printf("PQ_NATIVE_CORE FAIL test=%d cycle=%d unexpected fault\n",test,c);std::exit(1);}
                if(m.x_re){pending.push_back({c+6,m.x_addr});reads++;}
                if(bits(m.f_bus.data(),1615,1))qbeats++;
                if(bits(m.f_bus.data(),1063,1))bbeats++;
                if(bits(m.f_bus.data(),1619,1)) {
                    seen_go++;int tag=bits(m.f_bus.data(),1616,2);
                    tagmask|=1u<<tag;
                    active_tag=tag;
                }
                // A return can only follow the final operand beat of its operation.
                // External field work is modeled as 40 cycles after that beat.
                if(bits(m.f_bus.data(),1615,1)||bits(m.f_bus.data(),1063,1)) {
                    if(++emitted[active_tag]==nb*(np+1)) returns.push_back({c+40,active_tag,32*(np+1)});
                }
                if(issued==4&&seen_go==4&&m.idle&&pending.empty()&&returns.empty())idles++;else idles=0;
                if(idles>=32){finished=true;result.cycles=c-31;break;}
            }
        }
        if(!finished){std::printf("PQ_NATIVE_CORE FAIL test=%d did not retire seen_go=%d issued=%d\n",test,seen_go,issued);std::exit(1);}
        if(tagmask!=15){std::printf("PQ_NATIVE_CORE FAIL tag coverage mask=%u\n",tagmask);std::exit(1);}
        if constexpr (requires {m.ck_qb_aux;}) for(int i=0;i<12;i++) {
            auto wr=fam?m.ix_rows_written[i]:m.qb_rows_written[i];
            auto rd=fam?m.ix_rows_read[i]:m.qb_rows_read[i];
            if(wr!=0xffffffffu||rd!=0xffffffffu) {
                std::printf("PQ_NATIVE_CORE FAIL full storage rows test=%d bitmap_word=%d written=%08x read=%08x\n",test,i,wr,rd);std::exit(1);
            }
        }
        for(int a=0;a<2;a++)for(int row=0;row<128;row++)
            if(!ring_written[a][row]||!ring_read[a][row]){std::printf("PQ_NATIVE_CORE FAIL AQ ring row coverage\n");std::exit(1);}

    result.phase_cycles=m.phase_cycles;
    return result;
}
int main(int argc,char**argv) {
    Verilated::commandArgs(argc,argv);
    uint64_t baseline=0,candidate=0;
    for(int test=0;test<4;test++) {
       auto r=simulate<Vref>(test);auto d=simulate<Vdut>(test);
       if(r.packets!=d.packets) {std::printf("PQ_CORE_PIPE FAIL stream test=%d baseline_packets=%zu candidate_packets=%zu\n",test,r.packets.size(),d.packets.size());return 1;}
       std::printf("PQ_CORE_PIPE TIMING test=%d baseline_cycles=%u candidate_cycles=%u delta=%d baseline_phase=%u candidate_phase=%u packets=%zu\n",test,r.cycles,d.cycles,int(d.cycles)-int(r.cycles),r.phase_cycles,d.phase_cycles,d.packets.size());
       baseline+=r.cycles;candidate+=d.cycles;
    }
    std::printf("PQ_CORE_PIPE PASS component_diagnostic=1 baseline_cycles=%llu candidate_cycles=%llu loss_pct=%.6f native_full_token_qualified=0\n",(unsigned long long)baseline,(unsigned long long)candidate,100.*(double(candidate)/baseline-1.));
}
