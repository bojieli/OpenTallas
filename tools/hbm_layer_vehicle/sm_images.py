#!/usr/bin/env python3
"""VEH-FMT-SM (10-18): SM / DMA programme PAYLOADS for the d4g SW-quadrant slice vehicle (GEN2 RTL of record).

layer_images.py lowers SU records and lists, for every other record, the host-CP targets it needs (SW_TARGETS); this
module is the row ABI of the SM-chain and DMA targets -- what the host writes into each target's own programme store
through the ingress (layer_images.CpBus) -- transcribed from the RTL the slice binds (bundle sw2: slice/slice.v,
rtl/, masters/).  Every encoder cites its RTL; every field is range-checked (a value that does not fit is an error,
never a silent truncation).

Targets (die.v GEN2 straps; hleaf_SW unless noted):
  cp_svg_SW<k> 64+k   ot_static_cmd_target MODE 0 (AWA 10 / AWB 7 / RBW 7 / RCW 8): window A = the SM service
                      group's programme calendar rows (ot_smh_calendar_static W135 envelope), window B = issuer
                      descriptors (ot_hbm_svc_sm_issuer FIXED_GO 1); one run launch.  k = 4..7 through hleaf_SE__b_*.
  xc_SW<k>     192+k  ot_hbm_svc_sm_xcal_t: MODE 0 collar (programme window A, descriptor window B = the SAME
                      descriptor rows as cp_svg) + ot_hbm_svc_sm_xcal -> SM command[191:83] (cmd_ext) + kv_desc.
  xl_SW_ctl    100    ot_hgi_sm_xload_cl2_ctlx: MODE 1 command table, CW 108 (x-load commands on fixed cycles).
  smw_SW       160    ot_hbm_sm_vm_wr_q_t_lanes4: MODE 1 command table, CW 27 (SM result -> VM writer descriptors).
  calendar_SW  96     hfd_hgi_vm_calendar_f20 (hleaf_SW a group): VM bank calendar rows (wslot for the SM writer).
  hb_dbk_SW    104    ot_hgi_dma_back_static_vp4_banks_cp: MODE 1 command table, CW 308, RELF 2 (DMA dispatcher).
STATUS (VEH-FMT-SM2 10-19): row encoders only (VEH-FMT-SM draft 10-18, transcribed from the RTL, not yet exercised by a
slice replay).  The SM's own 83-bit normal-op calendar (the cmd83 field of svg_word) is compiled and pre-checked on the
die SM master by sm_mv_unit.py.
"""
from __future__ import annotations

MAGIC_ROW = 0xC7A1          # programme-row magic of every ot_static_program_target-style store (cfg_data[255:240])
MAGIC_DESC = 0x5D15         # ot_hbm_svc_sm_issuer descriptor magic (desc[255:240])


def _put(v, lo, w, x, name):
    x = int(x)
    if not 0 <= x < 1 << w:
        raise ValueError(f"{name}={x} does not fit {w} b")
    return v | (x << lo)


# --------------------------------------------------------------------------------------------- MODE 1 command tables
def cmd_table_rows(entries, cw):
    """ot_static_cmd_target_core MODE 1 table (host_static_20261015/ot_static_cmd_target.sv:132-136, 152-160): entry =
    {payload[cw], at[31:0]} (EW = 32 + cw), NW = ceil(EW/256) table rows per entry, host row = entry * NW + word.
    entries = [(at, payload)] in issue order.  Returns [(row, 256-b data)] for window 2 (cfg_addr = 0x800 | row)."""
    ew = 32 + cw
    nw = (ew + 255) // 256
    assert nw <= 4 and len(entries) <= 128, (nw, len(entries))
    rows = []
    for e, (at, pl) in enumerate(entries):
        v = _put(_put(0, 0, 32, at, "at"), 32, cw, pl, "payload")
        for w in range(nw):
            rows.append((e * nw + w, (v >> (256 * w)) & ((1 << 256) - 1)))
    return rows


CMD_WIN_TABLE, CMD_PERIOD_ADDR = 0x800, 0xC00


