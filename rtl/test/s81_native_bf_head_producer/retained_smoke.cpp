// C++ orchestration test links unchanged Vpb/Vcut/Vretn/Vroot archives.
// Raw1/2 weights and XN1 are test stimuli; expected roots are assertions only.
#include "s81_native_bf_head_producer.hpp"
#ifdef DSROM_S81_RETAINED_HEAD_STREAM_BIND_ONLY
#include "s81_native_head_collective.hpp"

// Caller hook for the SAME native R128 argmax on missing ranks1..3. Include
// this existing source with BIND_ONLY in the enclosing shared-clock caller.
// No dot/comparator, host ordering, shadow logits or command-owner store.
// Required participant order: collector.prepare, bank.prepare, this.prepare;
// collector.rising (OLD ready sample), bank.rising, this.rising;
// all native falling, then collector.falling. The bank remains its sole owner.
template<class NativeAmax,class Vm>
DsromS81MinimumParticipant dsrom_s81_retained_head_stream_participant(
    DsromS81MinimumRuntime& rt,NativeAmax& native,Vm& vm,
    unsigned rank,uint64_t identity,uint64_t sequence,
    std::function<bool()> actual_first_go,
    std::function<const dsrom_s81_minimum::NativeBfHeadRoots*()> held_source,
    std::function<const uint32_t*()> held_joined_bits,
    std::function<bool()> publication_live,
    std::function<void()> actual_write_taken) {
    if(rank<1||rank>3||identity>=(1ull<<47)||!rt.context||
       native.contextp()!=rt.context||vm.contextp()!=rt.context||
       !actual_first_go||!held_source||!held_joined_bits||!publication_live||!actual_write_taken)
        throw std::runtime_error("native head stream requires actual rank/context/source callbacks");
    struct Edge {bool prepared=false,begun=false,start=false,take=false,stopped=false;};
    auto edge=std::make_shared<Edge>();
    return {"native-head-accepted-writer-rank"+std::to_string(rank),
        [&,edge,rank,identity,sequence,actual_first_go,held_source,held_joined_bits,publication_live](const auto&) {
            if(edge->prepared||edge->stopped||native.fault)
                throw std::runtime_error("native head stream reused/quarantined edge");
            edge->prepared=true;edge->take=false;edge->start=actual_first_go();
            if(edge->start&&(edge->begun||native.busy||!rt.identity||*rt.identity!=identity))
                throw std::runtime_error("native head stream duplicate/foreign first accepted I5 GO");
            if(edge->begun&&(!rt.identity||*rt.identity!=identity))
                throw std::runtime_error("native head stream held source identity changed");
            native.start=edge->start;native.identity=identity;
            native.nout=32320;native.obase=486848;
            for(unsigned i=0;i<4;++i)native.write_valid[i]=native.write_accept[i]=0;
            for(unsigned i=0;i<120;++i)native.write_address[i]=0;
            for(unsigned i=0;i<128;++i)native.write_bits[i]=0;
            native.clk=0;native.eval(); // settle REAL ready, no extra clock edge
            if(native.source_rank!=rank)
                throw std::runtime_error("head stream compiled RANK differs from actual producer");
            const auto* source=held_source();const auto* bits=held_joined_bits();
            if(!publication_live()||!bits)return; // normalization/input writes are not head logits
            if(!edge->begun||!source||source->identity!=identity||source->request_sequence!=sequence||
               source->rank!=rank||source->local_row>=32320||!native.busy)
                throw std::runtime_error("head stream lacks actual retained producer/source epoch");
            // Do not let the sole VM accept a write the native leaf cannot
            // consume. Preserve its command/address/data/tag and existing seats.
            if(!native.write_ready)vm.wr_v=0;
            vm.clk=0;vm.eval();
            const unsigned offered=vm.wr_v,take=vm.wr_accept_v;
            if(take&~offered||__builtin_popcount(offered)>1)
                throw std::runtime_error("head scalar stream foreign/burst VM acceptance");
            if(!offered)return;
            const unsigned bank=__builtin_ctz(offered);
            const uint32_t mask=uint32_t((uint64_t(vm.wr_lane_mask)>>(16*bank))&65535);
            if(__builtin_popcount(mask)!=1)
                throw std::runtime_error("head scalar stream requires the actual one-word native publication");
            const unsigned lane=__builtin_ctz(mask);
            const uint32_t address=uint32_t((uint64_t(vm.wr_word_addr)>>(15*bank))&32767)*16+lane;
            if(bank!=((address>>4)&3)||address!=486848+source->local_row||vm.wr_word_data[bank*16+lane]!=*bits)
                throw std::runtime_error("head stream VM tuple differs from held native joined root");
            const unsigned root=(source->local_row%256)/2;
            native.write_valid[root/32]|=1u<<(root%32);
            native.write_bits[root]=vm.wr_word_data[bank*16+lane];
            for(unsigned i=0;i<30;++i) {
                const unsigned bit=root*30+i;
                native.write_address[bit/32]|=((address>>i)&1u)<<(bit%32);
            }
            if(take&(1u<<bank)) {
                if(!native.write_ready)throw std::runtime_error("VM took head logit without actual native credit");
                native.write_accept[root/32]|=1u<<(root%32);edge->take=true;
            }
            native.eval();
        },
        [&,edge,actual_write_taken](bool released) {
            if(!edge->prepared||edge->stopped)
                throw std::runtime_error("head stream rising lacks settled old writer tuple");
            if(!released&&(edge->begun||edge->start||edge->take))
                throw std::runtime_error("reset would erase accepted native head stream debt");
            native.rst_n=released;native.clk=1;native.eval();
            if(native.fault){edge->stopped=true;throw std::runtime_error("actual native head stream fault");}
            if(edge->start)edge->begun=true;
            // This callback records the native take; it NEVER grants a VM ACK
            // or releases the producer. Existing OutputBatch ACK still required.
            if(edge->take)actual_write_taken();
        },
        [&,edge](bool released) {
            native.rst_n=released;native.clk=0;native.eval();edge->prepared=false;
        },
        [&,edge](){return edge->stopped||bool(native.fault);}
    };
}

