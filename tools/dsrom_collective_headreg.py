"""Default-off W15 collective head integration; no build, inference or gate launch."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
ENGINE = 'rtl/rom/ot_w15_rom_oneshot_px_headreg.sv'


def price_collectives(collectives, *, clock_hz=1.2e9, ranks=4, lanes=16, tagw=32):
    """Price actual command identities once, not each rank's copy of a command.

    The system owner supplies ordered, unique collective identities from its
    executable calendar or actual command trace. This adds one cycle to each
    selected command; it does not assume a constant collectives/layer count.
    """
    import uarch_model as U
    ids = list(collectives)
    if len(set(ids)) != len(ids):
        raise ValueError('duplicate collective identity (rank copies must be collapsed)')
    if clock_hz <= 0 or ranks < 2 or lanes < 1 or tagw < 1:
        raise ValueError('invalid collective geometry/clock')
    # W15 has two parity FIFOs per source. Capacity and credits do not grow.
    record_bits = 32 * lanes + 3 + tagw
    bits = 2 * ranks * (record_bits + 1)
    return dict(collective_ids=ids, added_cycles=len(ids),
                added_seconds=len(ids) / clock_hz, clock_hz=clock_hz,
                extra_state_bits_per_die=bits,
                cell_area_floor_mm2=bits * U.DFF_UM2 / 1e6,
                MACs_per_cycle=0, input_bytes_per_cycle=4 * lanes,
                head_read_bits_per_cycle=ranks * record_bits,
                cached_head_bits=2 * ranks * record_bits,
                external_boundary_added_bits=0, replicas_per_die=2*ranks,
                routing_tracks_added_external=0, fifo_capacity_change=0,
                II_change=0, clock_fit=False, routed_slot_fit=False,
                adopted=False, scope='Analytical startup cost; actual stalls/SSFF/route require system measurement')


def install(sources, output, *, enable=False):
    """Select the existing Archimedes C8 parent list, without editing its files.

    Pass ParentBinding.native_sources(...) verbatim. Returned sources preserve
    that list's order and replace only the C8 enclosing die and runtime wrapper.
    Elaborate the same ot_v41_rt_die_l20_c8 top; COLL_HEADREG defaults to zero.
    enable=True returns its opt-in parameter, never changes source defaults.
    """
    return _install_selected(sources, output, enable=enable,
                             parameter='COLL_HEADREG', child_parameter='REGISTER_HEAD',
                             module='ot_w15_rom_oneshot_die_px_headreg', engine_path=ENGINE,
                             validation='Qwen cached-head algorithm reused; DS parity integration and physical context pending')


def _install_selected(sources, output, *, enable, parameter, child_parameter,
                      module, engine_path, validation):
    """Shared immutable enclosing-source export, no simulation or RTL tuning."""
    paths = [Path(p).resolve() for p in sources]
    if len(paths) != len(set(paths)):
        raise ValueError('duplicate source path')
    output = Path(output).resolve()
    targets = ('ot_chip_v41x_die_owner_safe_c8.sv', 'ot_v41_rt_die_l20_c8.sv')
    selected = {}
    for name in targets:
        matches = [p for p in paths if p.name == name]
        if len(matches) != 1:
            raise ValueError('actual C8 enclosing source missing/ambiguous: ' + name)
        selected[name] = matches[0]
    data = {name: p.read_text() for name, p in selected.items()}
    def replace_once(s, old, new):
        if s.count(old) != 1:
            raise ValueError('source interface changed: ' + old)
        return s.replace(old, new, 1)
    for name in targets:
        header = f'    parameter integer {parameter}=0,'
        if header not in data[name]:
            data[name] = replace_once(data[name], '    parameter integer C8_PUBLICATION=0,',
                                      header+'\n    parameter integer C8_PUBLICATION=0,')
        elif data[name].count(header) != 1:
            raise ValueError('ambiguous collective parameter: '+name)
    die = targets[0]
    selected_engine = f'{module} #(.{child_parameter}({parameter}),'
    if selected_engine not in data[die]:
        data[die] = replace_once(data[die], 'ot_w15_rom_oneshot_die_px #(', selected_engine)
    elif data[die].count(selected_engine) != 1:
        raise ValueError('ambiguous selected collective instance')
    top = targets[1]
    selected_die = f'ot_chip_v41x_die_owner_safe_c8 #(.{parameter}({parameter}),'
    if selected_die not in data[top]:
        data[top] = replace_once(data[top], 'ot_chip_v41x_die_owner_safe_c8 #(', selected_die)
    elif data[top].count(selected_die) != 1:
        raise ValueError('ambiguous collective parameter propagation')
    # No partial export on a failed interface check. Refuse to mutate inputs.
    if any(output == p.parent or output in p.parents for p in paths):
        raise ValueError('output must be separate from input sources')
    engine = ROOT / engine_path
    # An upstream source installer may already carry the same successor from
    # another checkout. Reuse its exact bytes instead of defining it twice.
    engines = [p for p in paths if p.name == engine.name]
    if len(engines) > 1:
        raise ValueError('duplicate successor engine definitions')
    if engines and engines[0].read_bytes() != engine.read_bytes():
        raise ValueError('selected successor engine source changed')
    # Check every destination before writing either source: a second-file
    # conflict must not leave a misleading partially installed first file.
    for name, content in data.items():
        dest = output / name
        if dest.exists() and dest.read_text() != content:
            raise FileExistsError('immutable selected source exists: ' + str(dest))
    output.mkdir(parents=True, exist_ok=True)
    replacements = {}
    for name, content in data.items():
        dest = output / name
        if not dest.exists():
            with dest.open('x') as f:
                f.write(content)
        replacements[selected[name]] = dest
    result = [replacements.get(p, p) for p in paths]
    if not engines:
        result.append(engine)
    pins = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in result}
    return dict(top='ot_v41_rt_die_l20_c8', parameters={parameter: int(enable)},
                sources=result, source_sha256=pins,
                verilator_args=['-G'+parameter+'='+str(int(enable))],
                input_sha256={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
                validation=validation)


def install_s81_parent(binding, original_export, output, *, enable=False,
                       actual_collectives=None, clock_hz=1.2e9):
    """Join Archimedes's actual selected S81 ParentBinding source factory.

    Allocation, BF sites, active ragged pairs and RD64 remain binding-owned.
    Refuse an S82 placeholder; no shape substitution or private source list.
    The enclosing caller passes returned parameters to its existing elaborator.
    """
    if binding.stages != 81 or binding.inventory['TP'] != 4:
        raise ValueError('selected S81/TP4 owner allocation required')
    if binding.contract['return_contract']['RD'] != 64:
        raise ValueError('selected active-pair RD64 required')
    result = install(binding.native_sources(original_export), output, enable=enable)
    result['selected_stages'] = binding.stages
    result['pairs_per_rank_die'] = binding.pairs
    result['return_depth'] = 64
    result['collective_price'] = None if actual_collectives is None else price_collectives(
        actual_collectives, clock_hz=clock_hz)
    # Off selection has no latency/storage debit. The analytical price remains
    # visible separately if a calendar was supplied, but is not an adoption.
    result['added_cycles'] = (result['collective_price']['added_cycles']
                             if enable and result['collective_price'] is not None
                             else (None if enable else 0))
    return result
