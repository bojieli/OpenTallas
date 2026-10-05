#!/usr/bin/env python3
"""One source-pinned V4.1 QE tile: FP8 and paired-FP4 checkpoint bank images.

This is a representative local owner and readback witness, not a full-die
placement. Macro words are 274 bits; each file row is 35 little-endian bytes
with unused high bits zero. ECC generation and macro-Q timing remain open.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools import v41_fullshape_qe_stream_image as Q
SCHEMA = "opentallas.v41x.qe_local_tile_bank.v1"
MACROS = 16
DEPTH = 8192
WORD_BITS = 274
FILE_BYTES = 35
TILE = "die0.layer0.rank0.tile0.qe"
MATRICES = ("wq_a", "exp110.w1")


def digest(path: Path) -> str:
    return Q.digest(path)


def _fixed_geometry(name: str, nrows: int, nb: int) -> tuple[int, int]:
    expected = {"wq_a": (320, 160), "exp110.w1": (576, 160)}[name]
    if (nrows, nb) != expected:
        raise ValueError(f"unexpected shipped rank0 L0 {name} shape")
    if nb % 8:
        raise ValueError("qtile K blocks must fit complete eight-lane beats")
    return nb // 8, nrows * (nb // 8)


def local_slot(name: str, row: int, block: int) -> dict:
    """One checkpoint 32-column block -> macro, row, pair half/lane.

    qtile G=1, plg=0: beat=row*nbeat+block//8. This differs deliberately
    from the executable core's 16-row qrom word address.
    """
    nrows, nb = {"wq_a": (320, 160), "exp110.w1": (576, 160)}[name]
    if not (0 <= row < nrows and 0 <= block < nb):
        raise ValueError("checkpoint block outside selected matrix")
    beat = row * (nb // 8) + block // 8
    lane = block % 8
    if name == "wq_a":
        macro = lane
        macro_row = beat
        half = 0
    else:
        macro = 8 + (beat & 1) * 4 + lane // 2
        macro_row = beat // 2
        half = lane & 1
    if macro_row >= DEPTH:
        raise ValueError("macro depth overflow")
    return dict(tile=TILE, physical_id=f"{TILE}.rom{macro:02d}",
                cluster=TILE, macro_id=macro, macro_row=macro_row,
                read_port=0, qtile_beat=beat, chain_position=lane,
                half_lane=half)


def skew_port_witness(name: str) -> dict:
    """Replay qtile's eight staggered chain-position requests, one bank port.

    The RTL uses SK(c)=0 for c<2, else 3*(c-1). A bank may answer two
    lanes only when both request the *same* physical macro row that cycle.
    """
    nrows = 320 if name == "wq_a" else 576
    beats = nrows * 20
    skew = [0 if c < 2 else 3 * (c - 1) for c in range(8)]
    conflicts = 0
    same_row_shares = 0
    max_distinct = 0
    max_active_ports = 0
    read_transactions = 0
    issued = 0
    for cycle in range(beats + max(skew)):
        bank_rows: dict[int, set[int]] = {}
        bank_accesses: dict[int, int] = {}
        for c in range(8):
            beat = cycle - skew[c]
            if not 0 <= beat < beats:
                continue
            row, q = divmod(beat, 20)
            loc = local_slot(name, row, q * 8 + c)
            bank_rows.setdefault(loc["macro_id"], set()).add(loc["macro_row"])
            bank_accesses[loc["macro_id"]] = bank_accesses.get(loc["macro_id"], 0) + 1
            issued += 1
        conflicts += sum(len(rows) > 1 for rows in bank_rows.values())
        same_row_shares += sum(n - 1 for n in bank_accesses.values() if n > 1)
        read_transactions += len(bank_rows)
        max_active_ports = max(max_active_ports,len(bank_rows))
        max_distinct = max(max_distinct, max((len(rows) for rows in bank_rows.values()),default=0))
    if conflicts:
        raise AssertionError(f"{name} single-read macro port conflicts: {conflicts}")
    return dict(chain_skew_cycles=skew, qtile_beats=beats, lane_requests=issued,
                macro_row_conflicts=conflicts, same_row_shared_lane_requests=same_row_shares,
                macro_read_transactions=read_transactions,
                physical_bytes_read=read_transactions*WORD_BITS//8,
                ideal_synchronous_macro_reads=beats*(8 if name=="wq_a" else 4),
                max_active_macro_ports=max_active_ports,
                max_distinct_macro_rows_per_cycle=max_distinct,
                scope="one descriptor, no overlapping second descriptor")


def pack_tile(source_manifest: Path, source_dir: Path, output_dir: Path) -> dict:
    src = json.loads(source_manifest.read_text())
    if (src.get("layer"), src.get("rank"), src.get("tp")) != (0, 0, 4):
        raise ValueError("local tile witness requires TP4 L0 rank0")
    source = {}
    for name in MATRICES:
        source[name] = Q.source_matrix(src, source_dir, name)
    w_codes, w_scale, w_fp4 = source["wq_a"]
    e_codes, e_scale, e_fp4 = source["exp110.w1"]
    if w_fp4 or not e_fp4:
        raise AssertionError("format mismatch")
    wnbeat, wbeats = _fixed_geometry("wq_a", w_codes.shape[0], w_codes.shape[1] // 32)
    enbeat, ebeats = _fixed_geometry("exp110.w1", e_codes.shape[0], e_codes.shape[1] // 16)
    if wbeats > DEPTH or (ebeats + 1) // 2 > DEPTH:
        raise ValueError("selected matrices exceed one local tile bank depth")
    image = np.zeros((MACROS, DEPTH, FILE_BYTES), np.uint8)
    # FP8: one {UE8M0 byte, 32 code bytes} lane per 274-bit macro read.
    w_blocks = w_codes.reshape(320, wnbeat, 8, 32).reshape(wbeats, 8, 32)
    w_scales = np.repeat(w_scale, 32, axis=0).reshape(320, wnbeat, 8).reshape(wbeats, 8)
    for lane in range(8):
        image[lane, :wbeats, :32] = w_blocks[:, lane]
        image[lane, :wbeats, 32] = w_scales[:, lane]
    # FP4: two {UE8M0 byte, 16 packed code bytes} lanes per 274-bit word.
    # The even/odd beat chooses one of two bank sets; each set has four ports.
    e_blocks = e_codes.reshape(576, enbeat, 8, 16).reshape(ebeats, 8, 16)
    e_scales = e_scale.reshape(576, enbeat, 8).reshape(ebeats, 8)
    e_lane = np.empty((ebeats, 8, 17), np.uint8)
    e_lane[:, :, :16] = e_blocks
    e_lane[:, :, 16] = e_scales
    for parity in range(2):
        for pair in range(4):
            image[8 + parity * 4 + pair, :ebeats // 2, :34] = (
                e_lane[parity::2, pair * 2:pair * 2 + 2].reshape(ebeats // 2, 34))
    verify_tile(image, source)
    output_dir.mkdir(parents=True, exist_ok=True)
    macro_rows = []
    for macro in range(MACROS):
        path = output_dir / f"{TILE.replace('.', '_')}_rom{macro:02d}.bin"
        path.write_bytes(image[macro].tobytes())
        valid_rows = wbeats if macro < 8 else ebeats // 2
        macro_rows.append(dict(physical_id=f"{TILE}.rom{macro:02d}", serves_clusters=[TILE],
                               macro_id=macro, read_ports=1, depth=DEPTH, word_bits=WORD_BITS,
                               payload_format="fp8_single" if macro < 8 else "fp4_paired",
                               valid_rows=valid_rows, padded_rows=DEPTH-valid_rows,
                               reserved_check_bits=10 if macro < 8 else 2,
                               image_file=path.name, image_sha256=digest(path),
                               image_file_bytes=path.stat().st_size))
    q_record_path = ROOT / "results/rtl/hdc_v41x_fullshape_qe_stream_200k_l0_rank0.json"
    q_record = json.loads(q_record_path.read_text())
    logical_hashes = {}
    for name in MATRICES:
        if name not in q_record["matrices"]:
            raise ValueError("logical stream manifest missing mapped matrix")
        codes, scales, fp4 = source[name]
        logical, _, _ = Q.pack_stream(codes, scales, fp4)
        actual_hash = hashlib.sha256(logical.tobytes()).hexdigest()
        if actual_hash != q_record["matrices"][name]["logical_stream_sha256"]:
            raise ValueError(f"logical stream hash mismatch: {name}")
        logical_hashes[name] = actual_hash
    port_witnesses = {name:skew_port_witness(name) for name in MATRICES}
    physical_read = sum(w["physical_bytes_read"] for w in port_witnesses.values())
    useful_source = int(w_codes.nbytes + w_scale.nbytes + e_codes.nbytes + e_scale.nbytes)
    out = dict(schema=SCHEMA, status="source_pinned_local_tile_roundtrip_pass",
               claim_boundary="two matrix/local tile witness only; no full-die fit, P&R, or rate",
               full_die_supported=False, layer=0, rank=0, tp=4, tile=TILE,
               source_manifest=str(source_manifest.relative_to(ROOT)),
               source_manifest_sha256=digest(source_manifest),
               logical_stream_manifest=str(q_record_path.relative_to(ROOT)),
               logical_stream_manifest_sha256=digest(q_record_path),
               logical_stream_hashes=logical_hashes,
               tool_sha256=digest(Path(__file__)),
               source_commit=src.get("source_commit"), checkpoint=src.get("checkpoint"),
               macro_type="ot_rom_8192x274_m8", macro_bits=WORD_BITS,
               macro_depth=DEPTH, macros=macro_rows, matrices={
                   "wq_a": dict(format="FP8_E4M3", logical_base_word=q_record["matrices"]["wq_a"]["base_word"],
                                logical_word_count=q_record["matrices"]["wq_a"]["word_count"],
                                qtile_beats=wbeats, first_beat=0, last_beat=wbeats-1,
                                macro_ids=list(range(8)), macro_row_formula="row*20+block//8",
                                macro_formula="block%8", half_lane=0,
                                initiation_interval_assumed=1, initiation_interval_measured=None,
                                sustained_service_record=None),
                   "exp110.w1": dict(format="FP4_E2M1", logical_base_word=q_record["matrices"]["exp110.w1"]["base_word"],
                                     logical_word_count=q_record["matrices"]["exp110.w1"]["word_count"],
                                     expert_id=110, expert_id_base=q_record["matrices"]["exp110.w1"]["expert_id_base"],
                                     expert_stride_words=q_record["matrices"]["exp110.w1"]["expert_stride_words"],
                                     qtile_beats=ebeats, first_beat=0, last_beat=ebeats-1,
                                     macro_ids=list(range(8, 16)),
                                     macro_row_formula="(row*20+block//8)//2",
                                     macro_formula="8+((row*20+block//8)%2)*4+(block%8)//2",
                                     half_lane_formula="block%2", initiation_interval_assumed=1,
                                     initiation_interval_measured=None, sustained_service_record=None)},
               word_mapping="local_slot(name,row,block); qtile G=1 plg=0, 8 K blocks/beat",
               logical_core_roundtrip="every checkpoint code/scale reconstructed then qrom image byte-equal",
               local_tile_image_supported=True, qtile_rtl_replay_supported=False,
               qtile_address_translation_required="qtile sequential beat -> macro row; FP4 uses beat parity bank set",
               qtile_fp4_pair_expander_required=True,
               physical_macro_words_allocated=MACROS*DEPTH,
               physical_macro_bits_allocated=MACROS*DEPTH*WORD_BITS,
               physical_macro_bytes_allocated=MACROS*DEPTH*WORD_BITS//8,
               physical_file_bytes=MACROS*DEPTH*FILE_BYTES,
               valid_macro_words=8*wbeats+8*(ebeats//2),
               padded_macro_words=8*(DEPTH-wbeats)+8*(DEPTH-ebeats//2),
               physical_bytes_read_per_two_ops=physical_read,
               source_checkpoint_bytes=useful_source,
               required_simultaneous_ports=dict(fp8=8,fp4=7),
               qtile_skew_port_witnesses=port_witnesses,
               local_bank_set_mux_required=True,
               ecc_generated=False, macro_q_to_lane_timing_closed=False,
               unsupported_full_die_reasons=["only wq_a and exp110.w1 mapped", "qtile bank-address and paired-FP4 expander RTL absent",
                                             "no all-384-expert bank binpack",
                                             "no connected activation/result network or finite-resource schedule",
                                             "no macro ECC image or routed 274-bit bank-set mux"])
    return out


def verify_tile(image: np.ndarray, source: dict) -> None:
    if image.shape != (MACROS, DEPTH, FILE_BYTES):
        raise AssertionError("macro image geometry")
    if np.any(image[:, :, 34] != 0):
        raise AssertionError("nonzero unused high image bits")
    w_codes, w_scale, _ = source["wq_a"]
    e_codes, e_scale, _ = source["exp110.w1"]
    wnbeat, wbeats = _fixed_geometry("wq_a", 320, 160)
    enbeat, ebeats = _fixed_geometry("exp110.w1", 576, 160)
    w_lanes = np.stack([image[l, :wbeats, :33] for l in range(8)], axis=1)
    w_restore = w_lanes[:, :, :32].reshape(320, wnbeat, 8, 32).reshape(w_codes.shape)
    w_scale_rows = w_lanes[:, :, 32].reshape(320,160)
    if not np.array_equal(w_restore, w_codes) or not np.array_equal(w_scale_rows, np.repeat(w_scale,32,axis=0)):
        raise AssertionError("FP8 local tile readback mismatch")
    if np.any(image[:8, wbeats:]) or np.any(image[:8, :wbeats, 33:]):
        raise AssertionError("FP8 bank padding or check bits nonzero")
    e_lane = np.empty((ebeats, 8, 17), np.uint8)
    for parity in range(2):
        for pair in range(4):
            e_lane[parity::2,pair*2:pair*2+2] = image[8+parity*4+pair,:ebeats//2,:34].reshape(ebeats//2,2,17)
    e_restore = e_lane[:,:,:16].reshape(576,enbeat,8,16).reshape(e_codes.shape)
    e_scale_restore = e_lane[:,:,16].reshape(e_scale.shape)
    if not np.array_equal(e_restore,e_codes) or not np.array_equal(e_scale_restore,e_scale):
        raise AssertionError("FP4 paired local tile readback mismatch")
    if np.any(image[8:,ebeats//2:]):
        raise AssertionError("FP4 bank padding nonzero")
    for name, codes, scales, fp4 in (("wq_a",w_restore,w_scale,False),
                                     ("exp110.w1",e_restore,e_scale_restore,True)):
        expected, _, _ = Q.pack_stream(source[name][0],source[name][1],fp4)
        actual, _, _ = Q.pack_stream(codes,scales,fp4)
        if not np.array_equal(expected,actual):
            raise AssertionError(f"{name} qrom/core stream roundtrip mismatch")


def main() -> None:
    p=argparse.ArgumentParser()
    p.add_argument("--source-manifest",type=Path,default=ROOT/"results/rtl/hdc_v41x_fullshape_200k_l0_rank0_image.json")
    p.add_argument("--source-dir",type=Path,default=Path("/tmp/codex_v41_fullshape_golden/images/ctx200000_L00_r0"))
    p.add_argument("--output-dir",type=Path,required=True)
    p.add_argument("--record",type=Path,required=True)
    a=p.parse_args()
    result=pack_tile(a.source_manifest,a.source_dir,a.output_dir)
    a.record.parent.mkdir(parents=True,exist_ok=True)
    a.record.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({k:result[k] for k in ("status","physical_macro_bytes_allocated","physical_bytes_read_per_two_ops","full_die_supported")}))


if __name__=="__main__":
    main()
