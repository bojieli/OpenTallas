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
        data[name] = replace_once(data[name], '    parameter integer C8_PUBLICATION=0,',
                                  '    parameter integer COLL_HEADREG=0,\n    parameter integer C8_PUBLICATION=0,')
    die = targets[0]
    data[die] = replace_once(data[die], 'ot_w15_rom_oneshot_die_px #(',
                            'ot_w15_rom_oneshot_die_px_headreg #(.REGISTER_HEAD(COLL_HEADREG),')
    top = targets[1]
    data[top] = replace_once(data[top], 'ot_chip_v41x_die_owner_safe_c8 #(',
                            'ot_chip_v41x_die_owner_safe_c8 #(.COLL_HEADREG(COLL_HEADREG),')
    # No partial export on a failed interface check. Refuse to mutate inputs.
    if any(output == p.parent or output in p.parents for p in paths):
        raise ValueError('output must be separate from input sources')
    output.mkdir(parents=True, exist_ok=True)
    replacements = {}
    for name, content in data.items():
        dest = output / name
        if dest.exists() and dest.read_text() != content:
            raise FileExistsError('immutable selected source exists: ' + str(dest))
        if not dest.exists():
            with dest.open('x') as f:
                f.write(content)
        replacements[selected[name]] = dest
    engine = ROOT / ENGINE
    result = [replacements.get(p, p) for p in paths]
    if engine not in result:
        result.append(engine)
    pins = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in result}
    return dict(top='ot_v41_rt_die_l20_c8', parameters={'COLL_HEADREG': int(enable)},
                sources=result, source_sha256=pins,
                input_sha256={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
                validation='Qwen cached-head algorithm reused; DS parity integration and physical context pending')
