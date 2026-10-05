"""Additive real generated-port driver binding; prepares source, never compiles."""
from pathlib import Path
import hashlib,json
SOURCE='4e38326d6f361bc85e660f48c59c355e2bb95274'
BASE='rtl/test/v41_runtime/w17_future_validated_fastpp_die_rt.cpp'
COPY='rtl/test/v41_runtime/w17_connected_observation_die_rt.cpp'
HEADER='tools/runtime/w17_connected_observation_capture.hpp'

def transform(text):
    changes=[]
    def replace(a,b):
        nonlocal text
        if text.count(a)!=1:raise ValueError('exact capture transformation count')
        changes.append(dict(before=a,after=b));text=text.replace(a,b)
    replace('#include "Vdie0.h"','''#if !defined(W17_FULLTOKEN_OBSERVATION_OPT_IN) || W17_FULLTOKEN_OBSERVATION_OPT_IN != 1
#error "Connected observation copy requires new reviewed build plan; no live binding"
#endif
#if !defined(W17_FUTURE_BIND_DBG_FS)
#error "Source-pinned real sticky fault port binding required"
#endif
#include "../../../tools/runtime/w17_connected_observation_capture.hpp"
#include "Vdie0.h"''')
    replace('    virtual void eval() = 0;','    virtual void eval() = 0;\n    virtual void observation_edge(uint64_t host_cycle) = 0;')
    replace('        d->clk = 0; d->rst_n = 0; d->eval();','        d->sim_obs_epoch = 1; // fresh process reset era; no cross-reset fence claim\n        d->clk = 0; d->rst_n = 0; d->eval();')
    replace('    void eval() override { d->eval(); }','''    void eval() override { d->eval(); }
    void observation_edge(uint64_t host_cycle) override {
        if(d->sim_obs_valid) w17_capture::trace->edge(unsigned(id),host_cycle,d->sim_obs_packet,
            bool(d->done),uint32_t(d->fault),uint32_t(d->dbg_fs),uint64_t(d->dbg_state));
    }''')
    replace('    RtPool pool(threads);','''    if(wrong) throw std::invalid_argument("wrong-edge is not connected qualification");
#ifdef V41_L20
    w17_capture::trace.reset(new w17_capture::Trace(true));
#else
    w17_capture::trace.reset(new w17_capture::Trace(false));
#endif
    RtPool pool(threads);''')
    replace('''            for (auto& d : dies) { d->field_propagate(); d->att_propagate(); }
        } else {''','''            // Joined rising-edge tasks complete. Drain registered pre-edge packet once,
            // before propagation/settling; post-edge debug fault/DONE are separate metadata.
            for (auto& d : dies) d->observation_edge(uint64_t(cyc));
            for (auto& d : dies) { d->field_propagate(); d->att_propagate(); }
        } else {''')
    return text,changes

def inverse(text,changes):
    for c in reversed(changes):
        if text.count(c['after'])!=1:raise ValueError('capture inverse count')
        text=text.replace(c['after'],c['before'])
    return text

if __name__=='__main__':
    root=Path(__file__).resolve().parents[1];base=(root/BASE).read_text();text,changes=transform(base)
    assert inverse(text,changes)==base
    with (root/COPY).open('x') as f:f.write(text)
    print(json.dumps(changes,indent=2))
