#!/usr/bin/env python3
"""Exact source transformation; prepares only, never compiles/selects a driver."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
PIN='4e38326d6f361bc85e660f48c59c355e2bb95274'
ORIGINAL='rtl/test/v41_runtime/w17_current_fastpp_die_rt.cpp'
SHA='8d1b7a553adc8882d4dd7c5f1c8bff53c34754eb5859be1804a436324a1cea04'
COPY='rtl/test/v41_runtime/w17_future_validated_fastpp_die_rt.cpp'


def source():
    raw=subprocess.check_output(['git','show',PIN+':'+ORIGINAL],cwd=ROOT)
    if hashlib.sha256(raw).hexdigest()!=SHA: raise ValueError('original driver source pin mismatch')
    return raw.decode()


def transform(text):
    changes=[]
    def replace(old,new,name):
        nonlocal text
        if text.count(old)!=1: raise ValueError('exact transformation count: '+name)
        offset=text.index(old)
        text=text.replace(old,new);changes.append({'name':name,'offset':offset,'before':old,'after':new})
    replace('#include "Vdie0.h"', '''// NEW opt-in validation copy only. Protected original stays unchanged.
#if !defined(W17_FUTURE_DRIVER_VALIDATION_OPT_IN) || W17_FUTURE_DRIVER_VALIDATION_OPT_IN != 1
#error "Future driver requires parent review and explicit opt-in; no source-list adoption"
#endif
#include "../../../tools/runtime/w17_future_driver_validation.hpp"
#include "Vdie0.h"''','opt-in guard/header')
    replace('f->skip_on = atoi(e) != 0;', 'f->skip_on = w17_future::boolean(e,"RT_SKIP");','strict skip')
    replace('    virtual uint32_t issue() = 0;', '''    virtual uint32_t issue() = 0;
    virtual uint32_t fault_sources() = 0; // optional existing wrapper port binding''','future interface getter')
    replace('    uint32_t issue() override { return d->issue_unit; }', '''    uint32_t issue() override { return d->issue_unit; }
    uint32_t fault_sources() override {
#ifdef W17_FUTURE_BIND_DBG_FS
        // Requires future generated classes from pinned wrapper with dbg_fs port.
        return d->dbg_fs;
#else
        return 0; // Packed sticky sources in dstate remain sampled independently.
#endif
    }''','optional generated-class getter')
    replace('int main(int argc, char** argv) {','int future_main(int argc, char** argv) {','catchable entry point')
    old='''    long maxc = (argc > 3 && argv[3][0] != '-') ? atol(argv[3]) : 2000000;
    bool wrong = false;
    for (int i = 3; i < argc; i++) if (!strcmp(argv[i], "--wrong-edge")) wrong = true;
    int threads = 16;
    if (const char* t = getenv("RT_THREADS")) threads = atoi(t);'''
    new='''    long maxc = 2000000;
    bool wrong = false, have_maxc = false;
    for (int i=3;i<argc;i++) {
        if (!strcmp(argv[i],"--wrong-edge")) wrong=true;
        else if (!have_maxc) { maxc=w17_future::cycles(argv[i],"max_cycles"); have_maxc=true; }
        else throw std::invalid_argument("unexpected argument");
    }
    int threads=16, LAT_U=48, LAT_X=177;
    long WD=5000; // unchanged PC-dwell diagnostic value, NOT a service deadline
    bool continue_fault=false;
    if (const char* t=getenv("RT_THREADS")) threads=w17_future::positive_int(t,"RT_THREADS");
    if (const char* t=getenv("RT_LAT_U")) LAT_U=w17_future::latency(t,"RT_LAT_U");
    if (const char* t=getenv("RT_LAT_X")) LAT_X=w17_future::latency(t,"RT_LAT_X");
    if (const char* t=getenv("RT_WATCHDOG")) WD=w17_future::cycles(t,"RT_WATCHDOG");
    if (const char* t=getenv("RT_CONTINUE_ON_FAULT")) continue_fault=w17_future::boolean(t,"RT_CONTINUE_ON_FAULT");
    if (const char* t=getenv("RT_SKIP")) (void)w17_future::boolean(t,"RT_SKIP");'''
    replace(old,new,'all runtime control parsing before construction')
    replace('''    int LAT_U = 48, LAT_X = 177;
    if (const char* s = getenv("RT_LAT_U")) LAT_U = atoi(s);
    if (const char* s = getenv("RT_LAT_X")) LAT_X = atoi(s);
''','', 'move link controls before construction')
    replace('rx[peer].u.q.push_back({cyc + LAT_U,', 'rx[peer].u.q.push_back({w17_future::due_at(cyc,LAT_U),','checked UCIe due timestamp')
    replace('rx[dst].x[s % 2].q.push_back({cyc + LAT_X,','rx[dst].x[s % 2].q.push_back({w17_future::due_at(cyc,LAT_X),','checked T1 due timestamp')
    replace('long t = cyc + (pkg ? CKV_LAT_U : CKV_LAT_X);','long t = w17_future::due_at(cyc,pkg ? CKV_LAT_U : CKV_LAT_X);','checked existing CKV timestamp')
    replace('        cyc++;','        cyc=w17_future::next_cycle(cyc);','checked cycle increment')
    start=text.index('    // no-progress watchdog:')
    end=text.index('        if (cyc % 200 == 0)',start)
    old=text[start:end]
    new='''    // PC silence is per-rank diagnostic only. No causal service bound exists.
    w17_future::Monitor monitor(4,cyc,maxc,WD);
    w17_future::Verdict validation;
    printf("FUTURE_VALIDATION service=BOUND_MISSING maxc=%ld pc_diag=%ld\\n",maxc,WD);
    while (cyc < maxc) {
        tick();
        std::vector<w17_future::Snapshot> samples;
        for(int d=0;d<4;d++) samples.push_back({dies[d]->pc(),dies[d]->busy(),dies[d]->issue(),
            dies[d]->fault(),dies[d]->dwords(),dies[d]->fault_sources(),dies[d]->dstate(),dies[d]->done()});
        validation=monitor.sample(cyc,samples); // latches fault BEFORE any DONE/watchdog decision
        if(validation.fault) {
            for(int d=0;d<4;d++) if(monitor.ranks()[d].sticky_fault)
                printf("FAULT die=%d cyc=%ld sticky=%08x pc=%u state=%016lx words=%08x\\n",d,cyc,
                    monitor.ranks()[d].sticky_fault,samples[d].pc,(unsigned long)samples[d].state,samples[d].words);
            fflush(stdout);
            if(!continue_fault) break; // continued diagnostics can NEVER clear failed verdict
        }
        for(int d=0;d<4;d++) if(done_at[d]<0 && samples[d].done) {
            done_at[d]=cyc;
            printf("DONE die=%d cyc=%ld core_cycles=%u fault=%02x\\n",d,cyc,dies[d]->cycles(),samples[d].fault);
        }
        for(size_t d:validation.pc_silent)
            printf("PC_DIAGNOSTIC die=%zu cyc=%ld dwell=%ld service=BOUND_MISSING pc=%u busy=%02x state=%016lx words=%08x\\n",
                d,cyc,cyc-monitor.ranks()[d].last_pc,samples[d].pc,samples[d].busy,(unsigned long)samples[d].state,samples[d].words);
        // Queue age is diagnostic: use real stored due timestamps and fixed latency.
        // Tick already called link_step once. No queue, credit or scheduling mutation.
        if(cyc%200==0 || !validation.pc_silent.empty()) {
            for(int d=0;d<4;d++) for(int lane=0;lane<3;lane++) {
                auto& line=(lane==0)?rx[d].u:rx[d].x[lane-1];
                if(!line.q.empty()) {
                    auto age=w17_future::link_age(cyc,line.q.front().first,line.lat,line.q.size());
                    printf("LINK_DIAGNOSTIC dst=%d lane=%d enqueued=%ld due=%ld age=%ld overdue=%ld queued=%zu\\n",
                        d,lane,age.enqueued,age.due,age.age,age.overdue,age.queued);
                }
            }
        }
        if(validation.all_done) break; // final status remains failed if sticky fault
        if(validation.maxc) { printf("MAXC cyc=%ld cap=%ld service=BOUND_MISSING\\n",cyc,maxc); break; }
'''
    replace(old,new,'per-rank diagnostic loop with sticky fault precedence')
    replace('''    bool all = true; for (long x : done_at) all &= x >= 0;
    printf("%s cycles=%ld''','''    bool all = validation.success;
    const char* terminal=all?"END":(validation.fault?"FAULT":(cyc>=maxc?"MAXC":"INCOMPLETE"));
    printf("%s cycles=%ld''','sticky final result')
    replace('all ? "END" : "TIMEOUT", cyc, run_s,','terminal, cyc, run_s,','explicit MAXC vs diagnostic terminal')
    append_offset=len(text)
    text+='''
int main(int argc,char** argv) {
    try { return future_main(argc,argv); }
    catch(const std::exception& e) { fprintf(stderr,"FUTURE_VALIDATION_ERROR %s\\n",e.what()); return 2; }
}
'''
    changes.append({'name':'entry exception catch','offset':append_offset,'before':'','after':text[text.rfind('\nint main('):]})
    return text,changes


def prepare(out):
    if out.exists(): raise FileExistsError('fresh transformation record required')
    text,changes=transform(source())
    target=ROOT/COPY
    if target.exists(): raise FileExistsError('new copy only; never overwrite')
    target.write_text(text)
    out.mkdir(parents=True)
    record={'status':'PREPARED_OPT_IN_COPY_NOT_FULL_DIE_COMPILED','source_commit':PIN,
       'original_path':ORIGINAL,'original_sha256':SHA,'copy_path':COPY,
       'copy_sha256':hashlib.sha256(text.encode()).hexdigest(),'changes':changes,
       'selection_gate':'parent review required before any future binary selection; no source-list change',
       'semantics':'PC watchdog value retained as diagnostic; MAXC retained as explicit execution ceiling, not causal service deadline. No busy/state/traffic deadline reset.',
       'service_bounds':'BOUND_MISSING; no causal service instrumentation or new bound',
       'dbg_fs':'optional macro getter requires future generated class port binding; no live getter attach',
       'limitations':['fake harness only; generated model binding/linking and actual driver integration uncompiled','no binary selection, payload reads, source-list change, live run/restart, hardware/timing/adoption claim']}
    (out/'transformation.json').write_text(json.dumps(record,indent=2,sort_keys=True)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True)
    prepare(p.parse_args().out)
