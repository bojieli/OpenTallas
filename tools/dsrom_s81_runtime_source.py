"""Wire the native S81 field to Rawls's unchanged strict-pruned return model.

Source preparation only. This replaces historical padded host connectivity with
one actual ot_v41_return_rd64_pruned model, preserving pre-edge evaluation.
"""
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
HOST='rtl/test/v41_runtime/w17_current_fastpp_c8_s82_rt.cpp'
CLIENT='rtl/test/v41_runtime/dsrom_s82_rom_client.hpp'


def transform_host(source):
    def one(old,new):
        nonlocal source
        if source.count(old)!=1:raise ValueError('actual host interface changed: '+old[:90])
        source=source.replace(old,new,1)
    one('//   Vretn         ot_v41_retn (one return-tree node + its wire stages)\n//   Vroot         ot_v41_ret_root (one per return region)',
        '//   Vrd64        canonical strict-pruned return; 5090 retained nodes and128 roots')
    one('        meta = load_meta(dir + "/field.txt");',
        '        meta = load_meta(dir + "/field.txt");\n#if !DSROM_C8_S81\n        throw std::runtime_error("S81 native runtime is default-off; select DSROM_C8_S81=1");\n#endif')
    source=source.replace('DSROM_C8_S82','DSROM_C8_S81').replace('DSROM_S82_STAGE','DSROM_S81_STAGE')
    source=source.replace('dsrom_s82','dsrom_s81').replace('S82','S81')
    one('#include "Vretn.h"\n#include "Vroot.h"','#include "Vrd64.h"')
    one('#include "Vrd64.h"','#include "Vrd64.h"\n#ifndef DSROM_S81_CAPTURE\n#define DSROM_S81_CAPTURE 0\n#endif')
    one('extern "C" int v41rt_vm_word(int a);',
        'extern "C" int v41rt_vm_word(int a);\nextern "C" int v41rt_c8_workspace_write(uint64_t identity, int address, int raw_bits);')
    one('    virtual void c8_observe(long)=0;',
        '    virtual void c8_observe(long)=0;\n    virtual bool c8_workspace_write(uint64_t identity, uint32_t address, uint32_t raw_bits)=0;')
    one('    long c8_observed_cycle=-1;', '''    bool c8_workspace_write(uint64_t identity,uint32_t address,uint32_t raw_bits) override {
        if(identity>=(uint64_t(1)<<47) || address>=(1u<<19))
            throw std::runtime_error("actual C8 workspace identity/address bounds");
        uint64_t live_identity;uint32_t live_token;uint16_t live_entry;
        if(!c8_context(live_identity,live_token,live_entry) || live_identity!=identity)
            return false;
        svSetScope(g_diescope[id]);
        // Source input loading only. This cannot grant context restoration or
        // fabricate a native write/drain ACK; the caller still owes both.
        return v41rt_c8_workspace_write(identity,int(address),int(raw_bits))==0;
    }
    long c8_observed_cycle=-1;''')
    one('    virtual void c8_observe(long)=0;',
        '    virtual void c8_observe(long)=0;\n    virtual void capture_warm_reset(bool request)=0;\n    virtual bool capture_visible(uint64_t identity)=0;')
    one('    long c8_observed_cycle=-1;', CAPTURE_RUNTIME+'    long c8_observed_cycle=-1;')
    one('        d->clk = 0; d->rst_n = 0; d->eval();',
        '        d->clk = 0; d->rst_n = 0;\n#if DSROM_S81_CAPTURE\n        d->capture_reset_request=0; for(auto& word:d->capture_root_rows)word=0;\n#endif\n        d->eval();')
    one('    int NL, L, LR, LS;','    int NL;')
    one('    std::vector<std::vector<std::unique_ptr<Vretn>>> nodes;\n    std::vector<std::unique_ptr<Vroot>> roots;\n    std::vector<int> return_owner;',
        '    std::unique_ptr<Vrd64> rd64; // actual strict-pruned 5090-node source, not a contracted tree')
    source=source.replace('2388','2417')
    one('meta.bf.size()!=512','meta.bf.size()!=519')
    one('source_stage>=82','source_stage>=81')
    one('        return_owner.assign(4096,-1);\n        for(int pair=0;pair<2417;pair++)return_owner[dsrom_s81::return_pair(pair)]=pair;\n        NL=8192;',
        '        NL=4834; // exact active two-bank leaves')
    one('         L = __builtin_ctz(NL); LR = __builtin_ctz(meta.r); LS = L - LR;','')
    a=source.index('        nodes.resize(LS);');b=source.index('\n    }\n    template <class F>',a)
    source=source[:a]+'''        rd64.reset(new Vrd64(pool.ctx((k++) % pool.size()), ("d"+std::to_string(die_id)+"rd64").c_str()));
'''+source[b:]
    one('    size_t nmodels() const { size_t n = act.size() + roots.size(); for (auto& l : nodes) n += l.size(); return n; }',
        '    size_t nmodels() const { return act.size()+1; }')
    a=source.index('    bool node_skip(Vretn& n)');b=source.index('    void model_at(',a);source=source[:a]+source[b:]
    a=source.index('        i -= act.size();');b=source.index('\n    }\n    void update_bus_go()',a)
    source=source[:a]+'''        if(i!=act.size())throw std::runtime_error("S81 return model index");
        rd64->clk=clk;rd64->rst_n=rst;rd64->eval();
'''+source[b:]
    a=source.index('    Node level_out(');b=source.index('    // the die\'s broadcast bus',a);source=source[:a]+source[b:]
    a=source.index('    void to_node(');b=source.index('\n};\n\n// ',a)
    source=source[:a]+PROPAGATE+source[b:]
    return source


