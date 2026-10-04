#pragma once
#include "s81_minimum_runtime.hpp"
#include "Vcut.h"
#include <memory>
#include <stdexcept>
#include <utility>

namespace dsrom_s81_minimum {
// Select callbacks for the ONE borrowed input cut; no cut/model allocation,
// private clock, raw-source ABI or alternate field/QE implementation. The
// caller gates the field/QE counterpart with the same source phase selection.
// Separate retained return models keep their own shared cold-reset owner;
// inactive HEAD never resets/evals/drives this borrowed cut, even on cold start.
// Peirce's input observes the actual existing owner's shared reset receipt.
class NativeBfHeadPhaseSelect {
    Vcut& cut;
    std::function<bool()> selected;
    DsromS81MinimumParticipant head;
    bool chosen=false,prepared=false,risen=false,stopped=false;
    static void require(bool ok,const char* why) {
        if(!ok)throw std::runtime_error(why);
    }
    void prepare(const DsromS81PairResult& old_result) {
        try {
            require(!stopped&&!prepared&&!risen,"HEAD phase shared edge reused/quarantined");
            chosen=selected(); // before ANY HEAD pin write or pair drive
            if(chosen)head.prepare(old_result);
            prepared=true;
        } catch(...) {stopped=true;throw;}
    }
    void rising(bool reset_released) {
        try {
            require(!stopped&&prepared&&!risen,"HEAD phase rising without preparation");
            require(selected()==chosen,"source phase changed during prepared native edge");
            if(chosen)head.rising(reset_released);
            risen=true;
        } catch(...) {stopped=true;throw;}
    }
    void falling(bool reset_released) {
        try {
            require(!stopped&&prepared&&risen,"HEAD phase falling without actual rising callback");
            // Use the SAME pre-edge choice, including an operation's last edge.
            if(chosen) {
                head.falling(reset_released);
                require(!head.fault(),"selected native HEAD participant fault");
            }
            prepared=false;risen=false;
        } catch(...) {stopped=true;throw;}
    }
public:
    NativeBfHeadPhaseSelect(DsromS81MinimumRuntime& runtime,Vcut& actual_borrowed_cut,
        std::function<bool()> actual_selected,DsromS81MinimumParticipant actual_head)
        :cut(actual_borrowed_cut),selected(std::move(actual_selected)),head(std::move(actual_head)) {
        require(runtime.context&&cut.contextp()==runtime.context&&selected&&
            !head.name.empty()&&head.prepare&&head.rising&&head.falling&&head.fault,
            "borrowed existing Vcut and complete native HEAD callbacks required");
    }
    bool fault()const{return stopped||(chosen&&head.fault());}
    DsromS81MinimumParticipant participant(const std::shared_ptr<NativeBfHeadPhaseSelect>& self) {
        require(self.get()==this,"HEAD phase helper lifetime mismatch");
        return {"selected-HEAD-"+head.name,
            [self](const DsromS81PairResult& old_result){self->prepare(old_result);},
            [self](bool released){self->rising(released);},
            [self](bool released){self->falling(released);},
            [self](){return self->fault();}};
    }
};

// Pass the SAME existing Vcut owned by the field/QE factory. The returned
// closures retain this host selector and the actual supplied callbacks only.
inline DsromS81MinimumParticipant dsrom_s81_select_native_bf_head_phase(
    DsromS81MinimumRuntime& runtime,Vcut& borrowed_cut,
    std::function<bool()> selected,DsromS81MinimumParticipant head) {
    auto owner=std::make_shared<NativeBfHeadPhaseSelect>(runtime,borrowed_cut,
        std::move(selected),std::move(head));
    return owner->participant(owner);
}
} // namespace dsrom_s81_minimum
