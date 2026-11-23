"""CLAND-FFKEY-CLAMP-1123 (FABLE-OPEN-KV x15): static census of landing bands whose chunked read-select key passes the bus.

landing_placement.tcl cland_ffkey keys the one-hot read selects of each 64-bit ring chunk (dch[c].u_dsel/di[k]) at the
chunk centre bit c*WCH + WCH/2.  ot_dp_clk_landing_ca pads the ring to RW = ceil(W/64)*64 (ot_meso_ring_ca: NCH =
RW/64 chunks of WCH = 64 when RW % 64 == 0, else one chunk of WCH = RW), so the last chunk's centre lies at or past the
bus width W whenever W % 64 is 1..32 (KV kv3_hroot: W 145, chunk 2 centre 160).  Before the clamp such a select group fell
back to its raw-name key and packed at the band's low corner (468 um round trip); now the Tcl clamps it to bit W-1 and
prints OT_CLAND_FFKEY_CLAMP.  This census needs only the plan: band width (or the bus width) and ring_width.

Only bands with ring_place == "ff" go through cland_ffkey (tag +ff/+ffr); others are listed as latent.  A band whose
type has a START pin cland_fstart_in_<bus> (landing_contract.pins) is marked start: there cland_ctl_rekey moves every di
select to the START bit anyway, so the clamp changes placement only on bands without one.  The chunk-centre keys of the
opt-in local-chunk forms (tcc, u_wen, srep) depend on runtime chunk widths and are not censused here.

  python3 -I tools/die_plan/cland_ffkey_clamp.py PLAN.json [PLAN.json ...] [--json]
"""
import argparse
import json
import sys


def chunking(ring_width):
    """(NCH, WCH) of ot_meso_ring_ca for a ring of width ring_width"""
    nch = ring_width // 64 if ring_width % 64 == 0 else 1
    return nch, ring_width // nch


def clamped_chunks(width, ring_width=None):
    """[(chunk, key_bit)] of chunks with real bus bits whose select key c*WCH + WCH/2 is >= width (clamped to width-1)"""
    rw = ring_width or ((width + 63) // 64) * 64
    nch, wch = chunking(rw)
    if nch < 1 or wch < 1:
        return []
    return [(c, c * wch + wch // 2) for c in range(nch) if c * wch + wch // 2 >= width]


def _types(plan):
    for key in ("partition_types", "types"):
        t = plan.get(key)
        if isinstance(t, dict):
            return sorted(t.items())
        if isinstance(t, list):
            return [(x.get("name"), x) for x in t]
    return []


def _bus_width(t, bus):
    for b in t.get("buses") or []:
        if b.get("name") == bus and isinstance(b.get("width"), int):
            return b["width"]
    for s in t.get("ft_slots") or []:
        if s.get("name", "") + "_i" == bus or s.get("name", "") + "_o" == bus:
            return s.get("width")
    return None


def census(plan):
    """rows {type, band, width, ring_width, chunk, key, clamp_to, ring_place, hard_core, start}"""
    rows = []
    for tn, t in _types(plan):
        lc = ((t or {}).get("clock") or {}).get("landing_contract") or {}
        bands = lc.get("bands") or {}
        pins = {p.get("name") for p in lc.get("pins") or [] if isinstance(p, dict)}
        for bn, band in sorted(bands.items()):
            w = band.get("width")
            if not isinstance(w, int):
                w = _bus_width(t, bn)
            if not isinstance(w, int) or w < 1:
                continue
            rw = band.get("ring_width") if isinstance(band.get("ring_width"), int) else None
            for c, k in clamped_chunks(w, rw):
                rows.append(dict(type=tn, band=bn, width=w, ring_width=rw or ((w + 63) // 64) * 64, chunk=c, key=k,
                                 clamp_to=w - 1, ring_place=band.get("ring_place"), hard_core=band.get("hard_core"),
                                 start=f"cland_fstart_in_{bn}" in pins))
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("plans", nargs="+")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--summary", action="store_true", help="counts only, no per-group lines")
    a = ap.parse_args(argv)
    out = {}
    for p in a.plans:
        with open(p) as f:
            out[p] = census(json.load(f))
    if a.json:
        json.dump(out, sys.stdout, indent=1)
        print()
        return 0
    for p, rows in out.items():
        live = [r for r in rows if r["ring_place"] == "ff"]
        moved = [r for r in live if not r["start"]]
        print(f"{p}: {len(rows)} clamped select groups ({len(live)} live ring_place=ff, "
              f"{len(rows) - len(live)} latent), {len({(r['type'], r['band']) for r in live})} live bands, "
              f"{len(moved)} live without a START pin (placement changes)")
        for r in ([] if a.summary else rows):
            print(f"  OT_CLAND_FFKEY_CLAMP {r['type']}.{r['band']} dch[{r['chunk']}] key {r['key']} >= width {r['width']}"
                  f" -> {r['clamp_to']} (ring {r['ring_width']}, ring_place {r['ring_place']}"
                  f"{', hard_core ' + r['hard_core'] if r['hard_core'] else ''}{', START' if r['start'] else ''})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
