"""Expose existing native result producer/output to the add-only ReadResult binder.

Layer after selected S81 capture/WAVE ports. Original engine/controller untouched.
No clock, model generation, arithmetic or full-stage visibility is added.
"""
from pathlib import Path
import hashlib

TOP='ot_v41_rt_die_l20_c8.sv'
PORTS='''    output wire native_result_selected,native_result_active,
    output wire native_result_producer_take,native_result_am_any,
    output wire native_result_end_take,native_result_done,
    output wire [46:0] native_result_identity,
    output wire [13:0] native_result_entry,native_result_pc,
    output wire [20:0] native_result_token,
    output wire [31:0] native_result_value,
'''
EXPORTS='''
    // Existing engine signals only; fresh producer provenance is retained by
    // the caller binder. END/retire alone does not authorize full-stage output.
    assign native_result_selected = NATIVE_RESULT_READ != 0;
    assign native_result_active = NATIVE_RESULT_READ && c8_stage_active;
    assign native_result_identity = c8_engine_identity;
    assign native_result_entry = c8_engine_entry;
    assign native_result_pc = dbg_pc;
    assign native_result_done = NATIVE_RESULT_READ && done;
    assign native_result_producer_take = NATIVE_RESULT_READ &&
        dut.u_tile.u_core.e_go[dut.u_tile.u_core.EAM] &&
        dut.u_tile.u_core.e_ready[dut.u_tile.u_core.EAM] && dut.u_tile.u_core.me_amax;
    assign native_result_am_any = NATIVE_RESULT_READ && dut.u_tile.u_core.am_any_v[0];
    assign native_result_end_take = NATIVE_RESULT_READ && !fault &&
        dut.u_tile.u_core.st == 4'd6 && dut.u_tile.u_core.d_unit == 3'd0 &&
        dut.u_tile.u_core.d_ctl == 3'd0 && dut.u_tile.u_core.waited;
'''


def one(s,old,new):
    if s.count(old)!=1:raise ValueError('actual native result hook changed: '+old)
    return s.replace(old,new,1)


def transform(s):
    s=one(s,'module ot_v41_rt_die_l20_c8 #(\n','module ot_v41_rt_die_l20_c8 #(\n    parameter integer NATIVE_RESULT_READ=0,\n')
    s=one(s,') (\n',') (\n'+PORTS)
    s=one(s,'.core_next_token(), .core_next_val()', '.core_next_token(native_result_token), .core_next_val(native_result_value)')
    return one(s,'\nendmodule',EXPORTS+'\nendmodule')


def install(selected,output,*,enable=False):
    if type(enable)is not bool:raise ValueError('enable must be bool')
    paths=[Path(p).resolve() for p in selected['sources']];output=Path(output).resolve()
    if any(output==p.parent or output in p.parents for p in paths):raise ValueError('disjoint output required')
    original={}
    for p in paths:
        b=p.read_bytes()
        if hashlib.sha256(b).hexdigest()!=selected['source_sha256'].get(str(p)):
            raise ValueError('selected source pin changed/missing: '+str(p))
        original[p]=b
    matches=[p for p in paths if p.name==TOP]
    if len(matches)!=1:raise ValueError('one actual selected top required')
    p=matches[0];s=transform(original[p].decode());dest=output/'native'/TOP
    if dest.exists()and dest.read_text()!=s:raise FileExistsError(dest)
    if any(q.read_bytes()!=b for q,b in original.items()):raise ValueError('selected source changed')
    dest.parent.mkdir(parents=True,exist_ok=True)
    if not dest.exists():dest.write_text(s)
    sources=[dest if q==p else q for q in paths];r=dict(selected)
    r.update(sources=sources,source_sha256={str(q):hashlib.sha256(q.read_bytes()).hexdigest() for q in sources},
             parameters=dict(selected.get('parameters',{}),NATIVE_RESULT_READ=int(enable)),
             verilator_args=list(selected.get('verilator_args',[]))+['-GNATIVE_RESULT_READ='+str(int(enable))],
             native_terminal_producer_bound=False,physical_admission=False,measured_system_result=False)
    return r
