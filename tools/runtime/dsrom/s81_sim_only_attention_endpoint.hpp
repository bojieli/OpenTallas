#pragma once
#include <array>
#include <cstdint>
#include <cstdio>
#include <stdexcept>
#include "verilated.h"

// SIMULATION ONLY. Replaces only the unfinished arithmetic endpoint of the
// existing V41_ATT_CUT, never the adapter, packed KV producer, SourceIo or VM
// publication. No expected/checkpoint outputs are accepted. All service edges
// below are host functional scheduling, NOT RTL timing or performance evidence.
// H16/D512/TD32/NL4/T640/PWORDS1; integer IEEE binary32 RNE, gradual underflow,
// canonical +0; BF16 products; chunk8 sequential sums and padded ordered tree.
// Sources: ot_hdc_v41x_attn_tile::{deq,bmul,chunk}, attn::{elem,lane_tree,merge},
// hdc_golden_v41.csum. Adapter still performs the actual BF16 RNE conversion.
// Finite host capacity/rank: packed KV339200B +1280B row padding, Q16384B, P20480B,
// computed score40960B/PV32768B +18432B fault bytes, total469504B plus
// exposed buses/control. No hardware area/latency/rate credit.
// Each job captures 16 queries,160 four-row KV beats,320 two-row P words and
// emits BOTH160 score beats and8 PV beats. Credit pools64/64, pulse-only outputs
// and positive captured credit return. Same enclosing Cut freezes OLD inputs.
class DsromS81SimOnlyAttentionEndpoint {
public:
    uint8_t clk=0,rst_n=0,job_v=0,q_v=0,kv_v=0,kv_m=0,p_v=0;
    uint8_t sc_cr=0,pv_cr=0,job_ready=0,q_ready=0,kv_ready=0,p_ready=0;
    uint16_t job_t=0,sc_row=0;
    uint8_t sc_v=0,sc_m=0,pv_v=0,pv_c=0;
    uint64_t sc_f=0;
    std::array<uint32_t,256> q_w{};
    std::array<uint32_t,530> kv_w{};
    std::array<uint32_t,16> p_w{};
    std::array<uint32_t,64> sc_y{};
    std::array<uint32_t,1024> pv_y{};
    std::array<uint32_t,32> pv_f{};
private:
    struct Number { uint32_t bits=0; bool fault=false; };
    VerilatedContext* context_;
    bool prior_clk=false,active=false,computed=false;
    unsigned nq=0,nkv=0,np=0,score_cursor=0,pv_cursor=0;
    unsigned sc_credit=64,pv_credit=64,sc_debt=0,pv_debt=0;
    std::array<uint16_t,16*512> query{};
    std::array<uint16_t,16*640> probability{};
    std::array<std::array<uint32_t,133>,640> rows{}; // 4240 bits/row; last word padded
    std::array<uint32_t,16*640> scores{};
    std::array<uint32_t,16*512> values{};
    std::array<uint8_t,16*640> score_fault{};
    std::array<uint8_t,16*512> value_fault{};
    static void need(bool v,const char* message) {if(!v)throw std::runtime_error(message);}
    template<class A> static uint32_t bits(const A& a,unsigned offset,unsigned width) {
        uint32_t x=0;for(unsigned j=0;j<width;++j)x|=((a[(offset+j)/32]>>((offset+j)%32))&1u)<<j;return x;
    }
    static uint64_t jam(uint64_t a,unsigned n) {
        if(!n)return a;
        if(n>=64)return a!=0;
        return (a>>n)|((a&((uint64_t(1)<<n)-1))!=0);
    }
    // Round once at each binary32 add. Three guard/round/sticky bits suffice;
    // cancellation with close exponents is exact before renormalisation.
    static Number add(Number a,Number b) {
        bool bad=a.fault||b.fault;
        unsigned ea=(a.bits>>23)&255,eb=(b.bits>>23)&255;
        if(ea==255||eb==255)return {0,true};
        if(!(a.bits&0x7fffffff))return {b.bits&0x7fffffff?b.bits:0,bad};
        if(!(b.bits&0x7fffffff))return {a.bits,bad};
        uint64_t ma=(a.bits&0x7fffff)|(ea?0x800000:0),mb=(b.bits&0x7fffff)|(eb?0x800000:0);
        ea=ea?ea:1;eb=eb?eb:1;
        unsigned sa=a.bits>>31,sb=b.bits>>31;
        if(ea<eb||(ea==eb&&ma<mb)) {auto t=ea;ea=eb;eb=t;auto m=ma;ma=mb;mb=m;t=sa;sa=sb;sb=t;}
        ma<<=3;mb=jam(mb<<3,ea-eb);
        uint64_t m=sa==sb?ma+mb:ma-mb;
        if(!m)return {0,bad};
        if(m&(uint64_t(1)<<27)){m=jam(m,1);++ea;}
        while(m<(uint64_t(1)<<26)&&ea>1){m<<=1;--ea;}
        uint64_t sig=m>>3;unsigned low=m&7;
        sig+=(low>4||(low==4&&(sig&1)));
        if(sig>=0x1000000){sig>>=1;++ea;}
        if(ea>=255)return {0,true};
        if(!sig)return {0,bad};
        const unsigned exponent=(ea==1&&sig<0x800000)?0:ea;
        return {(sa<<31)|(exponent<<23)|uint32_t(sig&0x7fffff),bad};
    }
    static Number product(uint16_t a,Number b) {
        unsigned ea=(a>>7)&255,eb=(b.bits>>7)&255;
        if(b.fault||ea==255||eb==255)return {0,true};
        unsigned ma=(a&127)|(ea?128:0),mb=(b.bits&127)|(eb?128:0);
        unsigned p=ma*mb,sgn=((a^b.bits)>>15)&1;
        if(!p)return {};
        int es=int(ea?ea:1)+int(eb?eb:1);
        unsigned top=0;for(unsigned i=0;i<16;++i)if(p&(1u<<i))top=i;
        int exponent=es-141+int(top); // es-126-leading_zero16
        if(exponent>=255)return {0,true};
        if(exponent>=1)return {(sgn<<31)|(uint32_t(exponent)<<23)|((p<<(23-top))&0x7fffff),false};
        int shift=es-119;
        uint32_t sub=0;
        if(shift>=0)sub=p<<unsigned(shift);
        else {
            unsigned n=unsigned(-shift);
            if(n<32){sub=p>>n;unsigned tail=p&((1u<<n)-1),half=1u<<(n-1);sub+=(tail>half||(tail==half&&(sub&1)));}
        }
        return {sub?((sgn<<31)|sub):0,false};
    }
    Number dequant(unsigned row,unsigned dim)const {
        const auto& w=rows[row];const unsigned group=(dim/32)*265,x=dim%32;
        unsigned fmt=bits(w,group+264,1),code,scale,prod,sgn;int exponent;
        bool nan;
        if(!fmt){
            code=bits(w,group+x*8,8);scale=bits(w,group+256,8);
            unsigned e=(code>>3)&15;sgn=code>>7;
            nan=(e==15&&(code&7)==7)||scale==255;
            prod=(e?8:0)|(code&7);exponent=int(e?e:1)+int(scale)-137;
        }else{
            code=bits(w,group+x*4,4);scale=bits(w,group+128+(x/16)*8,8);
            unsigned e=(code>>1)&3,s=(scale>>3)&15;sgn=(code>>3)^(scale>>7);
            nan=s==15&&(scale&7)==7;
            prod=((e?2:0)|(code&1))*((s?8:0)|(scale&7));
            exponent=int(e?e:1)-2+int(s?s:1)-10;
        }
        if(nan)return {0,true};
        if(!prod)return {uint32_t(sgn)<<15,false};
        unsigned top=0;for(unsigned j=0;j<6;++j)if(prod&(1u<<j))top=j;
        exponent+=int(top)+127;
        if(exponent<1||exponent>254)return {0,true};
        return {(sgn<<15)|(uint32_t(exponent)<<7)|((prod<<(7-top))&127),false};
    }
    template<class Term> static Number dot(unsigned count,Term term) {
        std::array<Number,128> chunks{};
        unsigned n=(count+7)/8,padded=1;while(padded<n)padded*=2;
        for(unsigned i=0;i<n;++i)for(unsigned j=0;j<8;++j)
            chunks[i]=add(chunks[i],i*8+j<count?term(i*8+j):Number{});
        for(unsigned level=padded;level>1;level/=2)
            for(unsigned i=0;i<level/2;++i)chunks[i]=add(chunks[2*i],chunks[2*i+1]);
        return chunks[0];
    }
    void compute() {
        for(unsigned h=0;h<16;++h){
            for(unsigned row=0;row<640;++row){
                auto n=dot(512,[&](unsigned k){return product(query[h*512+k],dequant(row,k));});
                scores[h*640+row]=n.bits;score_fault[h*640+row]=n.fault;
            }
            for(unsigned d=0;d<512;++d){
                auto n=dot(640,[&](unsigned row){return product(probability[h*640+row],dequant(row,d));});
                values[h*512+d]=n.bits;value_fault[h*512+d]=n.fault;
            }
        }
        computed=true;
    }
    void view() {
        job_ready=!active&&!sc_debt&&!pv_debt;
        q_ready=active&&nq<16;kv_ready=active&&nkv<640;p_ready=active&&np<640;
    }
    void reset() {
        need(!active&&!sc_debt&&!pv_debt,"SIM_ONLY ATT reset erases accepted debt");
        nq=nkv=np=score_cursor=pv_cursor=0;computed=false;sc_v=pv_v=0;
        sc_m=0;sc_f=0;pv_f.fill(0);sc_credit=pv_credit=64;
    }
    void edge() {
        const bool start=job_v&&job_ready,takeq=q_v&&q_ready,takekv=kv_v&&kv_ready,takep=p_v&&p_ready;
        if(sc_cr){need(sc_debt>0,"SIM_ONLY ATT unmatched score credit");--sc_debt;++sc_credit;}
        if(pv_cr){need(pv_debt>0,"SIM_ONLY ATT unmatched PV credit");--pv_debt;++pv_credit;}
        need(sc_credit<=64&&pv_credit<=64,"SIM_ONLY ATT credit overflow");
        sc_v=pv_v=0;
        if(start){
            need(job_t==640,"SIM_ONLY ATT requires actual target-context T640");
            active=true;computed=false;nq=nkv=np=score_cursor=pv_cursor=0;
        }
        if(takeq){
            for(unsigned d=0;d<512;++d)query[nq*512+d]=uint16_t(bits(q_w,d*16,16));
            ++nq;
        }
        if(takekv){
            need(kv_m==15&&nkv+4<=640,"SIM_ONLY ATT KV mask/order/extent");
            for(unsigned lane=0;lane<4;++lane){
                auto& w=rows[nkv+lane];w.fill(0);
                for(unsigned j=0;j<4240;++j)w[j/32]|=bits(kv_w,lane*4240+j,1)<<(j%32);
            }
            nkv+=4;
        }
        if(takep){
            need(np+2<=640,"SIM_ONLY ATT probability extent");
            for(unsigned row=0;row<2;++row)for(unsigned h=0;h<16;++h)
                probability[h*640+np+row]=uint16_t(bits(p_w,(row*16+h)*16,16));
            np+=2;
        }
        if(active&&!computed&&nq==16&&nkv==640&&np==640)compute();
        if(computed&&score_cursor<160&&sc_credit){
            sc_v=1;sc_m=15;sc_row=uint16_t(score_cursor*4);sc_f=0;
            for(unsigned lane=0;lane<4;++lane)for(unsigned h=0;h<16;++h){
                const unsigned i=h*640+sc_row+lane;
                sc_y[lane*16+h]=scores[i];sc_f|=uint64_t(score_fault[i])<<(lane*16+h);
            }
            ++score_cursor;--sc_credit;++sc_debt;
        }
        if(computed&&pv_cursor<8&&pv_credit){
            pv_v=1;pv_c=uint8_t(pv_cursor);pv_f.fill(0);
            for(unsigned tile=0;tile<64;++tile)for(unsigned h=0;h<16;++h){
                const unsigned i=h*512+tile*8+pv_cursor,out=tile*16+h;
                pv_y[out]=values[i];pv_f[out/32]|=uint32_t(value_fault[i])<<(out%32);
            }
            ++pv_cursor;--pv_credit;++pv_debt;
        }
        if(computed&&score_cursor==160&&pv_cursor==8)active=false;
    }
public:
    explicit DsromS81SimOnlyAttentionEndpoint(VerilatedContext* context,const char*) :context_(context) {
        need(context!=nullptr,"SIM_ONLY ATT requires existing shared context");
        std::fprintf(stderr,"SIM_ONLY_ATT_ENDPOINT H16 D512 T640: computed input math, native adapter/KV/VM ACK; NO native ATT timing/qualification\n");
    }
    VerilatedContext* contextp()const{return context_;}
    void eval() {
        if(!rst_n){reset();job_ready=q_ready=kv_ready=p_ready=0;}
        else {if(clk&&!prior_clk)edge();view();}
        prior_clk=clk;
    }
};
