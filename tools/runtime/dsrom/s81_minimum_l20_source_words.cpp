#include "s81_minimum_l20_source_words.hpp"
#include <algorithm>
#include <atomic>
#include <mutex>
#include <utility>

namespace {
void require(bool ok,const char* why){if(!ok)throw std::runtime_error(why);}
uint32_t le32(const unsigned char* p) {
    return uint32_t(p[0])|uint32_t(p[1])<<8|uint32_t(p[2])<<16|uint32_t(p[3])<<24;
}
void transfer(int fd,unsigned char* p,size_t n,bool send) {
    while(n) {
        const auto k=send ? ::send(fd,p,n,MSG_NOSIGNAL) : ::recv(fd,p,n,0);
        if(k<0&&errno==EINTR)continue;
        require(k>0,"L20 released source disconnected; no zero fallback");
        p+=k;n-=size_t(k);
    }
}
class ReadySource {
    int fd_=-1;pid_t child_=-1;
    std::mutex lock_;
public:
    ReadySource(const DsromS81L20SourceWordConfig& c,const std::string& kind,
                const std::string& node,const std::string& pin,unsigned rank,unsigned fragment) {
        int pair[2];require(!::socketpair(AF_UNIX,SOCK_STREAM,0,pair),"L20 source transport");
        auto r=std::to_string(rank),f=std::to_string(fragment);
        child_=::fork();
        if(child_<0){::close(pair[0]);::close(pair[1]);throw std::runtime_error("L20 source fork");}
        if(!child_) {
            ::close(pair[0]);
            if(pair[1]!=3&&::dup2(pair[1],3)<0)::_exit(126);
            bool closed=false;
#ifdef SYS_close_range
            closed=(::syscall(SYS_close_range,4u,UINT_MAX,0)==0);
#endif
            if(!closed){const long n=::sysconf(_SC_OPEN_MAX);for(int i=4;i<n;++i)::close(i);}
            ::execl(c.python.c_str(),c.python.c_str(),"-u",c.source_bridge.c_str(),
                "--fd","3","--owner",c.owner.c_str(),"--checkpoint",c.checkpoint.c_str(),
                "--kind",kind.c_str(),"--node",node.c_str(),"--source-sha",pin.c_str(),
                "--rank",r.c_str(),"--fragment",f.c_str(),static_cast<char*>(nullptr));
            ::_exit(127);
        }
        ::close(pair[1]);fd_=pair[0];
        try {
            unsigned char ready[40];transfer(fd_,ready,sizeof ready,false);
            require(le32(ready)==0&&le32(ready+36)==1,"L20 source child not READY");
            if(!pin.empty()) {
                const char* hex="0123456789abcdef";
                std::string actual;
                for(unsigned i=0;i<32;++i){actual+=hex[ready[4+i]>>4];actual+=hex[ready[4+i]&15];}
                require(actual==pin,"L20 READY source SHA mismatch");
            }
        }catch(...){close();throw;}
    }
    ReadySource(const ReadySource&)=delete;
    ~ReadySource(){close();}
    void close() {
        if(fd_>=0){::shutdown(fd_,SHUT_RDWR);::close(fd_);fd_=-1;}
        if(child_>0){int status;while(::waitpid(child_,&status,0)<0&&errno==EINTR){}child_=-1;}
    }
    std::array<uint32_t,9> read(uint32_t a,uint32_t b,uint32_t c,uint32_t d) {
        std::lock_guard<std::mutex> held(lock_);
        unsigned char request[16]{},reply[40];const uint32_t fields[4]={a,b,c,d};
        for(unsigned i=0;i<4;++i)for(unsigned j=0;j<4;++j)request[4*i+j]=(fields[i]>>(8*j))&255;
        transfer(fd_,request,sizeof request,true);transfer(fd_,reply,sizeof reply,false);
        require(le32(reply)==0,"L20 released source rejected address");
        std::array<uint32_t,9> out{};for(unsigned i=0;i<9;++i)out[i]=le32(reply+4+4*i);
        require((out[8]>>18)==0,"L20 source word exceeds274bits");return out;
    }
};
}

