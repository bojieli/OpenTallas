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


def install_completion_join(selected, output):
    """Select Planck's native END join in this exact capture/WAVE parent.

    Complete-plan coverage and visibility remain required producer ports;
    selecting RTL never makes a source plan or a publication receipt true.
    """
    from dsrom_wavefront_native_result_read import install as install_read
    from dsrom_wfc_stage_completion_bind import install as install_join, JOIN
    parameters = selected.get('parameters', {})
    for name in ('PKG_WAVE', 'C8_CONTEXT', 'S81_CAPTURE'):
        if parameters.get(name) != 1:
            raise ValueError('native completion join requires ' + name + '=1')
    output = Path(output).resolve()
    sources = [Path(p).resolve() for p in selected['sources']]
    for p in sources:
        if hashlib.sha256(p.read_bytes()).hexdigest() != selected['source_sha256'].get(str(p)):
            raise ValueError('selected completion input changed: ' + str(p))
    # The native readout installer exports the genuine producer/END/data pins.
    # Its old host consumer may coexist, but never drives this RTL stage_done.
    if 'NATIVE_RESULT_READ' not in parameters:
        selected = install_read(selected, output/'readout', enable=False)
        sources = [Path(p).resolve() for p in selected['sources']]
    tops = [p for p in sources if p.name == 'ot_v41_rt_die_l20_c8.sv']
    if len(tops) != 1:
        raise ValueError('one selected completion parent required')
    original = tops[0]
    joined = install_join(original, output/'join')
    generated = Path(joined['generated']).resolve()
    sources = [generated if p == original else p for p in sources]
    leaf = (ROOT/JOIN).resolve()
    if leaf not in sources:
        sources.append(leaf)
    result = dict(selected)
    result.update(sources=sources,
                  source_sha256={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
                  parameters=dict(selected['parameters'], WFC_COMPLETION_JOIN=1),
                  verilator_args=[a for a in selected['verilator_args']
                                  if not a.startswith('-GWFC_COMPLETION_JOIN=')]
                                 + ['-GWFC_COMPLETION_JOIN=1'],
                  completion_join=joined,
                  wholeplan_coverage_authority_bound=False,
                  real_visibility_authorities_bound=False,
                  physical_admission=False, measured_system_result=False)
    return result


def install(binding, original_export, output, *, drain=False, head=False,
            actual_collectives=None, trace=False, stage=None, accepted_pop=False,
            workspace=False, capture=False, kvt_source_stride=False, capture_stream=False):
    """Return actual elaborator sources/parameters, with every flag default off.

    trace is simulation-only and records commands admitted at dut.cmd_go,
    source-root identity, PC, all command fields and monotonically increasing
    per-launch ordinal. Tag wrap is never used as a transaction identity.
    No synthetic execution calendar or physical load closure is manufactured.
    """
    if capture_stream and not capture:
        raise ValueError('indexed stream requires capture selection')
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
            s = _one(s, '\nendmodule', DRAIN_SELECTION_GUARD + OBSERVER + WORKSPACE + '\nendmodule')
        if kvt_source_stride:
            s = _one(s, '    parameter integer IDX_DRAIN_LOOKAHEAD=0,',
                     '    parameter integer SU_KVT_SOURCE_STRIDE=0,\n    parameter integer IDX_DRAIN_LOOKAHEAD=0,')
            if role == 'core':
                s = _one(s, 'ot_hdc_v41x_su_adapt #(',
                         'ot_hdc_v41x_su_adapt #(.KVT_SOURCE_STRIDE(SU_KVT_SOURCE_STRIDE),')
            else:
                module = {'tile':'ot_hdc_core_v41x', 'die':'ot_chip_v41x_tile',
                          'top':'ot_chip_v41x_die_owner_safe_c8'}[role]
                s = _one(s, module+' #(', module+' #(.SU_KVT_SOURCE_STRIDE(SU_KVT_SOURCE_STRIDE),')
        if capture:
            from dsrom_s81_capture_parent import hook
            s=hook(role,s,stream=capture_stream)
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
    if kvt_source_stride:
        sources = _select_kvt_stride_sources(sources)
    if capture:
        from dsrom_s81_capture_parent import dependencies
        sources=dependencies(sources,output/'capture',stream=capture_stream)
    for rel in DRAIN:
        p = ROOT/rel
        if not p.is_file():
            raise FileNotFoundError(p)
        if p not in sources:
            sources.append(p)
    # Enabling the control candidate must elaborate the actual pooled ring
    # reader. Top defaults X_IDX=0/IDX_RING=0 would otherwise omit it entirely.
    drain_parameters = dict(X_IDX=2, IDX_RING=1) if drain else {}
    drain_args = ['-GX_IDX=2', '-GIDX_RING=1'] if drain else []
    result.update(sources=sources,
                  source_sha256={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
                  parameters=dict(result['parameters'], IDX_DRAIN_LOOKAHEAD=int(drain),
                                  S81_COMMAND_TRACE=int(trace), S81_TRACE_STAGE=-1 if stage is None else stage,
                                  S81_HOST_WORKSPACE=int(workspace), **drain_parameters),
                  verilator_args=result['verilator_args'] + drain_args + ['-GIDX_DRAIN_LOOKAHEAD='+str(int(drain)), '-GS81_COMMAND_TRACE='+str(int(trace)), '-GS81_TRACE_STAGE='+str(-1 if stage is None else stage), '-GS81_HOST_WORKSPACE='+str(int(workspace))],
                  capture_ready_not_inferred=True, parent_clock_loaded=False,
                  source_rebase='actual FASTPP PC21 L20; originals byte-identical')
    if capture:
        result['parameters']['S81_CAPTURE']=1
        result['verilator_args'].extend(['-GS81_CAPTURE=1','-I'+str(ROOT/'rtl/hdc/v41')])
        result['capture_added_idle_edges_per_executed_phase']=2
        result['physical_admission']=False
    if capture_stream:
        result['parameters']['S81_CAPTURE_STREAM']=1
        result['verilator_args'].append('-GS81_CAPTURE_STREAM=1')
        result['capture_stream_model']='results/uarch/dsrom_s81_adjacent_stream_price_20261005/model.json'
        result['capture_stream_remote_terminal_required']=True
        result['physical_admission']=False
    if kvt_source_stride:
        result['parameters']['SU_KVT_SOURCE_STRIDE']=1
        result['verilator_args'].append('-GSU_KVT_SOURCE_STRIDE=1')
        result['kvt_source_stride']={'128':11,'512':13}
        result['physical_admission']=False
    return result


def _select_kvt_stride_sources(sources):
    replacements={}
    for name in ('ot_hdc_v41x_su_adapt.sv','ot_hdc_v41x_vec.sv','ot_hdc_v41x_vec_lane.sv'):
        matches=[p for p in sources if p.name==name]
        if len(matches)!=1:
            raise ValueError('missing/duplicate actual KVT source: '+name)
        original=ROOT/'rtl/hdc/v41x'/name
        selected=ROOT/'rtl/hdc/v41x/s81_kvt_stride'/name
        if matches[0].read_bytes()!=original.read_bytes():
            raise ValueError('selected KVT original source mismatch: '+name)
        if not selected.is_file():raise FileNotFoundError(selected)
        replacements[matches[0]]=selected
    return [replacements.get(p,p) for p in sources]


DRAIN_SELECTION_GUARD = r'''
    // Elaboration selection is part of the candidate's hardware contract.
    // An enabled flag on an absent reader must never count as integration.
    generate if(IDX_DRAIN_LOOKAHEAD && (X_IDX != 2 || IDX_RING != 1)) begin:g_drain_selection_invalid
        initial $fatal(1,"S81 drain lookahead requires X_IDX=2 and IDX_RING=1");
    end endgenerate
'''


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
    parser.add_argument('--capture',action='store_true')
    parser.add_argument('--source-kvt-stride',action='store_true')
    parser.add_argument('--completion-join',action='store_true',
                        help='select native RTL END completion; actual coverage/fence producer ports required')
    parser.add_argument('--baseline-config',type=Path,
                        help='consume Claude-owned baseline config for the selected layer parent')
    args=parser.parse_args()
    if args.completion_join and not args.baseline_config:
        raise ValueError('completion join requires the existing owner capture/WAVE baseline selection')
    binding=ParentBinding(args.owner,args.selected,args.model_pin,args.interface_pin,
                          payload_interface=args.payload_interface, released_return_binding=args.released_return_binding)
    baseline = None
    if args.baseline_config:
        baseline=json.loads(args.baseline_config.read_text())
        if baseline.get('schema')!='opentallas.dsrom-baseline-config.v1':
            raise ValueError('unsupported owner baseline config')
        selected=json.loads((ROOT/baseline['selection_successor']).read_text())
        p=selected['parameters']
        for key in ('S81_CAPTURE','S81_HOST_WORKSPACE','COLL_ACCEPTED_POP','PKG_WAVE'):
            if p.get(key)!=1:
                raise ValueError('owner baseline requires '+key+'=1')
        if args.head or args.drain:
            raise ValueError('baseline layer selection cannot add rejected head or unselected drain')
        if args.stage is not None and args.stage!=selected['snapshot_stage']:
            raise ValueError('baseline stage must match owner-selected phase/native binding')
        args.stage=selected['snapshot_stage']
        args.trace=bool(p['S81_COMMAND_TRACE'])
        args.accepted_pop=args.workspace=args.capture=args.source_kvt_stride=True
    result=install(binding,args.original_export,args.output,drain=args.drain,
                   head=args.head,trace=args.trace,stage=args.stage,accepted_pop=args.accepted_pop,
                   workspace=args.workspace,capture=args.capture,kvt_source_stride=args.source_kvt_stride)
    if baseline is not None:
        from dsrom_wavefront_install import install as install_wave
        result=install_wave(result,Path(args.output)/'wave',enable=True,win=p['PKG_WAVE_WIN'])
        # Consume the owner's remaining layer flags, without claiming its
        # separately listed pending bindings have been installed by this path.
        for flag in selected['verilator_args']:
            if flag.startswith('-G'):
                key,value=flag[2:].split('=',1)
                if key in result['parameters']:
                    if int(value)!=result['parameters'][key]:
                        raise ValueError('baseline flag conflicts with installed source: '+key)
                    continue
                result['parameters'][key]=int(value)
            if flag not in result['verilator_args']:
                result['verilator_args'].append(flag)
        result['baseline_config']=str(args.baseline_config.resolve())
        result['baseline_config_sha256']=hashlib.sha256(args.baseline_config.read_bytes()).hexdigest()
        result['baseline_pending_bindings']=selected['baseline']['not_in_this_die_yet']
    if args.completion_join:
        result=install_completion_join(result,Path(args.output)/'completion')
    result['allocation_receipts']=binding.receipts
    text=json.dumps(result,default=str,indent=2)+'\n'
    receipt=Path(args.output)/'sources.json'
    if receipt.exists() and receipt.read_text()!=text:
        raise FileExistsError('immutable source receipt exists')
    if not receipt.exists():receipt.write_text(text)
    print(receipt)


if __name__=='__main__':main()
