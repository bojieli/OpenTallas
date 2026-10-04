#pragma once
#include <cstdint>
#include <stdexcept>
#include <vector>
#include "dsrom_c8_source_dispatch.hpp"

// Actual-source VM carry/input loading for simulation. No arithmetic, golden
// input generation, implicit context ACK, physical SRAM-port or rate claim.
// Capture once under the real source visibility callback, then retain those
// words until every destination setup write has succeeded.
class DsromS81Workspace {
    int source_die, target_die;
    uint64_t source_identity, target_identity;
    uint32_t source_address, target_address;
    std::vector<uint32_t> words;
    size_t next_word=0;
    bool captured=false;
public:
    DsromS81Workspace(int source_die_,uint64_t source_identity_,uint32_t source_address_,
                     int target_die_,uint64_t target_identity_,uint32_t target_address_,size_t count)
      :source_die(source_die_),target_die(target_die_),source_identity(source_identity_),
       target_identity(target_identity_),source_address(source_address_),target_address(target_address_),words(count) {
        if(source_die<0 || source_die>=324 || target_die<0 || target_die>=324 ||
           source_identity>=(uint64_t(1)<<47) || target_identity>=(uint64_t(1)<<47) ||
           count==0 || count>(1u<<19) || source_address>(1u<<19)-count ||
           target_address>(1u<<19)-count)
            throw std::runtime_error("actual S81 workspace owner/span bounds");
    }
    template<class SourceDie,class Visibility>
    bool capture(SourceDie& source,int physical_die,Visibility& source_visible) {
        if(physical_die!=source_die)throw std::runtime_error("workspace source physical owner mismatch");
        if(captured)return true;
        // Native producer visibility and retained source lease must authorize
        // the exact identity/range. Local done/idle is never substituted here.
        if(!source_visible(source_die,source_identity,source_address,words.size()))return false;
        for(size_t i=0;i<words.size();i++)words[i]=source.vm_word(source_address+uint32_t(i));
        captured=true;return true;
    }
    template<class TargetDie>
    size_t load(TargetDie& target,int physical_die,size_t max_words) {
        if(physical_die!=target_die)throw std::runtime_error("workspace destination physical owner mismatch");
        if(!captured || max_words==0)return 0;
        size_t written=0;
        while(next_word<words.size() && written<max_words) {
            if(!target.c8_workspace_write(target_identity,target_address+uint32_t(next_word),words[next_word]))break;
            next_word++;written++;
        }
        return written;
    }
    bool setup_complete() const {return captured && next_word==words.size();}
    uint64_t identity() const {return target_identity;}
    // Caller combines setup_complete with actual native input/lease visibility
    // and field/VM/reverse debt fences before C8 context_restored. This class
    // never drives restoration, offers, retirement, clocks, reset or a fence.
};
