"""Selected DS L0 scalar/broadcast lowering; never supplies runtime data.

The emitted programme is a candidate until its VM-to-RF bridge is bound and
qualified. Input VM data are owned by prior producers; fixture O is check-only.
No internal rr_w* replay is a connected producer.
"""
from __future__ import annotations

from hbm_layer_vehicle import layer_images as LI
from hbm_layer_vehicle.native_profile import NativeTiming


def _fields():
    from su_arith_generate import FIELDS
    widths = dict(FIELDS)
    offsets = {}
    pos = 0
    for name, width in reversed(FIELDS):
        offsets[name] = pos
        pos += width
    def get(word, name):
        return (word >> offsets[name]) & ((1 << widths[name]) - 1)
    def put(word, name, value):
        if not 0 <= value < 1 << widths[name]:
            raise ValueError((name, value))
        mask = ((1 << widths[name]) - 1) << offsets[name]
        return (word & ~mask) | (value << offsets[name])
    return get, put


def lower_broadcast(raw, *, q, timing, rf_address, scalar_ready, rf_local,
                    place=None, data=None, tag=""):
    """Compile VM scalar B -> RF class1 -> SU, with explicit ingress obligation.

    scalar_ready is the serial edge at which the real bridge presents rr_wv;
    qcore_r5 captures its input at +1 and commits at +2. Read starts at +3
    to avoid OLD-read overlap. rf_local is the actual selected slice parameter.
    Nonuniform strides remain refused; no lane arithmetic is emulated here.
    """
    import su_program_inventory as I
    if not isinstance(timing, NativeTiming):
        raise TypeError("explicit selected NativeTiming required")
    if not 0 <= rf_address < 256 or rf_local not in (0, 1) or scalar_ready < 0:
        raise ValueError("invalid RF slot/age")
    _, unit, sut, desc = I.decode(raw)
    b = desc.get("B")
    if unit != 2 or b is None or not b.ibcast or b.indexed or b.space != "VM":
        return dict(status="unlowered", reasons=["requires uniform VM B broadcast"])
    if b.m != 1 or sut["red"]:
        return dict(status="unlowered", reasons=["outer-varying broadcast/reducer calendar"])
    # The existing compiler emits A/C/D fills, arithmetic and O drains, while
    # refusing B's repeated non-sector addresses. Replace only that refusal.
    res = LI.su_record(raw, q=q, place=place, data=data, tag=tag, timing=timing)
    allowed = lambda reason: (reason.startswith("operand B group ") or
                              reason == "operand B broadcast/strided: needs RF-broadcast (srcs) calendar")
    remaining = [r for r in res.get("reasons", []) if not allowed(r)]
    if remaining or "ql" not in res:
        return dict(status="unlowered", reasons=remaining or res.get("reasons", []))
    get, put = _fields()
    old = res["ql"]
    # Start after real RF capture/commit, and leave room for the leading read.
    shift = max(0, scalar_ready + 4 + rf_local - res["setup_edge"])
    ql = LI.QLine()
    for field, commands in old.f.items():
        ql.f[field] = {edge + shift: value for edge, value in commands.items()}
    for edge, word in list(ql.f["control"].items()):
        terms = get(word, "ld_c") & ~(((1 << 240) - 1) << 240)
        vb = (get(word, "vb") & ~(((1 << 24) - 1) << 24)) | (rf_address << 24)
        srcs = (get(word, "srcs") & ~(3 << 2)) | (1 << 2)
        ql.f["control"][edge] = put(put(put(word, "ld_c", terms), "vb", vb), "srcs", srcs)
    first = res["setup_edge"] + shift
    end = max(res["issue_edges"]) + shift + LI.FIRST_OUT
    # Match whole-top production compiler: RF class held across operation.
    for edge in range(first - 1 - rf_local, end + 1):
        ql.put("rf", edge, 9, 9, 256 | rf_address)
    # Backend controls remain live through arithmetic and drain; reserve them
    # exclusively, including zero-valued cycles (never OR another record).
    hold = ql.f["control"][first]
    hold = put(put(hold, "ld", 0), "emit", 0)
    last = res["last_commit"] + shift + 1
    for edge in range(first, last + 1):
        ql.f["control"].setdefault(edge, hold)
    # OLD-read correction: output DRAIN must follow lane SRAM write.
    ql.f["vmw"] = {e + 1: v for e, v in ql.f["vmw"].items()}
    expect = [dict(x, edge=x["edge"] + shift + 1) for x in res["expect"]]
    return dict(status="candidate_requires_binding", reasons=[], ql=ql,
                lines=ql.lines(), preload=res["preload"], expect=expect,
                commands=[dict(kind="vm_scalar_to_rf", source_word=b.base,
                               rf_address=rf_address, rr_wa=rf_address >> 3,
                               select_word=b.base & 7, quarter=q,
                               capture_serial_edge=scalar_ready,
                               producer="runtime VM read; no injected scalar")],
                vm_reads=[(s, e + shift) for s, e in res["fills"]] + [(b.base >> 3, None)],
                vm_writes=[(s, e + shift + 1) for s, e in res["drains"]],
                issue_edges=[e + shift for e in res["issue_edges"]],
                reservations=[dict(resource="SU_control", first=first, last=last),
                              dict(resource="RF_sector", address=rf_address >> 3,
                                   first=scalar_ready, last=last)],
                last_commit=last, inputs_placeholder=res["inputs_placeholder"],
                qualifies_native_layer=False, qualifies_native_chain=False,
                binding_obligations=["VM scalar producer -> RF ingress with reserved rr arbitration",
                                     "real scalar readiness and actual RF_LOCAL parameter",
                                     "native arithmetic/VM numerical witness"])


