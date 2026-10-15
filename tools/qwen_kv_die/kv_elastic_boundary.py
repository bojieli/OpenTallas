"""Source-bound inventory for the unadopted 0az KV/HBM boundary.

This module deliberately installs no ABI aliases or physical bindings. A source
component proof is insufficient to replace the current die's controller/CDC.
"""
from collections import Counter
import hashlib
import re

STATIC = "rtl/qwen_sys/static_kv_20261014/"
SOURCES = {
    "controller": (STATIC + "qkd_ctrl_pc_host_static.sv", "qkd_ctrl_pc_host_static"),
    "front": (STATIC + "qkd_kv_hbm_elastic_front.sv", "qkd_kv_hbm_elastic_front"),
    "return": (STATIC + "qkd_static_kv_return_slots.sv", "qkd_static_kv_return_slots"),
    "writer": ("rtl/physical/ot_qkd_kv_static_writer_native.sv", "qkd_kv_static_writer_native"),
    "nominal_calendar": (STATIC + "qkd_static_kv_return_calendar.sv", "qkd_static_kv_return_calendar"),
    "sequencer": ("rtl/physical/ot_qwen_kv_centre_slots.sv", "qkd_seq"),
    "program_loader": ("rtl/qwen_sys/host_20261013/qkd_host_program_loader.sv", "qkd_host_program_loader"),
    "host_root": ("rtl/qwen_sys/split_20261014/qkd_host_root_pt.sv", "qkd_host_root_pt"),
    "link": ("rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_dies.sv", "qkd_d2d_static"),
}

# These are source requirements, not implemented die nets. Keep every field
# separate so a future adapter cannot silently drop identity or reservation bits.
MISSING_PRODUCERS = {
    "controller_hbm_calendar": ["static_cmd_owner", "static_cmd", "reserved_rd",
        "reserved_static_col", "reserved_write_col", "static_epoch", "expected_raw_valid"],
    "controller_write_context": ["es_context", "es_expected_valid", "es_expected_identity",
        "es_expected_address", "es_expected_pc", "es_expected_stack"],
    "front_block_calendar": ["blk_go"],
    "link_control_image": ["cfg_tx_we", "cfg_rx_we", "cfg_addr", "cfg_data", "cal_start", "cal_seg"],
    "return_core_calendar": ["expected_put", "expected_sector", "expected_epoch", "expected_layer"],
    "writer_independent_expectation": ["compiled_identity", "compiled_generation"],
    "link_independent_expectation": ["kvn_compiled_identity", "kvn_compiled_generation"],
}
WRITER_LINK_MAP = {
    "word_valid": "kvn_word_valid", "word_tag": "kvn_word_tag", "word_data": "kvn_word_data",
    "word_identity": "kvn_word_identity", "word_generation": "kvn_word_generation",
    "compiled_word_slot": "kvn_word_slot", "compiled_word_index": "kvn_word_index",
}
OPEN_JOINS = [
    "Bind cfg_stack to the actual two-bit package stack strap; retain the physical PC strap and logical landing PC mapping.",
    "Compile actual per-PC RD/WR/refresh reservations and independent identity from the production programme; do not schedule from valid/ready.",
    "Export controller tag/class/command/write ingress occupancy idle. Current controller has completion outputs but no drain output; front idle alone cannot prove KV drained.",
    "Expose ring publication/consumption occupancy idle across its real clock domains; ring currently exports only data and two faults.",
    "Join front hold to an actual exceptional sequencer block pause; current qkd_seq has no hold input. Preserve block credit blk_freed at HBM reservation issuer.",
    "Distribute writer four 288-bit es lanes and identity/context by dest_stack/dest_pc; preserve the actual asynchronous write ingress and expected-address checks.",
    "Join controller completion_v/we to each HOST slice and typed completion_fault to root; reduce actual front/ring/writer/controller faults with domain-safe registered exports.",
    "Provide controller ELASTIC=1 RAW_WD=256 TQD=64 physical master/outline/pin grants; inherited qkd_ctrl_pc physical view is a different source/ABI.",
    "Assign front, held return ring and held writer homes and actual pins; prove every required parent net, reach, native clocks and reset/boot sequence before adoption.",
    "Price front first-sector +10..26 HBM edges and writer reset minimum 3 core edges in the actual production image; pin source and calendar hashes.",
]


def _source(root, path, module):
    text = (root / path).read_text()
    clean = re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.S)
    match = re.search(r"\bmodule\s+" + re.escape(module) + r"\b", clean)
    if not match:
        raise ValueError(f"missing actual module {module}: {path}")
    header = clean[match.end():].split(");", 1)[0]
    # ANSI declarations may pack several names after one direction/type/width.
    ports = []
    for decl in re.finditer(r"\b(input|output|inout)\s+(.*?)(?=\b(?:input|output|inout)\b|$)", header, re.S):
        direction, body = decl.groups()
        width = re.search(r"\[([^]]+)\]", body)
        body = re.sub(r"\[[^]]+\]", " ", body)
        body = re.sub(r"\b(?:wire|reg|logic|signed)\b", "", body)
        for name in body.replace(")", "").split(","):
            name = name.strip()
            if name:
                if not re.fullmatch(r"[A-Za-z_]\w*", name):
                    raise ValueError(f"unparsed ANSI port in {module}: {name!r}")
                ports.append(dict(name=name, direction=direction, range=width.group(1) if width else None))
    if not ports:
        raise ValueError(f"no actual ANSI ports: {module}")
    return dict(path=path, module=module,
        sha256=hashlib.sha256((root / path).read_bytes()).hexdigest(), ports=ports)


def inventory(root, model, bindings):
    """Report exact source ABIs and current selected die modules; never grants adoption."""
    sources = {name: _source(root, *spec) for name, spec in SOURCES.items()}
    counts = Counter(bindings.get(i.master, {}).get("module", i.master) for i in model["insts"])
    required = {sources[n]["module"]: (1 if n == "writer" else 128)
                for n in ("controller", "front", "return", "writer")}
    deficits = {name: dict(required=n, selected=counts[name]) for name, n in required.items() if counts[name] < n}
    return dict(schema="opentallas.qwen-kv-elastic-boundary.integration.v1",
        status="OPEN_UNADOPTED", adoption_allowed=False, holds="KEPT",
        sources=sources, selected_modules=dict(sorted(counts.items())), required_module_deficits=deficits,
        missing_production_producers=MISSING_PRODUCERS,
        available_writer_link_map=WRITER_LINK_MAP,
        program_loader_limit="Existing loader exports pr143, program_ready, fault, digest64, program_epoch16, authorized_footer_valid/footer64; no KV reservation or D2D calendar-image output. Native pr is a distinct program interface.",
        nominal_calendar_limit="Produces raw/nominal corrected slots from reservations; does not issue reservations or the elastic block/core programme.",
        required_parameters=dict(controller=dict(ELASTIC=1, RAW_WD=256, TQD=64),
                                 front=dict(NBLK=4, BLK=8, STRIDE=1), return_ring=dict(DEPTH=8)),
        open_joins=OPEN_JOINS,
        qualification="Source component proof only; current parent/pin/clock/boot/native audits remain required.")


def require_adoption(report):
    """Fail closed until the production adapter and its audits replace this inventory."""
    # An inventory is not a qualification certificate, even if a caller edits its flags.
    raise ValueError("0az boundary adoption held: actual production producers, parent/pins/clocks/boot audits remain open")
