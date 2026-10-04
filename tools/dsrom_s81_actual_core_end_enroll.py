"""Enroll the real selected core END/head sources; never launch a full-core build.

This is source/model/build-plan preparation. Existing parameter switches leave
five arithmetic dependencies inside the core; a component archive is not claimed
until those existing engine interfaces are served and source-matched.
"""
from pathlib import Path
import argparse, ast, hashlib, json
import dsrom_s81_native_head_hook as hook
ROOT = Path(__file__).resolve().parents[1]
PARAMETERS = dict(FULL_SHAPE=1, INSTR_BITS=2048, AW=30, NW=21, PAW=14,
                  W=16, G=4, IL=8, BL=16, DIM=5120, TOPK=512, HDIM=512,
                  MP=1, NSLOT=1, X_ROM=1, OPT_NATIVE_HEAD=1,
                  S81_CAPTURE=1, ROM_R=128, ROM_PHW=10)
# Existing module interfaces. No replacement implementation or idle tie is emitted.
BLOCKS = [
    ('u_me', 'ot_hdc_v41_matvec', 'unconditional legacy ME engine0; X_ROM substitutes engine1 only',
     'e_go[0]', 'e_ready[0]', 'e_idle[0]', 'e_fault[0]'),
    ('u_qe', 'ot_hdc_v41_qe', 'unconditional QE, full NBMAX192/CHUNK8/BL16/IL8/MP1',
     'qe_go_e', 'qe_ready_e', 'qe_idle_e', 'qe_fault'),
    ('g_su_a.g_su.u_su', 'ot_hdc_v41_stream', 'X_SU0 still elaborates MP1 legacy SU',
     'su_go && (sp < su_m)', 'su_ready_v[sp]', 'su_idle_v[sp]', 'su_fault_v[sp]'),
    ('g_xu_a.u_xu', 'ot_hdc_v41_xu', 'X_SEL0/X_EG0 still elaborates legacy XU TOPK512',
     'xu_go', 'xu_ready', 'xu_idle', 'xu_fault'),
    ('g_he_x.u_he', 'ot_hdc_v41x_he_adapt', 'default X_HE1 still elaborates HE arithmetic; X_HE0 is another engine, not off',
     'he_go', 'he_ready', 'he_idle', 'he_fault'),
]

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def prepare(output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    hook.emit(output / 'native')
    original = hook.CORE.read_text()
    selected = (output / 'native' / hook.CORE.name).read_text()
    # The complete real FSM/decode/DYN region remains byte-identical.
    begin = '    // -- sequencer '
    end = '    // -- units '
    original_control = original[original.index(begin):original.index(end)]
    selected_control = selected[selected.index(begin):selected.index(end)]
    if original_control != selected_control:
        raise ValueError('original core FSM/decode/DYN changed')
    end_case = '''                                default: begin                                                       // END
                                    done <= 1'b1; next_token <= acc_any ? acc_bonus : am_idx;
                                    next_val <= am_val; st <= S_IDLE;
                                end'''
    if end_case not in selected or "wire waited = ((d_wait & ~(idles & ~gos)) == 5'd0);" not in selected:
        raise ValueError('real END/waited changed')
    # Exact partial-component pricing reuses the existing unified model. Never
    # claim an unpriced control split or double-charge the already selected body.
    # Load this exact pure model function without unrelated physical-record imports.
    parsed = ast.parse((ROOT/'tools/uarch_model.py').read_text())
    model_nodes = [n for n in parsed.body
                   if (isinstance(n, ast.FunctionDef) and n.name == 'dsrom_s81_head_result_hook')
                   or (isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'DFF_UM2' for t in n.targets))]
    if len(model_nodes) != 2:
        raise ValueError('unified head model/constant declaration changed')
    namespace = {}
    exec(compile(ast.Module(body=model_nodes, type_ignores=[]), 'tools/uarch_model.py', 'exec'), namespace)
    head_model = namespace['dsrom_s81_head_result_hook'](128)
    plan = dict(
        status='SOURCE_ENROLLED_MINIMUM_BUILD_BLOCKED_EXISTING_ENGINE_INTERFACES',
        actual_top='ot_hdc_core_v41x', parameters=PARAMETERS,
        no_build_launched=True, no_whole_array=True, field_instances=0,
        actual_control_sha256=hashlib.sha256(original_control.encode()).hexdigest(),
        literal_pcs='HeadSourceBinding.compile/emit caller pc_base+5 and pc_base+6; producer IDs4892/4893 are not PCs',
        accepted_context='caller accepted owner2147483648/sequence1/position1048575 only; never synthesized by enrollment',
        real_END='S_ISSUE, d_unit0, d_ctl0, waited -> registered done/next_token/next_val',
        waited='(d_wait & ~(idles & ~gos)) == 0; no idle tie while accepted callback debt exists',
        real_head='existing headhook EAM1/head_final_valid/data512/identity47; real busy/forwarded/final_ready',
        result_reader='existing native-result export/WaveNativeResultRead; producer_take/end_take/am_any/done remain actual source observations; C8 retire belongs enclosing caller',
        engine_dependencies=[dict(block=b, module=m, reason=r, go=g, ready=rd, idle=i, fault=f)
                             for b,m,r,g,rd,i,f in BLOCKS],
        smallest_next_step='Separate ONLY the listed engine module bodies at their unchanged existing instance interfaces, serving real accepted command/operand/output/ready/idle/fault edges. Keep core FSM/DYN/decoder and ROM/head native bodies. No interface implementation is fabricated here.',
        prohibited='No blackbox idle1, false ready/forwarded, fake Top, host done/C8-retire, reduced dimensions or automatic fullcore make.',
        archive_reuse=dict(
            SELECT='/tmp/dsrom-s81-native-aux2048-sagan-r1/selector/obj/VDsromS81Aux2048__ALL.a',
            TOP='/tmp/dsrom-s81-native-top2048-b97db7ec1-r1/obj/libVDsromTop2048.a',
            argmax_object='/tmp/s81_native_head_argmax.o',
            actual_core_header=None, actual_core_archive=None,
            historical_core_guard='different tb/fullSUN256-QE wrapper/source; cannot enroll as current OPT_NATIVE_HEAD1 core'),
        new_ports=0, new_queues=0, new_protocols=0,
        build_command=None,
        header_after_qualified_component_build='obj/Vot_hdc_core_v41x.h',
        archive_after_qualified_component_build='obj/Vot_hdc_core_v41x__ALL.a',
        future_build_policy='Before generation verify exact serviced engine interfaces and current source hashes; use measured host CPU/RAM/disk admission, no guessed wall/file caps; never submit an unbounded fullcore fallback',
    )
    boundaries = dict(program=dict(request=15, response=2048, response_bytes=256),
        start=dict(control=1, token=21, position=21, entry=14),
        return_field_bits=8832, root_rows_bits=2432, owner_bits=47, vm_accept_bits=128,
        head_final_bits=512+47+1, head_final_ready_bits=1,
        result=dict(done=1, token=21, value=32, fault=1))
    model = dict(status='COMPONENT_SOURCE_SIZING_ONLY_NOT_HARDWARE_OR_RUNTIME_QUALIFICATION',
        native_head_existing_model=head_model, boundaries=boundaries,
        MACs_per_cycle_new=0, arithmetic_replicas_new=0, mux_demux_added=0,
        replicas=4, FF_added_by_enrollment=0, area_added_by_enrollment_mm2=0,
        retained_control_storage=dict(instruction_register=2048, dyn64_AW30=1920, pc=14,
            scope='named retained arrays only, not complete mapped control area'),
        ports_bytes_per_native_edge=dict(program_response=256, field_response=1104, VM_logit_max=512),
        tracks_required=dict(field_return=8832, root_rows=2432, final_packet=560),
        available_routing_tracks=None, floorplan_slot_fit=None,
        control_split_area_mm2=None, control_split_ports_bits=None,
        source_END_latency='On first S_ISSUE edge with actual waited true; synchronous fetch FSM retained; final handoff/consumer/CDC costs remain existing caller obligations, not zero',
        instruction_fetch_edges=['S_FETCH requests', 'S_WAIT', 'S_CAP captures', 'S_DEC admits', 'S_ISSUE accepts'],
        composed_token_latency_delta_from_copy=0,
        measured_frequency=None, SS_FF=False,
        no_new_phy_or_provider=True)
    deps = [hook.CORE, hook.ADAPT, ROOT/'tools/dsrom_s81_native_head_hook.py',
            ROOT/'tools/dsrom_s81_native_head_join.py', ROOT/'tools/dsrom_wavefront_native_result_read.py',
            ROOT/'tools/dsrom_s81_head_source_binding.py', ROOT/'tools/uarch_model.py',
            ROOT/'rtl/rom/collectives/ot_rom_coll_pkg.sv',
            ROOT/'rtl/dsrom_sys/s81_native_head/ot_dsrom_s81_head_amax.sv',
            ROOT/'rtl/dsrom_sys/s81_native_head/ot_rom_argmax_rows.sv']
    record=dict(plan=plan, model=model,
                source_sha256={str(p.relative_to(ROOT)):sha(p) for p in deps},
                emitted_sha256={str(p.relative_to(output)):sha(p) for p in (output/'native').glob('*.sv')})
    (output/'enrollment.json').write_text(json.dumps(record,indent=2)+'\n')
    return record

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare',required=True,type=Path)
    args=parser.parse_args()
    result=prepare(args.prepare)
    print(result['plan']['status'])
