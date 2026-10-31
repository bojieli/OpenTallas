#!/usr/bin/env python3
"""DIE-S81-42 10-31 seqhost SRAM event (COORD 06:45 RULING: AUTOBUILD-PIPE-5 ASK DEFAULT APPROVED, one-block S81 plan event).

seqhost__t1 inferred memories over SYNTH_MEMORY_MAX_BITS (ot_link_afifo u_hx 16 x 514, u_ox 16 x 289; dsdv_sh_sd 16 x 546
flop FIFO) -> the SRAM form that already exists in the RTL (S81-SHLK s10, benched): as-built defines
  OT_S81_SH_SRAM   ot_dsdv_host_afifo_sram for u_hx / u_ox, dsdv_sh_sd SRAM FIFO
  OT_S81_SH_RSZ    right-sized masters (2 x 16x257 for u_hx, 1 x 16x289 for u_ox and u_sd) -- WITHOUT it SRAM selects the
                   pin-limited 16x546 master and P192 has no effect (OT_SH_M257/M289 are only used under RSZ)
  OT_S81_SH_P192   the p192 contact-pitch masters (physical/asap7_memory_macros_pa)
  OT_S81_SH_APIPE9 + OT_S81_SH_APIPE10   APIPE 10 ingest (registered SRAM head); every s81_dv bench sets both
and 4 static macro sites in seqhost__t1 (sites: delta_seqhost_sram_1031.json, DIE-S81-32 place_sites.py rules: 8.64 lattice
+ track offset, >= 10.8 channels/stack gaps, clear of ft corridors / landing bands / taps / relays / existing macros,
43.2 edge band; check() 0 problems; render delta_seqhost_sram_1031.png).  Measured cost: host path f_host -> s_hw / t_host
completion +6 edges vs the current as-built (seqhost bench lock-step passes at TB_HSH 8, base 2).  No outline, bus, pin,
ft slot, clock, reset, neighbour or die datum change.  Asserts the exact old form; a second run refuses.
usage (repo root): python3 physical/die_plan/s81/delta_seqhost_sram_1031.py"""
import json
from pathlib import Path

S81 = Path(__file__).resolve().parent
PLAN = S81 / "plan_h2_2249.json"
ASB = S81 / "bind" / "asbuilt_b178_coll_h2_2249.json"
SITES = S81 / "delta_seqhost_sram_1031.json"
TAG = "DIE-S81-42 10-31 seqhost SRAM FIFO site (delta_seqhost_sram_1031.py)"
DEFINES = ["OT_S81_SH_SRAM", "OT_S81_SH_RSZ", "OT_S81_SH_P192", "OT_S81_SH_APIPE9", "OT_S81_SH_APIPE10"]
FILES = ["rtl/dsrom_sys/s81_dv/unit/host_sram/ot_dsdv_host_afifo_sram.sv",
         "physical/asap7_memory_macros_pa/ot_sram_1r1w2c_16x257_m1_p192/ot_sram_1r1w2c_16x257_m1_p192_bb.v",
         "physical/asap7_memory_macros_pa/ot_sram_1r1w2c_16x289_m1_p192/ot_sram_1r1w2c_16x289_m1_p192_bb.v"]


def compact(o):
    return json.dumps(o, separators=(",", ":"))


def main():
    txt = PLAN.read_text()
    plan = json.loads(txt)
    ev = json.loads(SITES.read_text())
    tn = ev["type"]
    t = plan["partition_types"][tn]
    assert t["contents"] == ev["old_contents"], "seqhost__t1 contents not in the expected old form (second run?)"
    assert t.get("core_pg_connect") is True
    W, H = t["outline_um"]
    for s in ev["sites"]:
        x, y = s["origin_um"]
        w, h = s["outline_um"]
        assert 0 < x and 0 < y and x + w < W and y + h < H, s["inst"]
    head = f'\n  "{tn}": {{\n'
    assert txt.count(head) == 1
    a = txt.index(head)
    b = txt.index('\n  },\n', a)
    block = txt[a:b]
    rows = list(ev["old_contents"])
    old = '   "contents": [\n' + "".join(f"    {compact(c)}{',' if i < len(rows) - 1 else ''}\n"
                                      for i, c in enumerate(rows)) + '   ],\n'
    assert block.count(old) == 1, "old contents text form"
    rows += [dict(inst=s["inst"], module=s["module"], status="new", lef=s["lef"], lib=s["lib"], origin_um=s["origin_um"],
                  outline_um=s["outline_um"], orient="R0", obs_max="M4", note=TAG) for s in ev["sites"]]
    new = '   "contents": [\n' + "".join(f"    {compact(c)}{',' if i < len(rows) - 1 else ''}\n"
                                      for i, c in enumerate(rows)) + '   ],\n'
    txt = txt[:a] + block.replace(old, new) + txt[b:]
    after = json.loads(txt)
    for k in plan:
        if k != "partition_types":
            assert after[k] == plan[k], k
    for k in plan["partition_types"]:
        if k != tn:
            assert after["partition_types"][k] == plan["partition_types"][k], k
    PLAN.write_text(txt)
    asb_txt = ASB.read_text()
    asb = json.loads(asb_txt)
    assert not set(DEFINES) & set(asb["defines"]), "defines already set (second run?)"
    asb["defines"] += DEFINES
    for f in FILES:
        assert (S81.parents[2] / f).exists(), f
        if f not in asb["files"]:
            asb["files"].append(f)
    asb["defines_note"] += (" | DIE-S81-42 10-31 (COORD 06:45): seqhost SRAM FIFOs " + " ".join(DEFINES) +
                            " (u_hx 2x16x257_p192, u_ox + u_sd 16x289_p192; plan sites delta_seqhost_sram_1031.py)")
    ASB.write_text(json.dumps(asb, indent=1) + "\n")
    print(f'{tn}: +{len(ev["sites"])} macro sites; asbuilt defines +{len(DEFINES)}, files +{len(FILES)}')


if __name__ == "__main__":
    main()
