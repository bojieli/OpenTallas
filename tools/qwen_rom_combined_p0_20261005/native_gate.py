#!/usr/bin/env python3
"""Short changed-host gate: real preloads/edges/pins, retained model only.
No PASS is inferred from emission. Serial baseline/patch traces must match.
"""
import argparse, hashlib, json, re
from pathlib import Path
from native_fabric_patch import patch
from native_settle_patch import prepare, replace_once


def fields(header):
    return re.findall(r'^\s*(?:CData|SData|IData|QData|VlWide<\d+>|VlUnpacked<.*?>)/?[^;\n]*?\s+(ot_qwen\w+)\s*;', header, re.M)


def ports(header):
    return re.findall(r'VL_(?:IN|OUT)(?:8|16|64|W)?\(&([\w]+),', header)


def emit(a):
    a.output.mkdir()
    host=a.output/'host'; host.mkdir()
    dirty=patch(a.source.read_text(), True)
    (host/'dirty.cpp').write_text(dirty)
    prepare(host/'dirty.cpp', host/'gate.cpp')
    s=(host/'gate.cpp').read_text()
    s=replace_once(s, '    void eval_changed() {',
        '    void eval_changed() {\n'
        '        if(!getenv("QWEN_P0_NATIVE_DIRTY") || strcmp(getenv("QWEN_P0_NATIVE_DIRTY"),"1")) { eval(); return; }')
    s=replace_once(s, '    uint64_t native_full_tile_evals = 0, native_changed_tile_evals = 0;',
        '    uint64_t native_full_tile_evals = 0, native_changed_tile_evals = 0, native_invalidations = 0;')
    s=replace_once(s, '    void invalidate_all() {', '    void invalidate_all() {\n        ++native_invalidations;')
    dieports=ports(a.die_header.read_text()); tileports=ports(a.tile_header.read_text())
    root=a.root_header.read_text()
    pc='stack__BRA__0__KET____DOT__pc__BRA__0__KET__'
    # Entire actual PC0 landing incl code memory, held decoder payload/owner,
    # pointer rails and all18 selectors. Additional ranks use same field layout.
    names=[n for n in fields(root) if pc in n and '__DOT__u_l__DOT__' in n and '____V' not in n]
    consumer=[n for n in fields(root) if '__DOT__u_consumer__DOT__' in n and
        ('__DOT__u_kv__DOT__' in n or n.endswith('__DOT__w_valid')) and
        '__DOT__core__' not in n and '____V' not in n]
    names+=consumer
    injection=[n for n in names if n.endswith('r9_read__DOT__column__BRA__0__KET____DOT__u_sel__DOT__primary')]
    held=[n for n in names if n.endswith('__DOT__u_d3__DOT__primary')]
    if len(injection)!=1 or len(names)<50 or not dieports or not tileports:
        raise ValueError('actual generated ports/landing primary state not found')
    # Hash typed fields only: no pointer/padding/scheduler cache. All public
    # die/tile pins at every settled clock event; protected PC0 state all ranks.
    pre='''\nstatic uint64_t gate_hash(uint64_t h,const void* data,size_t n) {
    const auto* p=static_cast<const uint8_t*>(data);
    for(size_t i=0;i<n;++i) {h^=p[i]; h*=1099511628211ull;} return h;
}
template<class T> static void gate_add(uint64_t& h,const T& x) {
    h=gate_hash(h,&x,sizeof(x));
}
'''
    s=replace_once(s, 'struct Fabric {', pre+'\nstruct Fabric {')
    observe='''    bool native_negative=false;
    uint64_t native_events=0,native_dirty_captures=0,native_fault_events=0,native_held_valid=0;
    FILE* native_trace=fopen((dir+"/events.txt").c_str(),"wx");
    if(!native_trace) fatal("native event trace create");
    auto native_observe=[&](uint64_t fs) {
        uint64_t pins=1469598103934665603ull,state=pins;
        unsigned fill=0, fault=0, captures=0;
        for(int d=0;d<D;++d) {
            auto& v=*die[d]; auto* r=v.rootp;
'''
    observe+=''.join('            gate_add(pins,v.'+n+');\n' for n in dieports)
    observe+=''.join('            gate_add(state,r->'+n+');\n' for n in names)
    observe+='            native_held_valid+=bool((r->'+held[0]+'[9]>>1)&1);\n'
    observe+='''            fill+=v.st_fill_sectors;
            fault|=(v.rt_rst_n && (v.mem_fault || v.core_fault || v.s_fault || coll.fault))<<d;
            for(auto& ptr:fab[d]->t) {auto& t=*ptr;
'''
    observe+=''.join('                gate_add(pins,t.'+n+');\n' for n in tileports)
    observe+='''                captures+=bool(t.kvw_ce && t.clk);
            }
        }
        native_dirty_captures+=captures; native_fault_events+=bool(fault);
        if(fault && !native_negative) fatal("native positive active fault");
        fprintf(native_trace,"%llu %016llx %016llx fill=%u captures=%u fault=%u negative=%d\\n",
            (unsigned long long)fs,(unsigned long long)pins,(unsigned long long)state,fill,captures,fault,int(native_negative));
        ++native_events;
    };
'''
    s=replace_once(s,'    qwen_combined_p0::Clocks clocks;',observe+'    qwen_combined_p0::Clocks clocks;')
    s=s.replace('}, [&] { settle(live_all); });','}, [&] { settle(live_all); }, native_observe);')
    if s.count('}, native_observe);')!=2: raise ValueError('actual both clock callsites missing')
    s=replace_once(s,'            if (mf) {','            if (mf && !native_negative) {')
    # Negative happens after448 real core cycles of actual startup/fill, with
    # observed fill+KV clock captures mandatory; no reset or injected ready.
    kv_fields=[n for n in fields(a.tile_root_header.read_text()) if '__DOT__g_kv__' in n and n.endswith('__DOT__arr')]
    if len(kv_fields)!=2: raise ValueError('actual two tile KV arrays missing')
    kv_hash=''.join('                gate_add(kv,tile->rootp->'+n+');\n' for n in kv_fields)
    body='''        if(tick==448) {
            if(!native_dirty_captures || !native_held_valid || !die[0]->st_fill_sectors) fatal("gate dirty/held phase not covered");
            die[0]->rootp->INJECT ^= uint64_t(1);
            for(int d=0;d<D;++d) fab[d]->invalidate_all();
            native_die_coll_evaluated=false;
            native_negative=true;
            printf("P0_NATIVE_NEGATIVE actual selector primary rail mutation tick=%ld\\n",tick);
            fflush(stdout);
        }
        if(tick==512) {
            uint64_t kv=1469598103934665603ull;
            for(int d=0;d<D;++d) for(auto& tile:fab[d]->t) {
KVHASH            }
            fclose(native_trace);
            double wall=std::chrono::duration<double>(std::chrono::steady_clock::now()-tstart).count();
            uint64_t full=0,changed=0,invalidations=0;
            for(int d=0;d<D;++d) {full+=fab[d]->native_full_tile_evals;changed+=fab[d]->native_changed_tile_evals;invalidations+=fab[d]->native_invalidations;}
            printf("P0_NATIVE_GATE terminal core=%u events=%llu dirty_captures=%llu fault_events=%llu kv_hash=%016llx wall=%.9f wall_per_core=%.9f full_tile_evals=%llu changed_tile_evals=%llu invalidations=%llu die_evals=%llu coll_evals=%llu reentry_skip=%llu die_ns=%llu coll_ns=%llu fabric_comb_ns=%llu fabric_edge_ns=%llu propagate_ns=%llu full_token=0\\n",
                die[0]->cyc,(unsigned long long)native_events,(unsigned long long)native_dirty_captures,(unsigned long long)native_fault_events,(unsigned long long)kv,wall,wall/513,
                (unsigned long long)full,(unsigned long long)changed,(unsigned long long)invalidations,(unsigned long long)native_die_evals,(unsigned long long)native_coll_evals,(unsigned long long)native_reentries_skipped,
                (unsigned long long)native_die_ns,(unsigned long long)native_coll_ns,(unsigned long long)native_fabric_comb_ns,(unsigned long long)native_fabric_edge_ns,(unsigned long long)native_propagate_ns);
            fflush(stdout);
            return native_fault_events && native_dirty_captures ? 0:1;
        }
'''.replace('INJECT',injection[0]).replace('KVHASH',kv_hash)
    s=replace_once(s, '        if (tick % progress_every == 0) {',body+'        if (tick % progress_every == 0) {')
    (host/'gate.cpp').write_text(s)
    clock=a.clock_header.read_text()
    clock=clock.replace('class Settle>','class Settle, class Observe>')
    clock=clock.replace('Settle settle) {','Settle settle, Observe observe) {')
    clock=clock.replace('controller(h_); settle();','controller(h_); settle(); observe(next_h_);')
    clock=clock.replace('core(); settle(); now_ = time_fs;','core(); settle(); observe(time_fs); now_ = time_fs;')
    (host/'clock.hpp').write_text(clock)
    record=dict(status='EMITTED_NOT_COMPILED',core_prefix=513,negative_tick=448,
        source_sha256=hashlib.sha256(a.source.read_bytes()).hexdigest(),
        output_sha256=hashlib.sha256(s.encode()).hexdigest(),
        die_pins=dieports,tile_pins=tileports,protected_state_fields=names,
        negative_primary=injection[0],state_scope='PC0 full landing all ranks + consumer KV ownership; all die/tile pins; final all tile KV RAM',
        full_token_pass=False,physical_qualified=False)
    (a.output/'gate_source.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps({k:v for k,v in record.items() if k not in ['die_pins','tile_pins','protected_state_fields']}))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['source','output','die-header','tile-header','tile-root-header','root-header','clock-header']:
        p.add_argument('--'+name,type=Path,required=True)
    emit(p.parse_args())
