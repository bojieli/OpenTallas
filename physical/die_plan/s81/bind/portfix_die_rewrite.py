#!/usr/bin/env python3
"""S81/PORTFIX (2026-10-25): die-top rewrite of the S81 as-built (dv_die) for S81 DECISIONS 3 / 4 (CFG + fault rings).

Run after tools/s81_dv/svc_rs/svc_rs_face_bind.py and tools/s81_dv/portfix_dead/dead_die_rewrite.py (DECISION 5):
  portfix_die_rewrite.py IN.v OUT.v MAP_IN.json MAP_OUT.json REPORT.json

  CFG (DEC 3)  u_eng: cfg_en / cfg_layer / cfg_rank die inputs removed (boot-time CTL cfg op on the column-6 V rung);
               u_iqf: uid die input removed (CONFIG frame on qs).  st[3:0] -> 1-bit sticky fault.
  FLT (DEC 4)  every unit's 1-bit sticky fault goes to a die-level ring stop (ot_s81_frs, rtl/dsrom_sys/s81_dv/unit) in a
               ring partition: sid ring seqhost.sid_ro -> s_7S_C .. s_0S_C -> s_0N_C .. s_7N_C -> seqhost.sid_ri,
               vid ring seqhost.vid_ro -> svc_0,2,..,14,15,13,..,1 -> seqhost.vid_ri (plan v4.8 order, 1-b lanes);
               feeders (plan flt__* lanes): iqf -> svc_0, eng -> svc_14, phy_hbm k_oor -> svc_8, bk_sel -> gunit stop ->
               s_3N_C, lep LP faults -> their C stop (the lep wrapper fault).  Detailed status die outputs dropped with
               their RTL ports (FLT branch); landing (transport) fault outputs are disconnected: the binder dissolves
               the landings into its own registered lanes.  Die fault/status ports removed.
  H4 (planned class): bk_sel tl_o -> s_0N lep tl, lep ca / cb -> bk_sel ca / cb wired (die ports removed).
  Die ports kept that other lanes own: iqf_ql / iqf_qc0 / iqf_qc1 (S81/IDXNET), the SerDes PMA ports.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import asbparse as A  # noqa: E402

src, dst, map_in, map_out, rep_path = sys.argv[1:6]
lines, I = A.parse(src)
rep = dict(changed={}, removed_ports=[], stops={}, errors=[])

DROP_PORTS = {"s_0N_hb_arm_mask", "s_0N_hb_arm_commit", "s_0N_hb_fault", "s_0N_hb_hbc_fault", "s_0N_hb_return_fault",
              "s_0N_hb_ctx_valid", "phy_hbm_k_oor", "rsv_05_so_ready", "rsv_05_so_done", "rsv_05_so_fault_code",
              "rsv_11_so_ready", "rsv_11_so_done", "rsv_11_so_fault_code", "bk_sel_vm_fault", "bk_sel_tx_st",
              "seqhost_t_mf", "seqhost_hostb_fault", "seqhost_hb_job_active", "iqf_st", "iqf_uid", "eng_cfg_en",
              "eng_cfg_layer", "eng_cfg_rank", "eng_st", "land_fault", "endpoint_fault", "block_fault"} | \
             {"irg_%02d_st" % k for k in range(8)}
FAULT_NET = re.compile(r"^(block_fault|endpoint_fault|land_fault)\[\d+\]$")
TRANSPORT_LAND = re.compile(r"^(dsfd_dvland_\d+l?|dsdv_svc_busland_\d+|dsdv_pv_local_land_n32_source4_276)$")

newwires = []
fnet = {}                                   # instance -> its fault net


def conn(d, p):
    for q, e in d["conns"]:
        if q == p:
            return e
    return None


def setc(inst, drop=(), ren=None, add=None):
    d = I[inst]
    before = [p for p, _ in d["conns"]]
    out = []
    for p, e in d["conns"]:
        if p in drop:
            continue
        if ren and p in ren:
            p, e = ren[p]
        out.append([p, e])
    for p, e in (add or []):
        out.append([p, e])
    d["conns"] = out
    d["dirty"] = True
    rep["changed"][inst] = dict(module=d["module"], dropped=[p for p in before if p in drop],
                                renamed={k: v[0] for k, v in (ren or {}).items()}, added=[p for p, _ in (add or [])])


def fault_of(inst, port="fault", new=None):
    """re-point inst.port (a die-port fault bit) to a named 1-bit net f_<inst>"""
    n = "f_" + inst[2:]
    newwires.append(n)
    setc(inst, ren={port: (new or port, n)})
    fnet[inst] = n
    return n


# ---- DEC 3: CFG (eng / iqf) + their 1-bit faults
fault_of("u_eng", "st", "fault")
setc("u_eng", drop=("cfg_en", "cfg_layer", "cfg_rank"))
fault_of("u_iqf", "st", "fault")
setc("u_iqf", drop=("uid",))
# ---- DEC 4: unit faults
fault_of("u_bk_sel")
setc("u_bk_sel", drop=("vm_fault", "tx_st"))
fault_of("u_gunit")
for k in range(8):
    fault_of("u_irg_%02d" % k, "st", "fault")
for k in (5, 11):
    i = "u_rsv_%02d" % k
    fault_of(i)
    setc(i, drop=("so_ready", "so_done", "so_fault_code"))
for k in range(16):
    fault_of("u_etap_%02d" % k)
fault_of("u_phy_hbm", "k_oor")
n = "f_s_0N_hb"
newwires.append(n)
setc("u_s_0N", drop=("hb_arm_mask", "hb_arm_commit", "hb_hbc_fault", "hb_return_fault", "hb_ctx_valid"),
     ren={"hb_fault": ("hb_fault", n)})
fnet["u_s_0N.hb"] = n
for h in ("0S", "0N", "7S", "7N") + tuple("%d%s" % (c, s) for c in range(1, 7) for s in "SN"):
    fault_of("u_s_" + h)
for i in ("ld_pv_E", "ld_pv_W"):
    fault_of(i)
# landing transports: fault output disconnected (dissolved by the binder); u_bk_col (retired, transport) likewise
for inst, d in I.items():
    e = conn(d, "fault")
    if e and FAULT_NET.match(e) and inst not in fnet:
        if TRANSPORT_LAND.match(d["module"]) or inst == "u_bk_col":
            setc(inst, drop=("fault",))
        else:
            rep["errors"].append("unhandled fault net %s.fault(%s) [%s]" % (inst, e, d["module"]))
# seqhost: status outputs dropped (internal now); ring ends
setc("u_seqhost", drop=("t_mf", "hostb_fault", "hb_job_active"),
     add=[("sid_ro", "fr_sid_seqhost"), ("vid_ro", "fr_vid_seqhost"), ("sid_ri", "fr_sid_ret"), ("vid_ri", "fr_vid_ret")])
newwires += ["fr_sid_seqhost", "fr_vid_seqhost", "fr_sid_ret", "fr_vid_ret"]

# ---- S81/H4 tree lanes (planned class): bk_sel tl_o -> s_0N lep tl, s_0N lep ca / cb -> bk_sel ca / cb (the H4 RTL
# ports of ot_s81sl_slice_lepw_mab_hbc_prod_mu_72; were die ports bk_sel_ca / bk_sel_cb / bk_sel_tl_o in the as-built)
if conn(I["u_bk_sel"], "tl_o") == "bk_sel_tl_o" and conn(I["u_s_0N"], "tl") is None:
    setc("u_bk_sel", ren={"tl_o": ("tl_o", "h4_tl"), "ca": ("ca", "h4_ca"), "cb": ("cb", "h4_cb")})
    setc("u_s_0N", add=[("tl", "h4_tl"), ("ca", "h4_ca"), ("cb", "h4_cb")])
    DROP_PORTS |= {"bk_sel_ca", "bk_sel_cb", "bk_sel_tl_o"}
    H4_WIRES = ["  wire [275:0] h4_tl, h4_ca, h4_cb;"]
else:
    rep["errors"].append("H4 wiring: unexpected as-built tl / ca / cb connections")
    H4_WIRES = []

# ---- ring stops
inv_in = {}
for ln in lines:
    m = re.search(r"INVx2_ASAP7_75t_R \w+ \(\.A\(([\w\[\]]+)\), \.Y\((u_rsv_\d+_rst)\)\)", ln)
    if m:
        inv_in[m.group(2)] = m.group(1)


def ckrst(inst):
    d = I[inst]
    ck = None
    for p in ("ck", "clk", "ck_C", "ck_S", "ck_K", "ck_line"):
        ck = ck or conn(d, p)
    r = conn(d, "rst_n")
    if r is None and conn(d, "rst") in inv_in:
        r = inv_in[conn(d, "rst")]
    if ck is None or r is None:
        rep["errors"].append("no clock / active-low reset found on %s" % inst)
    return ck, r


stops = []          # (part, ref inst, [local f nets], fi, fo)
sid_parts = ["s_%d%s_C" % (k, "S") for k in range(7, -1, -1)] + ["s_%d%s_C" % (k, "N") for k in range(8)]
vid_parts = ["svc_%d" % n for n in list(range(0, 16, 2)) + list(range(15, 0, -2))]
# gunit stop: fi = bk_sel feeder, f = gunit fault -> s_3N_C
stops.append(("gunit", "u_gunit", [fnet["u_gunit"]], fnet["u_bk_sel"], "fr_gunit"))
newwires.append("fr_gunit")
prev = "fr_sid_seqhost"
for p in sid_parts:
    h = p[2:4]
    f = [fnet["u_s_" + h]]
    if h == "0N":
        f.append(fnet["u_s_0N.hb"])
    if h == "3N":
        f.append("fr_gunit")
    if h == "4S":
        f.append(fnet["ld_pv_E"])
    if h == "3S":
        f.append(fnet["ld_pv_W"])
    fo = "fr_sid_" + p
    stops.append((p, "u_s_" + h, f, prev, fo))
    newwires.append(fo)
    prev = fo
stops[-1] = stops[-1][:4] + ("fr_sid_ret",)
newwires.remove("fr_sid_" + sid_parts[-1])
prev = "fr_vid_seqhost"
for p in vid_parts:
    k = int(p[4:])
    f = []
    if k % 2 == 0:
        f += [fnet["u_etap_%02d" % k], fnet["u_etap_%02d" % (k + 1)], fnet["u_irg_%02d" % (k // 2)]]
    if k in (5, 11):
        f.append(fnet["u_rsv_%02d" % k])
    if k == 0:
        f.append(fnet["u_iqf"])
    if k == 14:
        f.append(fnet["u_eng"])
    if k == 8:
        f.append(fnet["u_phy_hbm"])
    fo = "fr_vid_" + p
    stops.append((p, "u_rsv_%02d" % k, f, prev, fo))
    newwires.append(fo)
    prev = fo
stops[-1] = stops[-1][:4] + ("fr_vid_ret",)
newwires.remove("fr_vid_" + vid_parts[-1])

stop_lines = ["  // ---- S81/PORTFIX (DECISION 4): die fault ring stops (ot_s81_frs: s <= s | (|f); fo <= fi | s)"]
mp = json.load(open(map_in))
for part, ref, f, fi, fo in stops:
    ck, r = ckrst(ref)
    nm = "u_frs_" + part
    if f:
        stop_lines.append("  ot_s81_frs #(.NL(%d)) %s (.ck(%s), .rst_n(%s), .f({%s}), .fi(%s), .fo(%s));"
                          % (len(f), nm, ck, r, ", ".join(f), fi, fo))
    else:
        stop_lines.append("  ot_s81_frs0 %s (.ck(%s), .rst_n(%s), .fi(%s), .fo(%s));" % (nm, ck, r, fi, fo))
    mp["parts"][nm] = part
    rep["stops"][nm] = dict(part=part, f=f, fi=fi, fo=fo, ck=ck, rst_n=r)
mp["note"] = mp.get("note", "") + " | S81/PORTFIX 10-25: + u_frs_<part> fault ring stops"

# ---- emit
for inst, d in I.items():
    if d.get("dirty"):
        lines[d["line"]] = A.emit(d["module"], d["params"], inst, d["conns"])
hdr = lines[1]
m = re.match(r"^module dv_die \((.*)\);\s*$", hdr)
ports = [p.strip() for p in m.group(1).split(",")]
keep = [p for p in ports if p not in DROP_PORTS]
rep["removed_ports"] = [p for p in ports if p in DROP_PORTS]
lines[1] = "module dv_die (%s);" % ", ".join(keep)
out = []
for i, ln in enumerate(lines):
    dm = re.match(r"^\s*(input|output) wire (\[[^\]]*\] )?(\w+);\s*$", ln)
    if dm and dm.group(3) in DROP_PORTS:
        continue
    if ln.strip() == "endmodule" and i > 2 and not any("u_frs_" in x for x in out):
        out.append("  wire %s;" % ", ".join(sorted(set(newwires))))
        out += H4_WIRES
        out += stop_lines
    out.append(ln)
txt = "\n".join(out)
for pn in DROP_PORTS:
    if re.search(r"\b%s\b" % pn, txt):
        rep["errors"].append("die port %s still referenced" % pn)
open(dst, "w").write(txt)
json.dump(mp, open(map_out, "w"), indent=0)
json.dump(rep, open(rep_path, "w"), indent=1)
print(json.dumps(dict(changed=len(rep["changed"]), removed_ports=len(rep["removed_ports"]), stops=len(rep["stops"]),
                      errors=rep["errors"][:20])))
sys.exit(1 if rep["errors"] else 0)