// Supply this actual ports object to the existing four-rank collector. Rank0
// remains its existing raw-core ports; never substitute a local winner for it.
template<class NativeAmax>
DsromS81NativeHeadPorts dsrom_s81_retained_head_stream_ports(NativeAmax& native) {
    return dsrom_s81_native_head_amax_ports(native);
}
#else
#include "Vpb.h"
#include "Vretn.h"
#include "Vroot.h"
#include "svdpi.h"
#include <map>
#include <iostream>
using namespace dsrom_s81_minimum;
NativeBfHeadProducer<Vretn,Vroot>* producer=nullptr;
#ifdef DSROM_S81_RELEASED_HEAD_COMPONENT
#include "s81_native_bf_head_factory.hpp"

#endif
std::map<const void*,unsigned> banks;
extern "C" void v41rt_rom_register(const char* instance) {
    std::string name=instance?instance:"";
    banks[svGetScope()]=!name.empty()&&name.back()=='b';
}
extern "C" void v41rt_cfg_register() {}
extern "C" long long v41rt_cfg_read(int address) {
#ifdef DSROM_S81_RELEASED_HEAD_COMPONENT
    // The existing producer below owns direct component ROM/CFG routing.
#endif
    if(!producer)throw std::runtime_error("CFG before actual head producer");
    return producer->cfg_word(address);
}
extern "C" void v41rt_rom_read(int address,svBitVecVal* out) {
#ifdef DSROM_S81_RELEASED_HEAD_COMPONENT
    // No whole-caller PairMem installer is substituted here.
#endif
    if(!producer)throw std::runtime_error("ROM before actual head producer");
    auto word=producer->raw_word(banks.at(svGetScope()),address);
    std::copy(word.begin(),word.end(),out);
}
int synthetic_main(int argc,char** argv) {
 try {
    VerilatedContext ctx;ctx.commandArgs(argc,argv);ctx.threads(1);ctx.randReset(0);
    Vpb pair(&ctx,"head_selected_pb");
    DsromS81MinimumRuntime rt{};rt.context=&ctx;rt.stage=0;rt.rank=0;rt.pair=0;rt.bf16=true;
    long cycles=0;uint32_t source=(argc>1)?0x3f800001:0x3f800000;unsigned reads=0,accepted=0,raw_reads=0;
    DsromS81PairDrive driven{};
    rt.result=[&](){return DsromS81PairResult{pair.pv,pair.perr,pair.ppos,pair.pseg,pair.pnseg,
        pair.prow,pair.pval,bool(pair.busy),bool(pair.quiet),bool(pair.fault)};};
    rt.drive=[&](const DsromS81PairDrive& p){driven=p;
      pair.cfg_go=p.cfg_go;pair.cfg_ph=p.cfg_ph;pair.cfg_np=p.cfg_np;
      pair.go=p.go;pair.go_bf=p.go_bf;pair.xs_v=p.xs_v;pair.xs_p=p.xs_p;pair.xs_b=p.xs_b;
      pair.xs_sv=p.xs_sv;pair.xs_e0=p.xs_e0;pair.xs_e1=p.xs_e1;pair.xs_pos=p.xs_pos;
      pair.xb_pos=p.xb_pos;pair.xb_v=p.xb_v;pair.xb_b=p.xb_b;pair.xb_sv=p.xb_sv;pair.xb_u=p.xb_u;
      for(unsigned i=0;i<8;i++){pair.xs_q0[i]=p.xs_q0[i];pair.xs_q1[i]=p.xs_q1[i];}
      for(unsigned i=0;i<32;i++)pair.xb_d[i]=p.xb_d[i];};
    rt.cycle=[&](){return cycles;};rt.drive({});
    Vcut actual_shared_cut(&ctx,"borrowed_head_cut");
    NativeBfHeadProducer<Vretn,Vroot> head(rt,actual_shared_cut,
      [&](uint64_t id,uint32_t a)->std::optional<uint32_t>{
        if(id!=7||a<46464||a>=51584)throw std::runtime_error("source XN bounds");reads++;return source;},
      [&](uint64_t id,uint32_t a,unsigned n){return id==7&&a==46464&&n==5120;},
      [&](unsigned rank,unsigned row,unsigned h,unsigned b){
        if(rank||row>=4||h>=40||b>=8)throw std::runtime_error("raw fixture bounds");
        NativeBfHeadRom::Word w{};unsigned value=(row&1)?0x4000:0x3f80;
        for(unsigned i=0;i<8;i++)w[i]=value|(value<<16);raw_reads++;return w;},
      [&](const NativeBfHeadRoots& out){
        if(out.identity!=7||out.request_sequence!=19||out.rank||out.local_row!=accepted)
            throw std::runtime_error("actual native output source identity");
        uint32_t a=(accepted&1)?0x46000000:0x45800000,b=(accepted&1)?0x45000000:0x44800000;
        if(out.root4096!=a||out.root1024!=b)throw std::runtime_error("actual BF ordered subtree mismatch");
        std::cout<<"NATIVE_HEAD_ROOTS row="<<out.local_row<<" A="<<std::hex<<out.root4096
                 <<" B="<<out.root1024<<std::dec<<" cycle="<<cycles<<"\n";
        source=0x40400000;accepted++;return true;},true);
    producer=&head;
    auto edge=[&](bool released){
      auto old=rt.result();for(auto& p:rt.participants)p.prepare(old);
      pair.clk=1;pair.rst_n=released;pair.eval();for(auto& p:rt.participants)p.rising(released);
      pair.clk=0;pair.eval();for(auto& p:rt.participants)p.falling(released);
      if(released){cycles++;if(pair.fault)throw std::runtime_error("PB native fault");
        for(auto& p:rt.participants)if(p.fault())throw std::runtime_error("native participant fault "+p.name);}
    };
    edge(false);rt.identity=7;head.start(7,19,0);
    // Source cycle watchdog, not an elapsed-time budget. Two native rowpairs.
    while(accepted<4&&cycles<15000){edge(true);head.advance();}
    if(accepted!=4||reads!=5120||raw_reads!=1280||head.all_roots_accepted())
        throw std::runtime_error("native BF snapshot/read counts or premature whole-head completion");
    std::cout<<"RETAINED_BF_HEAD_SMOKE_PASS cycles="<<cycles<<" source_reads="<<reads
             <<" raw274_reads="<<raw_reads<<" roots="<<accepted*2<<"\n";
    return 0;
 }catch(const std::exception& e){std::cerr<<"NATIVE_HEAD_SMOKE_FAIL "<<e.what()<<"\n";return 1;}
}

