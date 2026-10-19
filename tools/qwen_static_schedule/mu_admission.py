"""Precompile repeatable INIT/inference/retirement epochs into an explicit list.

No context flag selects an instruction. Each scheduled admission plays an INIT
range, then complete inference units, then a normal retirement head. The inactive
interval contains no programme or link starts. The list repeats indefinitely.
Physical and full-token certificates remain separate, required bindings.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from . import mu_opcal as O
from .calendar import ScheduleError

MAGIC = 0x13A9
ROM_DEPTH = 4096
ROM_BANKS = 3
PERIOD_BITS = 23
ADDR_BITS = 14


def compile_expanded(cal, link_images, *, head_ref, context_binding, phases=2,
                     identity_bound=False, q_readiness_bound=False):
    """Compile one cyclic superframe, retaining the latency user's whole stream.

    ``context_binding`` distinguishes the logical MU selector from opaque wire
    beat0 and supplies its measured receive/validated-bank ages. Missing evidence
    is reported as BLOCKED, never converted into a production certificate.
    """
    if phases != 2:
        raise ScheduleError("this expanded ABI is sized/proved for two repeating phases")
    if context_binding.get("logical_beat") != 1 or context_binding.get("wire_beat") != 0:
        raise ScheduleError("MU logical selector1 must retain canonical opaque wire beat0")
    cal = dict(cal, schedule={int(u): seq for u, seq in cal["schedule"].items()},
               segs={int(seg): entries for seg, entries in cal["segs"].items()})
    H, T = cal["H"], cal["T"]
    period = phases * H
    if period >= 1 << PERIOD_BITS or T >= 1 << 22 or period % T:
        raise ScheduleError("expanded H/T exceeds its23/22-bit or periodicity ABI")
    units = {int(u): sorted((t % H, name, block) for name, t, block in seq)
             for u, seq in cal["schedule"].items()}
    heads = {u: [(t, b) for t, n, b in seq if n == "head"] for u, seq in units.items()}
    slots = [dict(id=i, source_user=0, source_head=t,
                  wire_arrive=t + head_ref + context_binding["arrive_offset"],
                  bank_load=t + head_ref + context_binding["arrive_offset"] + context_binding["bank_extra"])
             for i, (t, _) in enumerate(heads[0])]
    used, bounds = set(), {}
    for u in range(1, O.NU):
        for initial, _ in heads[u]:
            eligible = [s for s in slots if s["id"] not in used and 0 < s["bank_load"] < initial]
            if not eligible:
                continue
            slot = max(eligible, key=lambda s: s["bank_load"])
            used.add(slot["id"])
            retired, rb = heads[u][-1]
            end = H + retired + rb["length"]
            next_load = period + slot["bank_load"]
            if end >= next_load:
                raise ScheduleError(f"user{u}: no validated quiet interval before recurring reload")
            bounds[u] = dict(init=initial, retire=H + retired, retire_end=end,
                             load_slot=slot, next_load=next_load,
                             quiet_edges=next_load - end,
                             init_load_margin=initial-slot["bank_load"])
            break
        else:
            raise ScheduleError(f"user{u}: no distinct canonical MU slot before INIT")

    def active(t, u):
        return u == 0 or bounds[u]["init"] <= t <= bounds[u]["retire"]

    pb = O.playback(cal)
    image = O.initial_context_image(cal["segs"])
    # GI enables CTX_DW for OPSEG: seal must carry a valid empty record.
    # Actual filler admission remains in explicit runtime context slots.
    image["dw"] = O.with_ctx(image["dw"], {}, mask=set())
    image["boot_context"] = dict(tag=O.CTX_TAG, mask=0, users=[], admission="runtime_slots")
    initial = image["initial_range"]
    leaf = []
    for phase in range(phases):
        for S, u, stage, first, cnt, src, _ in pb["starts"]:
            if src != "leaf":
                continue
            time = S % H + phase * H
            if not active(time, u):
                continue
            is_init = time == bounds[u]["init"]
            if is_init:
                if stage != 0 or cnt != initial["cnt"]:
                    raise ScheduleError("INIT must replace a complete equal-count token-start range")
                first = initial["first"]
            leaf.append(dict(time=time, user=u, stage=stage, first=first, cnt=cnt,
                             initial=is_init, retirement=time == bounds[u]["retire"]))
    leaf.sort(key=lambda e: e["time"])
    gaps = [b["time"]-a["time"] for a, b in zip(leaf, leaf[1:])]
    gaps.append(leaf[0]["time"] + period - leaf[-1]["time"])
    if min(gaps) < O.LEAF_MIN_GAP:
        raise ScheduleError("expanded leaf violates the measured ROM prefetch gap")
    if len(leaf)+1 > ROM_BANKS*ROM_DEPTH:
        raise ScheduleError("expanded admission exceeds the sized three-ROM leaf")
    words = [(MAGIC << 59) | (period << 36) | (len(leaf) << 22) | T]
    for e in leaf:
        t = (e["time"] - 1) % period
        if e["first"] % 4 or e["first"] >= 1024 or not 0 < e["cnt"] < 1024:
            raise ScheduleError("calendar range exceeds the explicit10-bit entry ABI")
        words.append((int(e["initial"]) << 71) | ((t >> 22) << 69) |
                     (e["cnt"] << 59) | (e["first"] << 49) | (e["stage"] << 43) |
                     (e["user"] << 41) | ((t & ((1 << 22)-1)) << 19))

    links = {c: [] for c in ("C_tx", "C_rx", "K_tx", "K_rx")}
    active_units, completed = [], {u: 0 for u in units}
    known_end = {u: (bounds[u]["retire_end"], "retirement head length") for u in bounds}
    for phase in range(phases):
        for u, seq in units.items():
            for t, name, block in seq:
                time = phase*H+t
                if not active(time, u):
                    continue
                active_units.append(dict(time=time, user=u, name=name, stage=block["stage"]))
                if name == "head" and (u == 0 or time != bounds[u]["init"]):
                    completed[u] += 1
                windows = block["windows"]
                if u:
                    for resource, intervals in windows.items():
                        for _, end in intervals:
                            if time+end > known_end[u][0]:
                                known_end[u] = (time+end, name+":"+resource)
                exchanges = []
                if "d2d_q" in windows:
                    exchanges += [(time+windows["d2d_q"][0][0], "req", 0),
                                  (time+windows["d2d_q"][0][0], "rsp", 0)]
                if name == "head":
                    exchanges += [(time+head_ref, "tok_tx", 1), (time+head_ref, "tok_rx", 1)]
                for ref, segment, sel in exchanges:
                    for calendar, desc in link_images[segment].items():
                        raw = ref+desc["start"]
                        links[calendar].append(dict(time=raw % period, segment=sel, user=u,
                                                    owner_time=time, owner_name=name,
                                                    crossing=raw//period))
    for events in links.values():
        events.sort(key=lambda e: e["time"])
    for u, (end, owner) in known_end.items():
        if end >= bounds[u]["next_load"]:
            raise ScheduleError(f"user{u}: known operator {owner} is live at reload")
        bounds[u]["known_quiescence_end"] = end
        bounds[u]["known_quiescence_last_resource"] = owner
        bounds[u]["quiet_edges"] = bounds[u]["next_load"]-end
        first_l0 = min(e["time"] for e in active_units if e["user"] == u and e["name"].startswith("L0"))
        emb = bounds[u]["init"] + O.result_timing(cal["inputs"].get("am_root_capture", 0))["emb_t"]
        if not bounds[u]["load_slot"]["bank_load"] < emb < first_l0:
            raise ScheduleError(f"user{u}: INIT embedding does not precede first L0")
        bounds[u]["first_embedding"] = emb
        bounds[u]["first_L0"] = first_l0
    head_block = heads[0][0][1]
    known_prefix_span = max([head_block["length"]] +
                            [end for intervals in head_block["windows"].values() for _, end in intervals])
    prefix_gap = 1  # finitecold-start guard: receive capture finishesbeforeL0sampling
    prefix_span = known_prefix_span + prefix_gap
    missing = []
    if not context_binding.get("measured", False):
        missing.append("validated context-slot to bank age not measured in bound RTL")
    if not identity_bound:
        missing.append("full face context image/digest/epoch/cap/user binding absent")
    if not q_readiness_bound:
        missing.append("real PW/DW512-seat producer and all32 Q-read times absent")
    missing += ["expanded leaf/list physical views not closed", "full INIT-to-token proof absent"]
    return dict(schema="opentallas.qwen.expanded_admission.v1", production_bound=False,
                verdict="BLOCKED", blockers=missing, base_H=H, H=period, T=T,
                phases=phases, origin=0, D0=16,
                anchor_contract=dict(relation="leaf_L0=OVL_anchor+D0+measured_list_and_pin_launch_age",
                                     list_launch_age=None, user0_prelude_bound=False),
                programme_abi=dict(UVM_STRIDE=O.UVM, PIDX_STRIDE=O.PIDX, NU=O.NU, OPSEG=1,
                                   STN_USER="52:51", STN_KCM1="66:59", table_user_allocation_bound=False),
                user0_prefix=dict(known_reservation_span=known_prefix_span, extra_guard_edges=prefix_gap,
                                  span=prefix_span, stage=0, user=0,
                                  init_first=initial["first"], init_cnt=initial["cnt"],
                                  stage0_relative_L0=-prefix_span,
                                  embedding_relative_L0=-prefix_span+O.result_timing(cal["inputs"].get("am_root_capture", 0))["emb_t"],
                                  stage0_epoch_edge=None, identity_and_embedding_bound=False),
                root_timing=O.result_timing(cal["inputs"].get("am_root_capture", 0)),
                context_binding=context_binding, boundaries=bounds, image=image,
                leaf_words=words, leaf_entries=leaf, leaf_min_gap=min(gaps),
                leaf_abi=dict(expanded=1, banks=ROM_BANKS, address_bits=ADDR_BITS,
                              period_bits=PERIOD_BITS, magic=MAGIC, header="magic13,H23,nent14,T22",
                              entry_time_hi_bit=69),
                active_units=active_units, link_starts=links,
                completed_tokens=completed, lifecycle_tok_s=sum(completed.values())*O.CLK/period,
                base_tok_s=cal["aggregate_tok_s"])


def write_artifacts(programme, out, instance="qfd_tt_ctlm_opseg"):
    """Write source-addressed PW/DW/three raw-ROM images and the complete receipt."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    files = {}
    for name, data, width in (("pw.hex", programme["image"]["pw"], 16),
                              ("dw.hex", programme["image"]["dw"], 16)):
        text = "".join(f"{word:0{width}x}\n" for word in data)
        (out/name).write_text(text)
        files[name] = hashlib.sha256(text.encode()).hexdigest()
    for bank in range(ROM_BANKS):
        name = instance + ("" if bank == 0 else f"_b{bank}") + ".viamap.hex"
        text = O.viamap_hex(programme["leaf_words"][ROM_DEPTH*bank:ROM_DEPTH*(bank+1)])
        (out/name).write_text(text)
        files[name] = hashlib.sha256(text.encode()).hexdigest()
    receipt = dict(programme, artifact_sha256=files)
    (out/"admission.json").write_text(json.dumps(receipt, indent=2)+"\n")
    return receipt


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frame-input", type=Path, required=True,
                        help="source-pinned paired-slot frame JSON: cal,im,head_ref")
    parser.add_argument("--context-binding", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    frame_bytes = args.frame_input.read_bytes()
    if frame_bytes[:2] == b"\x1f\x8b":
        import gzip
        frame_bytes = gzip.decompress(frame_bytes)
    frame = json.loads(frame_bytes)
    binding = json.loads(args.context_binding.read_text())
    programme = compile_expanded(frame["cal"], frame["im"], head_ref=frame["head_ref"],
                                 context_binding=binding)
    programme["source_sha256"] = dict(frame=hashlib.sha256(frame_bytes).hexdigest(),
                                      context_binding=hashlib.sha256(args.context_binding.read_bytes()).hexdigest(),
                                      compiler=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                                      opcal=hashlib.sha256(Path(O.__file__).read_bytes()).hexdigest())
    write_artifacts(programme, args.out)
    print("EXPANDED_ADMISSION_COMPILED", programme["verdict"], "H", programme["H"],
          "entries", len(programme["leaf_entries"]), "tok_s", round(programme["lifecycle_tok_s"], 4))


if __name__ == "__main__":
    main()
