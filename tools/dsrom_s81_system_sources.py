"""Actual S81 native parent selection; original sources are never edited.

Uses the main collective installer. The kctl chain is rebased on the manifest's
FASTPP PC21 L20 core, not the historical regular-ckvsel patch target.
"""
from pathlib import Path
import hashlib
import dsrom_collective_accepted_pop as A

ROOT = Path(__file__).resolve().parents[1]
CORE = 'rtl/w17_runtime/hdc/v41x/fastpp_pc21/l20/ot_hdc_core_v41x.sv'
TILE = 'rtl/chip/ckvsel/ot_chip_v41x_tile.sv'
DRAIN = ('rtl/hdc/v41x/ot_hdc_v41x_idx_pool_adapt_drain.sv',
         'rtl/hdc/v41x/ot_hdc_v41x_idx_kstream_ring_drain.sv')


def _one(text, old, new):
    if text.count(old) != 1:
        raise ValueError('actual native interface changed: ' + old)
    return text.replace(old, new, 1)


def install(binding, original_export, output, *, drain=False, head=False,
            actual_collectives=None, trace=False, stage=None, accepted_pop=False,
            workspace=False):
    """Return actual elaborator sources/parameters, with every flag default off.

    trace is simulation-only and records commands admitted at dut.cmd_go,
    source-root identity, PC, all command fields and monotonically increasing
    per-launch ordinal. Tag wrap is never used as a transaction identity.
    No synthetic execution calendar or physical load closure is manufactured.
    """
    if head:
        raise ValueError("headreg candidate rejected; selected baseline requires head=False")
    if trace and (type(stage) is not int or not 0 <= stage < 81):
        raise ValueError("actual trace stage owner required")
    output = Path(output).resolve()
    # The canonical installer checks selected allocation and uses native_sources.
    result = A.install_s81_parent(binding, original_export, output/'collective',
                                  enable=accepted_pop)
    result['added_cycles']=0
    result['collective_price']=None
    result['head_candidate_selected']=False
    paths = result['sources']
    by_role = {}
    for role, suffix in [('core', CORE), ('tile', TILE),
                         ('die', 'ot_chip_v41x_die_owner_safe_c8.sv'),
                         ('top', 'ot_v41_rt_die_l20_c8.sv')]:
        matches = [p for p in paths if p.as_posix().endswith(suffix)]
        if len(matches) != 1:
            raise ValueError('missing/ambiguous selected native role: ' + role)
        by_role[role] = matches[0]
    if any(output == p.parent or output in p.parents for p in paths
           if p not in (by_role['die'], by_role['top'])):
        raise ValueError('output must be separate from native inputs')
    changed = {}
    for role, p in by_role.items():
        s = p.read_text()
        anchor = ('    parameter integer IDX_RING = 0,' if role in ('core','tile')
                  else '    parameter integer C8_PUBLICATION=0,')
        s = _one(s, anchor, '    parameter integer IDX_DRAIN_LOOKAHEAD=0,\n' + anchor)
        if role == 'core':
            s = _one(s, 'ot_hdc_v41x_idx_pool_adapt #(',
                     'ot_hdc_v41x_idx_pool_adapt_drain #(.DRAIN_LOOKAHEAD(IDX_DRAIN_LOOKAHEAD),')
        elif role == 'tile':
            s = _one(s, 'ot_hdc_core_v41x #(',
                     'ot_hdc_core_v41x #(.IDX_DRAIN_LOOKAHEAD(IDX_DRAIN_LOOKAHEAD),')
        elif role == 'die':
            s = _one(s, 'ot_chip_v41x_tile #(',
                     'ot_chip_v41x_tile #(.IDX_DRAIN_LOOKAHEAD(IDX_DRAIN_LOOKAHEAD),')
        else:
            s = _one(s, 'ot_chip_v41x_die_owner_safe_c8 #(',
                     'ot_chip_v41x_die_owner_safe_c8 #(.IDX_DRAIN_LOOKAHEAD(IDX_DRAIN_LOOKAHEAD),')
            s = _one(s, '    parameter integer C8_PUBLICATION=0,',
                     '    parameter integer S81_COMMAND_TRACE=0,\n    parameter integer S81_TRACE_STAGE=-1,\n    parameter integer S81_HOST_WORKSPACE=0,\n    parameter integer C8_PUBLICATION=0,')
            s = _one(s, '\nendmodule', OBSERVER + WORKSPACE + '\nendmodule')
        changed[p] = s
    dests = {p: output/'native'/p.name for p in changed}
    for p, dest in dests.items():
        if dest.exists() and dest.read_text() != changed[p]:
            raise FileExistsError('immutable native source exists: ' + str(dest))
    for p, dest in dests.items():
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not dest.exists():
            dest.write_text(changed[p])
    sources = [dests.get(p, p) for p in paths]
    for rel in DRAIN:
        p = ROOT/rel
        if not p.is_file():
            raise FileNotFoundError(p)
        if p not in sources:
            sources.append(p)
    result.update(sources=sources,
                  source_sha256={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
                  parameters=dict(result['parameters'], IDX_DRAIN_LOOKAHEAD=int(drain),
                                  S81_COMMAND_TRACE=int(trace), S81_TRACE_STAGE=-1 if stage is None else stage,
                                  S81_HOST_WORKSPACE=int(workspace)),
                  verilator_args=result['verilator_args'] + ['-GIDX_DRAIN_LOOKAHEAD='+str(int(drain)), '-GS81_COMMAND_TRACE='+str(int(trace)), '-GS81_TRACE_STAGE='+str(-1 if stage is None else stage), '-GS81_HOST_WORKSPACE='+str(int(workspace))],
                  capture_ready_not_inferred=True, parent_clock_loaded=False,
                  source_rebase='actual FASTPP PC21 L20; originals byte-identical')
    return result


OBSERVER = r'''
`ifndef SYNTHESIS
    generate if(S81_COMMAND_TRACE) begin:g_s81_trace
        integer launch_serial=0, command_ordinal=0;
        reg [46:0] trace_identity=0;
        initial if(!C8_CONTEXT || !C8_PUBLICATION || S81_TRACE_STAGE<0 || S81_TRACE_STAGE>=81)
            $fatal(1,"S81 trace requires actual source-root context/publication");
        always @(posedge clk) if(rst_n) begin
            if(c8_engine_start) begin
                launch_serial=launch_serial+1; command_ordinal=0;
                trace_identity=c8_engine_identity;
                $display("S81_LAUNCH stage=%0d rank=%0d launch=%0d identity=%0d entry=%0d token=%0d", S81_TRACE_STAGE,RANK,launch_serial,trace_identity,c8_engine_entry,c8_engine_token);
            end
            if(dut.cmd_go) begin
                if(launch_serial==0) $fatal(1,"collective without actual engine launch");
                $display("S81_COLLECTIVE stage=%0d rank=%0d launch=%0d identity=%0d ordinal=%0d pc=%0d op=%0d src=%0d dst=%0d n=%0d ibase=%0d k=%0d stride=%0d seq=%0d rnd=%0d", S81_TRACE_STAGE,RANK,launch_serial,trace_identity,command_ordinal,dbg_pc,dut.core_coll_op,dut.core_coll_src,dut.core_coll_dst,dut.core_coll_n,dut.core_coll_ibase,dut.core_coll_k,dut.core_coll_stride,dut.core_coll_seq,dut.core_coll_rnd);
                command_ordinal=command_ordinal+1;
            end
            if(c8_retire_v)
                $display("S81_RETIRE stage=%0d rank=%0d launch=%0d identity=%0d",S81_TRACE_STAGE,RANK,launch_serial,c8_retire_identity);
        end
    end endgenerate
`endif
'''

# Simulation input-loader ABI, not a native SRAM write port or visibility ACK.
# It must never set context_restored. The caller supplies actual producer bits;
# physical capture/debt qualification remains with the enclosing native service.
WORKSPACE = r'''
`ifndef SYNTHESIS
    export "DPI-C" function v41rt_c8_workspace_write;
    function int v41rt_c8_workspace_write(input longint unsigned identity,
                                         input int address, input int raw_bits);
        v41rt_c8_workspace_write=1;
        if(S81_HOST_WORKSPACE && C8_CONTEXT && C8_PUBLICATION && rst_n &&
           identity < (64'd1 << 47) && address>=0 && address<(1<<19) &&
           c8_context_v && !c8_context_restored && !c8_stage_active &&
           identity[46:0]==c8_context_identity && c8_write_quiet &&
           !c8_write_fault && !c8_write_quarantine && !c8_stage_quarantine &&
           !(|dut.u_tile.rom_we)) begin
            dut.u_tile.vm[address]=32'(raw_bits);
            v41rt_c8_workspace_write=(dut.u_tile.vm[address]===32'(raw_bits)) ? 0 : 2;
        end
    endfunction
`endif
'''


def main():
    import argparse
    import json
    from dsrom_c8_parent_binding import ParentBinding
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--owner',required=True)
    parser.add_argument('--selected',required=True)
    parser.add_argument('--model-pin',required=True)
    parser.add_argument('--interface-pin',required=True)
    parser.add_argument('--payload-interface',required=True)
    parser.add_argument('--original-export',required=True)
    parser.add_argument('--released-return-binding')
    parser.add_argument('--output',required=True)
    parser.add_argument('--stage',type=int)
    parser.add_argument('--drain',action='store_true')
    parser.add_argument('--head',action='store_true')
    parser.add_argument('--accepted-pop',action='store_true')
    parser.add_argument('--workspace',action='store_true')
    parser.add_argument('--trace',action='store_true')
    args=parser.parse_args()
    binding=ParentBinding(args.owner,args.selected,args.model_pin,args.interface_pin,
                          payload_interface=args.payload_interface, released_return_binding=args.released_return_binding)
    result=install(binding,args.original_export,args.output,drain=args.drain,
                   head=args.head,trace=args.trace,stage=args.stage,accepted_pop=args.accepted_pop,
                   workspace=args.workspace)
    result['allocation_receipts']=binding.receipts
    text=json.dumps(result,default=str,indent=2)+'\n'
    receipt=Path(args.output)/'sources.json'
    if receipt.exists() and receipt.read_text()!=text:
        raise FileExistsError('immutable source receipt exists')
    if not receipt.exists():receipt.write_text(text)
    print(receipt)


if __name__=='__main__':main()
