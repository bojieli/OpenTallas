"""Add host logging of EXISTING debug ports only; no RTL/getters/timer changes."""
from pathlib import Path
SOURCE='4e38326d6f361bc85e660f48c59c355e2bb95274'
ORIGINAL='rtl/test/v41_runtime/w17_current_fastpp_die_rt.cpp'
COPY='rtl/test/v41_runtime/w17_existing_port_trace_die_rt.cpp'
A='''        if (cyc % 200 == 0) {
            double el = std::chrono::duration<double>(std::chrono::steady_clock::now() - t1).count();'''
B='''        if (cyc % 200 == 0) {
            // Existing public debug ports only; this is host observation, not
            // owned retirement, provider progress, or a service bound.
            for (int rank=0;rank<4;++rank) {
                uint64_t ds=dies[rank]->dstate();
                printf("CORE_TRACE cyc=%ld rank=%d pc=%u busy=%02x last_issued=%u core_st=%u decoded_unit=%u idles=%02x waited=%u cdma_words=%08x fault=%02x done=%u owned_reads=UNAVAILABLE provider_retirement=UNAVAILABLE\\n",
                    cyc,rank,dies[rank]->pc(),dies[rank]->busy(),dies[rank]->issue(),
                    unsigned((ds>>24)&15),unsigned((ds>>21)&7),unsigned((ds>>16)&31),
                    unsigned((ds>>14)&1),dies[rank]->dwords(),dies[rank]->fault(),unsigned(dies[rank]->done()));
            }
            fflush(stdout);
            double el = std::chrono::duration<double>(std::chrono::steady_clock::now() - t1).count();'''
GUARD='''#ifndef W17_EXISTING_PORT_TRACE_OPT_IN
#error "existing-port trace copy requires explicit W17_EXISTING_PORT_TRACE_OPT_IN"
#endif
'''
def transform(text):
    if text.count(A)!=1:raise ValueError('exact source progress anchor')
    return GUARD+text.replace(A,B)
def inverse(text):
    if not text.startswith(GUARD) or text.count(B)!=1:raise ValueError('exact trace inverse')
    return text[len(GUARD):].replace(B,A)