#ifndef DSROM_S81_RELEASED_HEAD_COMPONENT
int main(int argc,char** argv){return synthetic_main(argc,argv);}
#else
#include "s81_native_bf_head_factory.hpp"
#include "s81_minimum_prefix_providers.hpp"
#include "s81_published_span_accept_sink.hpp"
// Opt in only for a successor caller with Arch's actual publication helper.
#ifdef DSROM_S81_RELEASED_HEAD_LOGIT_PUBLICATION
#ifndef DSROM_S81_HEAD_WINNER_BINDING_HEADER
#error "Logit publication requires the existing emitted HEAD winner binding header"
#endif
#include "s81_minimum_source_plan.hpp"
#endif
#include "Vnative_vm.h"
#include <sys/mman.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <fstream>

// Component source hookup only: unchanged native archives perform ALL FP.
// H/PF are the actual produced carry, not a head activation/reference image.
// Tail uses the existing return-node adder with TWO explicit sibling inputs,
// so neither golden +0 is promoted/bypassed by the tree tag normalizer.
static std::vector<uint32_t> read_bits(const std::string& path,unsigned count) {
    std::ifstream f(path,std::ios::binary);std::vector<uint32_t> v(count);
    if(!f.read(reinterpret_cast<char*>(v.data()),4*count)||f.peek()!=EOF)
        throw std::runtime_error("actual carry size/read "+path);
    return v;
}
static void write_bits(std::ofstream& f,uint32_t bits) {
    unsigned char b[4];for(unsigned j=0;j<4;j++)b[j]=bits>>(8*j);
    f.write(reinterpret_cast<char*>(b),4);
    if(!f)throw std::runtime_error("native output capture write");
}
int main(int argc,char** argv) {
 try {
    if(argc!=7)throw std::runtime_error("released component RANK INPUTDIR HEADSHARD BYTEOFFSET OUTDIR SELECTEDDIR");
    unsigned rank=std::stoul(argv[1]);if(rank>=4)throw std::runtime_error("rank0..3");
    std::string input=argv[2],output=argv[5];
    setenv("DSROM_S81_MINIMUM_SELECTED_DIR",argv[6],1);
    setenv("DSROM_S81_MINIMUM_CROM_HEX",(input+"/norm.crom.hex").c_str(),1);
    auto h=read_bits(input+"/H_rank"+std::to_string(rank)+".u32",20480);
    auto pf=read_bits(input+"/PF_rank"+std::to_string(rank)+".u32",4);
    int fd=open(argv[3],O_RDONLY);struct stat st{};
    if(fd<0||fstat(fd,&st))throw std::runtime_error("released head shard unavailable");
    uint64_t offset=std::stoull(argv[4]);
    if(offset+129280ull*5120*2>uint64_t(st.st_size))throw std::runtime_error("released head extent");
    auto* mapped=static_cast<unsigned char*>(mmap(nullptr,st.st_size,PROT_READ,MAP_PRIVATE,fd,0));
    if(mapped==MAP_FAILED)throw std::runtime_error("released head mmap");
    const auto* weights=mapped+offset;
    VerilatedContext ctx;ctx.commandArgs(argc,argv);ctx.threads(1);ctx.randReset(0);
    DsromS81MinimumRuntime rt{};rt.context=&ctx;rt.stage=80;rt.rank=rank;rt.pair=11;rt.bf16=true;
    constexpr uint64_t ID=1ull<<31;constexpr uint64_t SEQUENCE=1;
    long cycles=0;rt.cycle=[&](){return cycles;};
    auto tags=dsrom_s81_bind_minimum_source_tags(rt,ID);
    PrefixPublication publication(ID);
    unsigned actual_accepts=0,actual_acks=0;
    auto accept=tags.scalar_accept;tags.scalar_accept=[&](unsigned b,const auto& c){accept(b,c);actual_accepts++;};
    PublishedSpanAcceptSink<Vnative_vm>* target_ptr=nullptr;
    Vnative_vm vm(&ctx,"head_actual_vm");
    PublishedSpanAcceptSink<Vnative_vm> target(vm,ID,0,
        [&](const auto& o,unsigned lane){return o.vm_address<20480?tags.record(o,lane):publication.record(o,lane);},
        [&](auto id,auto a,auto n){return publication.source_span_lease(id,a,n);},
        [&](auto id,auto a,auto n){return publication.write_allowed(id,a,n);},
        [&](const auto& c,const auto& receipt){publication.on_prefix_scalar_ack(c,receipt);
            dsrom_s81_retire_source_scalar_tag(rt,c.word.address&3,c,receipt);},
        {true,tags.scalar_accept,tags.read_accept});target_ptr=&target;
    bool read_pending=false;uint32_t read_address=0;std::array<uint32_t,8> read_owner{};
    DsromS81MinimumSourceIo io{
        [&](uint64_t id,uint32_t a)->std::optional<uint32_t>{
            if(id!=ID)throw std::runtime_error("head SourceIo owner");
            if(!read_pending){read_address=a;read_owner=tags.read_owner(id,a);read_pending=true;}
            if(a!=read_address)throw std::runtime_error("head SourceIo held address");
            auto word=target_ptr->target_word(a,read_owner);
            if(word){dsrom_s81_retire_source_read_tag(rt,a,read_owner);read_pending=false;}
            return word;},
        [&](auto id,auto a,auto n){return target.source_span_lease(id,a,n);},
        [&](const auto& o,unsigned n){return target.offer_prefix(o,n);},
        [&](const auto& o,unsigned n){return target.visible_prefix(o,n);}};
    auto su=dsrom_s81_bind_minimum_su256(rt,ID,publication,io,tags);
    std::array<DsromS81PrefixOperation,5> ops{};
    std::ifstream instructions(input+"/normalization.words");
    const std::vector<std::vector<std::pair<uint32_t,uint32_t>>> extents{
        {{20480,5120}},{{20480,5120}},{{41344,5120},{51584,1}},{{51616,1}},{{46464,5120}}};
    for(unsigned i=0;i<5;i++){
        auto& op=ops[i];instructions>>op.index;op.unit=2;
        for(auto& w:op.instruction)instructions>>std::hex>>w;
        instructions>>std::dec;if(!instructions)throw std::runtime_error("literal head instruction input");
        publication.enroll_literal(op.index,extents[i]);
    }
#ifdef DSROM_S81_RELEASED_HEAD_LOGIT_PUBLICATION
    publication.enroll_literal(4892,{{486848,32320}});
    DsromS81MinimumPrefixOutputBatch logit_batch(rt,ID,publication,io,tags);
    bool head_publication_begun=false;
    uint32_t held_join_tag=0,held_join_bits=0;
#endif
    Vpb pair(&ctx,"released_head_pair");Vcut cut(&ctx,"released_head_shared_cut");
    rt.result=[&](){return DsromS81PairResult{pair.pv,pair.perr,pair.ppos,pair.pseg,pair.pnseg,
        pair.prow,pair.pval,bool(pair.busy),bool(pair.quiet),bool(pair.fault)};};
    rt.drive=[&](const DsromS81PairDrive& p){
        pair.cfg_go=p.cfg_go;pair.cfg_ph=p.cfg_ph;pair.cfg_np=p.cfg_np;
        pair.go=p.go;pair.go_bf=p.go_bf;pair.xs_v=p.xs_v;pair.xs_p=p.xs_p;pair.xs_b=p.xs_b;
        pair.xs_sv=p.xs_sv;pair.xs_e0=p.xs_e0;pair.xs_e1=p.xs_e1;pair.xs_pos=p.xs_pos;
        pair.xb_pos=p.xb_pos;pair.xb_v=p.xb_v;pair.xb_b=p.xb_b;pair.xb_sv=p.xb_sv;pair.xb_u=p.xb_u;
        for(unsigned i=0;i<8;i++){pair.xs_q0[i]=p.xs_q0[i];pair.xs_q1[i]=p.xs_q1[i];}
        for(unsigned i=0;i<32;i++)pair.xb_d[i]=p.xb_d[i];};rt.drive({});
    Vretn pad1(&ctx,"head_pad1"),pad2(&ctx,"head_pad2"),join(&ctx,"head_join");
    std::array<Vretn*,3> tail{&pad1,&pad2,&join};
    std::optional<NativeBfHeadRoots> held;unsigned tail_stage=0,logits=0;bool taken=false;
    std::ofstream logit_file(output+"/logits_rank"+std::to_string(rank)+".u32",std::ios::binary);
    std::ofstream xn_file(output+"/XN_rank"+std::to_string(rank)+".u32",std::ios::binary);
    unsigned raw_reads=0;
    DsromS81NativeHeadProducer head(rt,cut,io.read_word,io.span_lease,
        [&](unsigned r,unsigned row,unsigned group,unsigned step){
            if(r!=rank||row>=32320||group>=40||step>=8)throw std::runtime_error("released head source coordinates");
            NativeBfHeadRom::Word w{};
            for(unsigned lane=0;lane<16;lane++){
                uint64_t col=group*128+lane*8+step;
                uint64_t index=(uint64_t(r)*32320+row)*5120+col;
                uint32_t bf=uint32_t(weights[2*index])|(uint32_t(weights[2*index+1])<<8);
                w[lane/2]|=bf<<(16*(lane%2));
            }raw_reads++;return w;},
        [&](const NativeBfHeadRoots& roots){
            if(roots.identity!=ID||roots.request_sequence!=SEQUENCE||roots.rank!=rank||roots.local_row!=logits-(taken?1:0))
                throw std::runtime_error("native root source owner/sequence/row");
            if(!held){held=roots;tail_stage=0;taken=false;return false;}
            if(held->root4096!=roots.root4096||held->root1024!=roots.root1024)
                throw std::runtime_error("held native roots changed");
            if(!taken)return false;
            held.reset();tail_stage=0;taken=false;return true;
        },false);producer=&head;
    auto bank=target.participant();auto oldrise=bank.rising;
    bank.rising=[&](bool r){oldrise(r);if(r)actual_acks+=__builtin_popcount(unsigned(vm.wr_ack_v));};
    bool su_active=true,head_active=false;
    auto input_part=dsrom_s81_select_native_bf_head_phase(rt,cut,[&](){return head_active;},head.input_participant());
    auto ret_part=dsrom_s81_select_native_bf_head_phase(rt,cut,[&](){return head_active;},head.return_participant());
    auto cold_return=head.return_participant();
    auto tail_drive=[&](Vretn& node,uint32_t a,uint32_t b){
        uint32_t row=rank*32320+held->local_row;
        node.a_v=1;node.b_v=1;node.a_t=(row<<13)|2;node.b_t=(row<<13)|258;
        node.a_d=a;node.b_d=b;node.a_e=node.b_e=0;};
    auto step=[&](bool released){
        auto old=rt.result();bank.prepare(old);if(su_active)su.participant.prepare(old);
        input_part.prepare(old);ret_part.prepare(old);
        for(auto* node:tail){node->a_v=node->b_v=0;node->a_e=node->b_e=0;}
        if(released&&held&&!taken){
            if(tail_stage==0){tail_drive(pad1,held->root1024,0);tail_stage=1;}
            else if(tail_stage==1&&pad1.o_v){if(pad1.o_e)throw std::runtime_error("head pad1 error");tail_drive(pad2,pad1.o_d,0);tail_stage=2;}
            else if(tail_stage==2&&pad2.o_v){if(pad2.o_e)throw std::runtime_error("head pad2 error");tail_drive(join,held->root4096,pad2.o_d);tail_stage=3;}
            else if(tail_stage==3&&join.o_v){
                if(join.o_e||join.o_t!=(((rank*32320+held->local_row)<<13)|34))throw std::runtime_error("head join native error/tag");
#ifdef DSROM_S81_RELEASED_HEAD_LOGIT_PUBLICATION
            // Capture the actual pulse once; native roots remain owned while
            // the existing batch waits for the SAME bank's positive VM ACK.
            held_join_tag=join.o_t;held_join_bits=join.o_d;tail_stage=4;
#else
            write_bits(logit_file,join.o_d);++logits;taken=true;
#endif
            }
        }
#ifdef DSROM_S81_RELEASED_HEAD_LOGIT_PUBLICATION
        if(released&&held&&!taken&&tail_stage==4) {
            if(!head_publication_begun)throw std::runtime_error("head logit before native I5 acceptance");
            if(dsrom_s81_publish_minimum_head_logit(rt,logit_batch,ID,rank,
                 held->local_row,held_join_tag,held_join_bits,true)) {
                write_bits(logit_file,held_join_bits);++logits;taken=true;
            }
        }
        // Exactly NativeBfHeadInput's preedge acceptance predicate. start()
        // merely arms the input and cannot authorize a publication generation.
        const bool first_head_go=released&&head_active&&!head_publication_begun&&cut.go&&cut.ready;
        if(first_head_go&&(!rt.identity||*rt.identity!=ID||cut.i_ph!=0))
            throw std::runtime_error("first native I5 GO owner/phase mismatch");
#endif
        bank.rising(released);if(su_active)su.participant.rising(released);
        if(head_active||!released){pair.clk=1;pair.rst_n=released;pair.eval();}
        input_part.rising(released);
#ifdef DSROM_S81_RELEASED_HEAD_LOGIT_PUBLICATION
        if(first_head_go) {
            // Only after the selected input has executed that actual edge.
            if(input_part.fault())throw std::runtime_error("native I5 GO fault");
            publication.begin(ID,4892);head_publication_begun=true;
        }
#endif
        ret_part.rising(released);
        if(!released){cut.clk=1;cut.rst_n=0;cut.eval();cold_return.rising(false);}
        for(auto* node:tail){node->clk=1;node->rst_n=released;node->eval();}
        bank.falling(released);if(su_active)su.participant.falling(released);
        if(head_active||!released){pair.clk=0;pair.eval();}
        input_part.falling(released);ret_part.falling(released);
        if(!released){cut.clk=0;cut.eval();cold_return.falling(false);}
        for(auto* node:tail){node->clk=0;node->eval();if(node->fault)throw std::runtime_error("head tail native fault");}
        if(bank.fault()||(su_active&&su.participant.fault())||input_part.fault()||ret_part.fault()||pair.fault)
            throw std::runtime_error("actual native head participant fault");
        if(released)++cycles;
    };
    rt.tick=[&](){step(true);};step(false);head.observe_shared_cold_reset();rt.identity=ID;
    // Actual carried H first publishes through the native VM immutable input
    // sink, with its existing four-home order and actual scalar accept/ACKs.
    for(unsigned batch=0;batch<1280;batch++){
        S81EmbeddingOutput o{};o.vm_valid=true;o.vm_identity=ID;
        o.vm_address=(batch%4)*5120+(batch/4)*16;
        std::copy_n(h.begin()+o.vm_address,16,o.vm_data);
        while(!target.offer(o))rt.tick();while(!target.visible(o))rt.tick();
    }
    publication.begin(ID,PrefixPublication::PF);
    S81EmbeddingOutput p{};p.vm_valid=true;p.vm_identity=ID;p.vm_address=41152;
    for(unsigned lane=0;lane<4;lane++){
        p.vm_data[lane]=pf[lane];dsrom_s81_capture_minimum_prefix_scalar(rt,publication,PrefixPublication::PF,p,lane,true);
    }
    while(!io.offer(p,4))rt.tick();while(!io.visible(p,4))rt.tick();
    const long input_end=cycles;
    for(unsigned i=0;i<5;i++){
        auto& op=ops[i];while(!su.inputs_ready(op)||!su.ready())rt.tick();
        su.drive(op,true);publication.begin(ID,op.index);rt.tick();su.drive(op,false);
        while(!su.idle()||!publication.complete(ID,op.index))rt.tick();
        std::cout<<"NATIVE_HEAD_NORM rank="<<rank<<" node="<<i<<" producer="<<op.index<<" cycle="<<cycles<<std::endl;
    }
    const long norm_end=cycles;
    for(unsigned a=46464;a<51584;a++){
        std::optional<uint32_t> w;while(!(w=io.read_word(ID,a)))rt.tick();write_bits(xn_file,*w);
    }xn_file.close();
    su_active=false;head_active=true;head.start(ID,SEQUENCE,rank);
    const long dot_start=cycles;
    while(!head.all_roots_accepted()||held){
        rt.tick();head.advance();
        if(logits&&logits%512==0&&taken)std::cout<<"NATIVE_HEAD_LOGITS rank="<<rank<<" rows="<<logits<<" cycle="<<cycles<<std::endl;
    }
    if(logits!=32320||read_pending||!target.source_span_lease(ID,46464,5120))throw std::runtime_error("head native terminal count/lease");
#ifdef DSROM_S81_RELEASED_HEAD_LOGIT_PUBLICATION
    if(!head_publication_begun||logit_batch.pending()||logit_batch.fault()||
        !publication.complete(ID,4892)||!target.source_span_lease(ID,486848,32320))
        throw std::runtime_error("head logit terminal lacks actual full publication/lease");
#endif
    logit_file.close();std::ofstream terminal(output+"/native_rank"+std::to_string(rank)+".json");
    terminal<<"{\"rank\":"<<rank<<",\"input_end\":"<<input_end<<",\"normalization_end\":"<<norm_end
      <<",\"dot_start\":"<<dot_start<<",\"terminal_cycle\":"<<cycles<<",\"logits\":"<<logits
      <<",\"native_vm_accepts\":"<<actual_accepts<<",\"native_vm_acks\":"<<actual_acks
      <<",\"raw_native_words\":"<<raw_reads
#ifdef DSROM_S81_RELEASED_HEAD_LOGIT_PUBLICATION
      <<",\"logit_publication_acknowledged\":true"
#endif
      <<",\"argmax_bound\":false,\"reference_compared\":false}";
    producer=nullptr;munmap(mapped,st.st_size);close(fd);
    std::cout<<"NATIVE_HEAD_COMPONENT_DONE rank="<<rank<<" logits="<<logits<<" cycles="<<cycles<<std::endl;return 0;
 }catch(const std::exception& e){std::cerr<<"NATIVE_HEAD_COMPONENT_ERROR "<<e.what()<<std::endl;return 1;}
}
#endif
#endif // DSROM_S81_RETAINED_HEAD_STREAM_BIND_ONLY