def runtime_gather(raw, *, timing):
    """Describe a runtime index read followed by A[base + I*dyn_mul].

    No index value or fixture-resolved A address is accepted by this API.
    The actual indexed descriptor, not captured fixture desc, is authoritative.
    """
    import su_program_inventory as I
    _, unit, sut, desc = I.decode(raw)
    a, index, out = (desc.get(k) for k in ("A", "I", "O"))
    if (unit != 2 or a is None or index is None or out is None or not a.indexed
            or any(x.space != "VM" for x in (a, index, out))):
        return dict(status="unlowered", reasons=["requires VM indexed scalar A/I/O"])
    if a.n != 1 or a.m != 1 or index.n != 1 or out.n != 1:
        return dict(status="unlowered", reasons=["only selected scalar gather interface implemented"])
    if not isinstance(timing, NativeTiming):
        raise TypeError("explicit selected NativeTiming required")
    return dict(status="candidate_requires_binding", commands=[
        dict(kind="runtime_indexed_scalar", index_word=index.base, source_base=a.base,
             index_multiplier=a.dyn_mul, destination_word=out.base,
             index_source="live IDX.TOPK VM write", output_source="live runtime VM read")],
        events=[], reservations=[dict(resource="VM_runtime_scalar", exclusive=True)],
        address_expression="source_base + U32(VM[index_word]) * index_multiplier",
        reasons=[], binding_obligations=["runtime VM scalar engine instantiated on selected VM calendar ports",
                                        "IDX.TOPK commit -> index read dependency",
                                        "masked output write with actual fixed return ages"],
        qualifies_native_layer=False, qualifies_native_chain=False)


GQ_LOCAL_DEFINE = "OT_COLL_GQ_LOCAL_READ"
GQ_LOCAL_ORIGINAL_SHA256 = {
    "ot_hgi_coll_gq.sv": "d4990b482a26674449f61722eb44c246bce525c41d7682704e7d94bd5abcd0fa",
    "ot_hgi_coll_ring_ag.sv": "a8f396ed04718a29a73d222d73c66c3f9b495a171066590dd2507e5bf7d44516",
}