# ------------------------------------------------------------------------------------------------- smw_SW (writer)
def smw_cmd(base, stride, P, mir=0, fmt=0, h=0):
    """ot_hbm_sm_vm_wr_q_t_lanes4 descriptor cmd[26:0] (ot_hbm_sm_vm_wr_q_t_lanes_n.sv:117-118): base row [9:0],
    stride rows [19:10], P phases 1..8 [23:20], mirror [24], fmt (1 = BF16 RNE of the FP32 word) [25], half [26]
    (0 = banks 0-3 / wq_s, 1 = banks 4-7 / wq_t).  SM k (k = 0..3) row r phase p -> bank k + 4h, VM row
    base + r[11:3] + p*stride, lane r[2:0]."""
    if not 1 <= P <= 8:
        raise ValueError(f"smw P={P} outside 1..8")
    v = _put(0, 0, 10, base, "base")
    v = _put(v, 10, 10, stride, "stride")
    v = _put(v, 20, 4, P, "P")
    v = _put(v, 24, 1, mir, "mir")
    v = _put(v, 25, 1, fmt, "fmt")
    return _put(v, 26, 1, h, "h")


SMW_CW, SMW_LEAD = 27, 8


def smw_word_place(k, r, p, base, stride, h=0):
    """(bank, VM row, lane) the writer puts SM k's result row r, phase p at (lanes_n.sv:141, 158, 174-176)."""
    row = base + (r >> 3) + p * stride
    if row >= 1024:
        raise ValueError("smw row overflow (sticky fault)")
    return k + 4 * h, row, r & 7


# ------------------------------------------------------------------------------------------- calendar_SW (VM banks)
CAL_FIELDS = dict(client_seq=(0, 10), response_enable=(10, 5), response_seq=(15, 10), bank_enable=(25, 8),
                  bank_client=(33, 24), hub_ring_enable=(57, 2), hub_ring_client=(59, 6), rslot_v=(65, 8),
                  wslot_v=(73, 8), rslot=(81, 24), wslot=(105, 24), ring_tx_enable=(129, 2), ring_tx_source=(131, 6),
                  replay_enable=(137, 1), replay_source=(138, 1), lg_local_read=(139, 24), lg_local_write=(163, 24))
CAL_W = 187
WSLOT_SMW = 1               # write owner code of wq1 = smw (ot_vms_bank_q0_faces body: 0 su lg, 1 smw, 2 COLL, ...)


def cal_word(**f):
    """hfd_hgi_vm_calendar_f20 calendar word (calendar.sv:108-124)."""
    v = 0
    for k, x in f.items():
        lo, w = CAL_FIELDS[k]
        v = _put(v, lo, w, x, k)
    return v


def cal_wslot(banks, owner=WSLOT_SMW):
    """calendar word granting write owner `owner` on every bank in `banks` this edge."""
    wv = ws = 0
    for b in banks:
        wv |= 1 << b
        ws |= owner << (3 * b)
    return cal_word(wslot_v=wv, wslot=ws)


def prog_row(addr, payload, w):
    """programme row of an ot_static_program_target-style store: magic [255:240], reserved 0 [239:234], row identity
    [233:224] (= cfg_addr[9:0]), reserved 0, payload [w-1:0] (program_target.sv:88-89)."""
    assert w <= 224
    return _put(_put(0, 0, w, payload, "payload"), 224, 10, addr, "addr") | (MAGIC_ROW << 240)


# ---------------------------------------------------------------------- svg (service group: issuer + programme)
def svg_desc(i, base, row_base, landing, epoch, rows, tag_base, prog_base, prog_limit, loops, go_at):
    """ot_hbm_svc_sm_issuer descriptor row i (ot_hbm_svc_sm_issuer.sv:9-11, :74-75): [31:0] base, [46:32] row_base,
    [48:47] landing, [64:49] epoch, [71:65] rows (1..64), [81:72] tag_base, [91:82] prog_base, [102:92] prog_limit,
    [118:103] loops, [142:119] go_at (FIXED_GO: stream edge from the run launch), [239:233] row identity = i,
    [255:240] 5d15, all other bits 0."""
    if not 1 <= rows <= 64:
        raise ValueError(f"rows={rows}")
    v = _put(0, 0, 32, base, "base")
    v = _put(v, 32, 15, row_base, "row_base")
    v = _put(v, 47, 2, landing, "landing")
    v = _put(v, 49, 16, epoch, "epoch")
    v = _put(v, 65, 7, rows, "rows")
    v = _put(v, 72, 10, tag_base, "tag_base")
    v = _put(v, 82, 10, prog_base, "prog_base")
    v = _put(v, 92, 11, prog_limit, "prog_limit")
    v = _put(v, 103, 16, loops, "loops")
    v = _put(v, 119, 24, go_at, "go_at")
    v = _put(v, 233, 7, i, "identity")
    return v | (MAGIC_DESC << 240)