struct DsromS81MinimumL20SourceWords::Impl {
    struct Static {DsromS81L20StaticWordEnrollment source;std::shared_ptr<ReadySource> reader;};
    std::vector<Static> statics;
    std::vector<DsromS81DelayedEidEnrollment> dynamic_nodes;
    std::array<std::shared_ptr<ReadySource>,4> he;
    std::unique_ptr<DsromS81DelayedEidSessions> dynamic;
    DsromS81L20ResolveSourceAuthority resolve;
    std::atomic<bool> stopped{false};
    Impl(const DsromS81L20SourceWordConfig& c,
         const std::vector<DsromS81L20StaticWordEnrollment>& fixed,
         const std::vector<DsromS81DelayedEidEnrollment>& delayed,
         DsromS81L20ResolveSourceAuthority resolver):dynamic_nodes(delayed),resolve(std::move(resolver)) {
        require(!c.python.empty()&&!c.source_bridge.empty()&&!c.qe_bridge.empty()&&
                !c.owner.empty()&&!c.checkpoint.empty()&&bool(resolve),"L20 prestart actual source configuration");
        auto duplicate=[&](const std::string& node,unsigned rank,unsigned fragment) {
            for(const auto& s:statics)if(s.source.node==node&&s.source.rank==rank&&s.source.fragment==fragment)return true;
            return false;
        };
        for(const auto& e:fixed) {
            require(e.rank<4&&e.node.rfind("L20.",0)==0&&e.source_node_sha256.size()==64,
                    "L20 static node/rank/source SHA enrollment");
            require(!duplicate(e.node,e.rank,e.fragment),"duplicate L20 static source");
            const auto kind=e.kind==DsromS81L20WordKind::Field ? "field" : "me";
            require(e.kind==DsromS81L20WordKind::Field||e.kind==DsromS81L20WordKind::MeRaw,
                    "unsupported L20 source kind");
            statics.push_back({e,std::make_shared<ReadySource>(c,kind,e.node,e.source_node_sha256,e.rank,e.fragment)});
        }
        for(const auto& e:delayed) {
            require(e.node.rfind("L20.",0)==0&&e.rank<4&&e.capture_producer==2564&&
                    e.identity<(1ull<<47)&&e.capture_vm_base==366688,
                    "L20 dynamic actual I93 producer2564/ID47/destination required");
            require(!duplicate(e.node,e.rank,e.fragment),"static/dynamic source overlap");
        }
        std::array<DsromS81MinimumSourceIo,4> lazy_io;
        for(unsigned rank=0;rank<4;++rank) {
            lazy_io[rank].read_word=[this,rank](uint64_t id,uint32_t addr)->std::optional<uint32_t> {
                const auto a=resolve(rank);
                if(!a||!a->io.read_word)return std::nullopt;
                return a->io.read_word(id,addr);
            };
            lazy_io[rank].span_lease=[this,rank](uint64_t id,uint32_t addr,unsigned n) {
                const auto a=resolve(rank);return a&&a->io.span_lease&&a->io.span_lease(id,addr,n);
            };
        }
        if(!delayed.empty())dynamic=std::make_unique<DsromS81DelayedEidSessions>(
            c.python,c.qe_bridge,c.owner,c.checkpoint,delayed,std::move(lazy_io),
            [this](unsigned rank,uint64_t id,unsigned producer) {
                const auto a=resolve(rank);return a&&a->published&&a->published(id,producer);
            });
        for(unsigned rank=0;rank<4;++rank)
            he[rank]=std::make_shared<ReadySource>(c,"he","","",rank,0);
    }
};

DsromS81MinimumL20SourceWords::DsromS81MinimumL20SourceWords(std::shared_ptr<Impl> impl):impl_(std::move(impl)){}
std::shared_ptr<DsromS81MinimumL20SourceWords> DsromS81MinimumL20SourceWords::prestart(
    const DsromS81L20SourceWordConfig& c,const std::vector<DsromS81L20StaticWordEnrollment>& fixed,
    const std::vector<DsromS81DelayedEidEnrollment>& delayed,DsromS81L20ResolveSourceAuthority resolve) {
    return std::shared_ptr<DsromS81MinimumL20SourceWords>(new DsromS81MinimumL20SourceWords(
        std::make_shared<Impl>(c,fixed,delayed,std::move(resolve))));
}
DsromS81MinimumL20SourceWords::WordRead DsromS81MinimumL20SourceWords::word_reader(
    const std::string& node,unsigned rank,unsigned fragment) {
    require(rank<4,"L20 source rank");
    auto owner=impl_;
    for(const auto& e:owner->statics)if(e.source.node==node&&e.source.rank==rank&&e.source.fragment==fragment) {
        auto reader=e.reader;
        return [owner,reader,rank](int stage,int r,int macro,int row) {
            require(!owner->stopped&&stage==37&&r==int(rank)&&macro>=0&&macro<9668&&row>=0&&row<4096,
                    "L20 static source read ownership");
            try{return reader->read(unsigned(stage),unsigned(r),unsigned(macro),unsigned(row));}
            catch(...){owner->stopped=true;throw;}
        };
    }
    require(bool(owner->dynamic),"L20 source node not enrolled");
    auto read=owner->dynamic->word_reader(node,rank,fragment);
    return [owner,read](int stage,int r,int macro,int row) {
        require(!owner->stopped,"L20 source quarantined");
        try{return read(stage,r,macro,row);}catch(...){owner->stopped=true;throw;}
    };
}
DsromS81MinimumL20SourceWords::HeRead DsromS81MinimumL20SourceWords::he_words(unsigned rank) {
    require(rank<4,"L20 HE rank");auto owner=impl_;
    return [owner,rank](bool ffn,uint64_t line) {
        require(!owner->stopped&&line<61440,"L20 HE source ownership");
        try {
            auto raw=owner->he[rank]->read(ffn?1:0,rank,uint32_t(line),uint32_t(line>>32));
            require(raw[8]==0,"HE source exceeds256bits");
            std::array<uint32_t,8> out{};std::copy_n(raw.begin(),8,out.begin());return out;
        }catch(...){owner->stopped=true;throw;}
    };
}
void DsromS81MinimumL20SourceWords::captured_i93(unsigned rank,uint64_t id,
    const DsromS81DelayedEidSessions::Eids& ids) {
    require(!impl_->stopped&&bool(impl_->dynamic),"L20 dynamic source unavailable");
    try{impl_->dynamic->captured_i93(rank,id,2564,ids);}catch(...){impl_->stopped=true;throw;}
}
bool DsromS81MinimumL20SourceWords::advance_captured_bindings() {
    require(!impl_->stopped,"L20 source quarantined");
    try{return !impl_->dynamic||impl_->dynamic->advance_captured_bindings();}
    catch(...){impl_->stopped=true;throw;}
}
bool DsromS81MinimumL20SourceWords::bound(const std::string& node,unsigned rank,unsigned fragment) {
    return !impl_->stopped&&impl_->dynamic&&impl_->dynamic->bound(node,rank,fragment);
}
bool DsromS81MinimumL20SourceWords::fault()const {
    return impl_->stopped||(impl_->dynamic&&impl_->dynamic->fault());
}