def gq_local_program(*, source_sector, t_start, period, vm_rt,
                     state_read_isa_row, row_to_isa, rf_sector):
    """Actual F20 descriptor +1536-bit ISA rows for the source candidate.

    row_to_isa is REQUIRED: caller must use its source-pinned issuer age.
    Read/return ISA rows are two edges apart (GQ merge adds two to both).
    Caller chooses their absolute phase after the live VM->LOCAL capture and
    so the returned stream event occupies an allowed existing3:4 cxrc slot.
    No fixture value, peer traffic, internal RR stimulus or +0 arithmetic.
    """
    if not (0 <= source_sector < 65536 and 0 <= rf_sector < 32
            and 0 <= t_start < period < 65536 and vm_rt >= 0
            and row_to_isa >= 0 and state_read_isa_row >= 0):
        raise ValueError("invalid native source calendar")
    # period includes the fixed ND40+V drain and descriptor retirement.
    if period <= t_start + 42 + vm_rt:
        raise ValueError("period ends before local fetch retirement")
    payload = ((1 << 101) | (period << 85) | (8 << 69) |
               (source_sector << 37) | (1 << 19) | (t_start << 3))
    # Existing ring 1536-bit row field starts at630. LOCAL_TXread bit11;
    # rr_local bit54. Tag0 is legal because exactly one localF1 is in flight.
    rows = [dict(row=state_read_isa_row, word=(1 << 11) << 630),
            dict(row=state_read_isa_row + 2, word=(1 << 54) << 630)]
    halt = state_read_isa_row + 3
    if halt >= 256:
        raise ValueError("selected ROWS256 programme capacity")
    sparse = {row["row"]: row["word"] for row in rows}
    dense = []
    for pc in range(halt + 1):
        nxt = pc if pc == halt else pc + 1
        # Exact cfg37/ROWS256 metadata: next highbits51/54; target52/55.
        metadata = ((63 << 45) | (nxt & 63) | (((nxt >> 6) & 1) << 51) |
                    (((nxt >> 7) & 1) << 54) | ((pc & 63) << 6) |
                    (((pc >> 6) & 1) << 52) | (((pc >> 7) & 1) << 55))
        if pc == halt:
            metadata |= 1 << 44
        dense.append(dict(row=pc, word=sparse.get(pc, 0), metadata=metadata))
    return dict(status="source_candidate", defines=[GQ_LOCAL_DEFINE],
                source_changes=list(GQ_LOCAL_ORIGINAL_SHA256),
                gq_target=176, descriptor_row_bits=102,
                configuration_word=(0xc7a1 << 240) | payload,
                descriptor=dict(base=0, limit=1, loops=1),
                issuer_target=52, issuer_rows=rows, issuer_dense_rows=dense,
                issuer_descriptor=dict(base=0, limit=halt + 1, loops=1, rows_capacity=256),
                issuer_configuration="F20segments0..5:256b uop, segment6:metadata64/upper192zero; target leaves55edges after lastframe and ROWS256descriptor scan258edges before launch",
                isa_input_edges=[r["row"] + row_to_isa for r in rows],
                rf_registration=dict(red_sv=1, red_tag=(1 << 13) | (1 << 23) | (rf_sector << 18),
                                     reserve="cxrc carry epoch and returntag0 until capture"),
                reservations=[dict(resource="COLL_read", owner=3, sector=source_sector,
                                   bank=source_sector % 8, edge_from_fire=17),
                              dict(resource="ringA_LOCAL_tag0", exclusive=True),
                              dict(resource="cxrc_return_tag0", exclusive=True),
                              dict(resource="RF_sector", sector=rf_sector, exclusive=True)],
                binding_obligations=["match launch/fire/issuer source ages and cxrc legal phase",
                                     "actual VM read owner at bank after selected relay path",
                                     "source GQ+ringcontrol fingerprint rebind; no hardview alias"],
                qualifies_native_layer=False, qualifies_native_chain=False)


def stage_gq_local_sources(selected_bundle, overlay_dir):
    """Write only a NEW two-file overlay after exact original hash checks.

    The selected/live bundle is read-only. Caller clones its functional bundle
    and applies this overlay with the explicit opt-in define; immutable physical
    sources/views stay associated with their old fingerprint.
    """
    import hashlib
    from pathlib import Path
    selected_bundle, overlay_dir = Path(selected_bundle).resolve(), Path(overlay_dir).resolve()
    if selected_bundle == overlay_dir or selected_bundle in overlay_dir.parents:
        raise ValueError("overlay must be outside the selected immutable bundle")
    if overlay_dir.exists() and any(overlay_dir.iterdir()):
        raise ValueError("overlay destination must be new or empty")
    rel = Path("rtl/hbm_accel/generic/collective/p2p")
    canonical = Path(__file__).resolve().parents[2]
    manifest = {}
    pending = []
    for name, expected in GQ_LOCAL_ORIGINAL_SHA256.items():
        original = (selected_bundle / rel / name).read_bytes()
        if hashlib.sha256(original).hexdigest() != expected:
            raise ValueError("selected GQ/ring source differs: " + name)
        replacement = (canonical / rel / name).read_bytes()
        target = overlay_dir / rel / name
        pending.append((target, replacement))
        manifest[str(rel / name)] = dict(before=expected, after=hashlib.sha256(replacement).hexdigest())
    for target, replacement in pending:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(replacement)
    return dict(defines=[GQ_LOCAL_DEFINE], sources=manifest,
                status="unbound_functional_source_candidate", qualifies_native_layer=False,
                qualifies_native_chain=False)