def svg_sectors(rows):
    """sectors of a block of `rows` 136-B records (issuer.sv:57, feed: ceil(rows*136/128)*4)."""
    return ((rows * 136 + 127) >> 7) << 2


def svg_word(cmd83=0, read=None, retire=None):
    """W135 programme envelope (ot_hbm_svc_sm_feed_programmed_id.sv header): [82:0] SM command, [83] read_v,
    [84] bank, [100:85] epoch, [106:101] row, [116:107] tag; [117] retire_v, [118] bank, [134:119] epoch.
    read = (bank, epoch, row, tag), retire = (bank, epoch)."""
    v = _put(0, 0, 83, cmd83, "cmd83")
    if read is not None:
        b, ep, row, tag = read
        v |= 1 << 83
        v = _put(v, 84, 1, b, "read_bank")
        v = _put(v, 85, 16, ep, "read_epoch")
        v = _put(v, 101, 6, row, "read_row")
        v = _put(v, 107, 10, tag, "read_tag")
    if retire is not None:
        b, ep = retire
        v |= 1 << 117
        v = _put(v, 118, 1, b, "retire_bank")
        v = _put(v, 119, 16, ep, "retire_epoch")
    return v


SVG_W = 135


# ------------------------------------------------------------------------------------------- xl_SW_ctl (x-loader)
XL_CW, XL_LEAD, XL_RD_LAT, XL_PMAX = 108, 8, 6, 8
XC, XOFF = 3152, 2128        # x record bits per SM column part, BF16 field offset (ot_hgi_sm_xload_static_cl2.sv)


def xl_cmd(base, n, p, stride, fmt=0, xb=0, space=1):
    """ot_hgi_sm_xload_cl2_ctl x-load command[107:0] (cl2:615-618): x_base [39:0] (FP32-element VM address: [2:0] = 0,
    [5:3] bank, [15:6] row, [17:16] = slice id 0), x_n [60:40] elements per part, x_p [64:61] parts 1..8 (part p'
    -> SM x-column p'), x_stride [96:65] elements between parts (8-aligned), x_space [98:97] = 1, x_fmt [100:99]
    (0/3 BF16 path, 1 FP8 block-dot, 2 FP8-for-FP4), x_xb [107:101] SM x-buffer base row.  c_bad (cl2:121-122)
    refused here: a bad command is a sticky x_fault in the RTL."""
    if space != 1 or base & 7 or stride & 7 or not 1 <= p <= XL_PMAX or n == 0 or (fmt in (1, 2) and n % 32):
        raise ValueError(f"x-load command c_bad: base={base} n={n} p={p} stride={stride} fmt={fmt}")
    v = _put(0, 0, 40, base, "x_base")
    v = _put(v, 40, 21, n, "x_n")
    v = _put(v, 61, 4, p, "x_p")
    v = _put(v, 65, 32, stride, "x_stride")
    v = _put(v, 97, 2, space, "x_space")
    v = _put(v, 99, 2, fmt, "x_fmt")
    return _put(v, 101, 7, xb, "x_xb")


def xl_bf_timing(n, p, rd_lat=XL_RD_LAT):
    """BF-path (fmt 0/3) x-load timing relative to C = the ctl cmd_v cycle (= launch-at-pin + 3 + LEAD + at):
    VM read waves (one per edge, all 8 banks) at C+2+g*8nb+8p'+w, g < gn = ceil(n/512), p' < p, w < 8;
    first xw_en at the SM pins C+22+8p, last C+21+8p+8*gn*nb (nb = ceil(3152p/2048)); next command >= C+23+8p+8gn*nb.
    rd_lat = the ctl's RD_LAT build parameter (6 in the die)."""
    gn = -(-n // 512)
    nb = -(-XC * p // 2048)
    waves = [2 + g * 8 * nb + 8 * pp + w for g in range(gn) for pp in range(p) for w in range(8)]
    d = rd_lat - 6
    return dict(gn=gn, nb=nb, waves=waves, first_xw=22 + 8 * p + d, last_xw=21 + 8 * p + 8 * gn * nb + d,
                next_cmd=23 + 8 * p + 8 * gn * nb + d)


def xl_bf_place(i, pp, xb):
    """SM x-buffer place of element i of part pp (BF path): (xw_addr, bit offset in the 3152p'-bit row image)."""
    return (xb + 8 * (i >> 9) + (i & 7)) & 127, XC * pp + XOFF + 16 * ((i >> 3) & 63)
