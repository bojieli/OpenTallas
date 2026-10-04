#include "s81_minimum_hbm.hpp"
#include "svdpi.h"
#include <filesystem>
#include <fstream>
#include <sstream>
namespace dsrom_s81_minimum {
NativeHbm::NativeHbm(DsromS81MinimumRuntime&r,const std::string& name)
:runtime(r),model(r.context,name.c_str()) {
    if(!r.context||!r.cycle||r.identity)throw std::runtime_error("HBM requires cold canonical runtime");
    model.clk=0;model.rst_n=0;model.eval();
}
void NativeHbm::preload(const std::string& directory) {
    if(admitted||runtime.identity||model.history_ready||!drained())
        throw std::runtime_error("HBM preload after history/context admission");
    // Validate literal sparse address carrier BEFORE native readmemh: no modulo,
    // generated current row, default path, missing stack or zero-fill substitute.
    for(unsigned s=0;s<4;s++) {
        auto path=std::filesystem::path(directory)/("hbm_s"+std::to_string(s)+".hex");
        std::ifstream f(path);if(!f)throw std::runtime_error("missing retained HBM stack image");
        std::string token;uint64_t address=0;bool positioned=false,any=false;
        while(f>>token) {
            if(token[0]=='@'){address=std::stoull(token.substr(1),nullptr,16);positioned=true;}
            else {
                if(!positioned||address>=model.capacity_words||token.size()!=64||
                   token.find_first_not_of("0123456789abcdefABCDEF")!=std::string::npos)
                    throw std::runtime_error("invalid/out-of-bounds native HBM sparse sector");
                ++address;any=true;
            }
        }
        if(!any)throw std::runtime_error("empty retained HBM stack image");
    }
    std::string scope=std::string(model.name())+".DsromS81Hbm";
    auto native_scope=svGetScopeFromName(scope.c_str());
    if(!native_scope)throw std::runtime_error("native HBM preload scope absent: "+scope);
    auto old=svSetScope(native_scope);
    VDsromS81Hbm::s81_hbm_preload(directory.c_str());
    svSetScope(old);model.eval();
    if(!model.history_ready)throw std::runtime_error("native HBM preload did not finish");
}
void NativeHbm::preload_ckv(const std::string& directory) {
    if(admitted||runtime.identity||!model.history_ready||model.ckv_history_ready||!drained())
        throw std::runtime_error("CKV history init lacks cold backend/base history");
    for(unsigned s=0;s<4;s++) {
        std::ifstream f(std::filesystem::path(directory)/("ckv_s"+std::to_string(s)+".hex"));
        if(!f)throw std::runtime_error("missing retained CKV stack source");
        std::string a,word;bool any=false;
        while(f>>a) {
            if(!(f>>word))throw std::runtime_error("truncated retained CKV image");
            uint64_t address=std::stoull(a,nullptr,16);
            if(address<4194304||address>=model.capacity_words||word.size()!=64||
               word.find_first_not_of("0123456789abcdefABCDEF")!=std::string::npos)
                throw std::runtime_error("CKV source address/carrier invalid");
            any=true;
        }
        if(!any)throw std::runtime_error("empty retained CKV stack source");
    }
    auto scope=svGetScopeFromName((std::string(model.name())+".DsromS81Hbm").c_str());
    if(!scope)throw std::runtime_error("native CKV history init scope missing");
    auto old=svSetScope(scope);
    VDsromS81Hbm::s81_hbm_preload_ckv(directory.c_str());svSetScope(old);model.eval();
    if(!model.ckv_history_ready)throw std::runtime_error("native CKV history load unfinished");
}
NativeHbmTrafficSnapshot NativeHbm::traffic()const {return traffic_counters.snapshot();}
DsromS81MinimumParticipant NativeHbm::participant() {
    auto self=shared_from_this();
    return {"native-four-stack-HBM",
      [self](const auto&) {
        if(!self->join||!self->initialized())throw std::runtime_error("HBM missing borrowed mux/history binding");
        self->model.clk=0;
        // Two re-joins settle ready/response feedback before ANY rising edge.
        self->join();self->join();
        auto&m=self->model;
        self->accepted=m.m_v&m.m_rdy;self->write_mask=m.m_we;
        self->returned=m.s_v&m.s_rdy;self->committed=m.m_wr_done;
        for(unsigned s=0;s<4;s++) {
            self->lengths[s]=(m.m_len>>(4*s))&15;
            self->request_owner[s]=(m.m_tag>>(16*s+14))&3;
            self->response_owner[s]=(m.s_tag>>(16*s+14))&3;
            self->write_strobes[s]=m.m_wstrb[s];
        }
        self->prepared=self->runtime.cycle();
      },
      [self](bool released) {
        if(!released&&!self->drained())throw std::runtime_error("reset erases HBM accepted debt");
        if(released) {
          if(self->prepared!=self->runtime.cycle())throw std::runtime_error("HBM lacks shared pre-edge prepare");
          for(unsigned s=0;s<4;s++) {
            unsigned bit=1u<<s;
            if(self->accepted&bit){self->admitted=true;
              if(self->write_mask&bit)++self->writes[s];else self->reads[s]+=self->lengths[s];}
            if(self->returned&bit){if(!self->reads[s])throw std::runtime_error("HBM response without accepted read");--self->reads[s];}
            if(self->committed&bit){if(!self->writes[s])throw std::runtime_error("HBM write completion without accepted write");--self->writes[s];}
          }
          // Count ONCE on actual released rising edge, never in prepare/offer.
          self->traffic_counters.sample(self->runtime.cycle(),self->accepted,
              self->returned,self->committed,self->write_mask,self->lengths,
              self->request_owner,self->response_owner,self->write_strobes);
        }
        self->model.rst_n=released;self->model.clk=1;self->model.eval();
      },
      [self](bool released){self->model.rst_n=released;self->model.clk=0;self->model.eval();},
      [self](){return bool(self->model.fault);}};
}
}