PROPAGATE=r'''    void propagate() {
        update_bus_go();
        pool.run(act.size(), [&](size_t i) { each_pair(act[i], [&](auto& m) { bcast(m); }); });
        // Rawls canonical leaf_bus_index = 2*actual_pair+side. Never expose an
        // invented READY or drop a valid while a source root owes work.
        for(int pair=0;pair<2417;pair++)for(int side=0;side<2;side++) {
            Node a=leaf(pair,side);size_t i=2*pair+side;
            setb(rd64->lv,i,1,a.v);setb(rd64->le,i,1,a.e);
            setb(rd64->lt,32*i,32,a.t);setb(rd64->ld,32*i,32,a.d);
        }
        for(int region=0;region<128;region++) {
            size_t o=69*region;
            setb(die.rom_fr,o,1,getb(rd64->re,region,1));
            setb(die.rom_fr,o+1,16,getb(rd64->rbf16,16*region,16));
            setb(die.rom_fr,o+17,32,getb(rd64->rfp32,32*region,32));
            setb(die.rom_fr,o+49,3,getb(rd64->rpos,3*region,3));
            setb(die.rom_fr,o+52,16,getb(rd64->rrow,16*region,16));
            setb(die.rom_fr,o+68,1,getb(rd64->rv,region,1));
        }
        uint64_t f=rd64->fault;
        for(int pair:act)each_pair(pair,[&](auto& m){f|=m.fault;});
        die.rom_ffault=f?1:0;
    }
'''


def transform_client(source):
    source=source.replace('dsrom_s82','dsrom_s81').replace('DSROM_S82','DSROM_S81').replace('S82','S81')
    source=source.replace('stage>=82','stage>=81').replace('2388','2417')
    # The host uses the actual graph; prohibit this old padded coordinate API.
    a=source.index('inline int return_pair(')
    source=source[:a]+'}\n'
    return source


def prepare(output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    transformed={'w17_current_fastpp_c8_s81_rt.cpp':transform_host((ROOT/HOST).read_text()),
                 'dsrom_s81_rom_client.hpp':transform_client((ROOT/CLIENT).read_text())}
    for n,s in transformed.items():
        p=output/n
        if p.exists() and p.read_text()!=s:raise FileExistsError(p)
    for n,s in transformed.items():
        p=output/n
        if not p.exists():p.write_text(s)
    return [output/n for n in transformed]

# No reset debt is erased here. Cold rst_n remains a coordinated all-copy fence.
CAPTURE_RUNTIME=r'''
    void capture_warm_reset(bool request) override {
#if DSROM_S81_CAPTURE
        d->capture_reset_request=request;
#else
        if(request)throw std::runtime_error("capture reset requires selected S81 capture source");
#endif
    }
    bool capture_visible(uint64_t identity) override {
#if DSROM_S81_CAPTURE
        if(identity>=(uint64_t(1)<<47))throw std::runtime_error("capture identity bounds");
        // Real C8 quiet requires actual helper drained (cold empty or completed), alongside
        // native KV publication. FIFO empty or host grant cannot satisfy it.
        return d->capture_identity==identity && d->c8_write_quiet &&
               !d->capture_live && !d->capture_fault && !d->c8_write_quarantine;
#else
        return false;
#endif
    }
'''
