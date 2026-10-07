"""Opt-in S81 join construction; executable service top remains a parent blocker."""
import json
from functools import lru_cache
from s81_ctrl_join_model import read, TILE

WIDTHS = dict(rd=8896, rq=10912, rk=32, wd=32)


def joins(stack, ctrl, svc):
    return [(f'{p}_{stack}', 'hbm_read', bits,
             [(svc, p), (ctrl, p)] if p == 'rq' else [(ctrl, p), (svc, p)])
            for p, bits in WIDTHS.items()]


@lru_cache(None)
def pin_xs():
    rec = json.loads(read(TILE, 'physical/s81_ph_views/ports/contract/dsfd_ctrl_pc/ports.json'))
    xs = {p: [None]*w for p, w in WIDTHS.items()}
    for pc in range(32):
        for port, target, offset, width in [('rq','rq',pc*341,341), ('rk','rk',pc,1), ('wd','wd',pc,1),
                ('r_data','rd',pc*256,256), ('r_tag','rd',8192+pc*17,17),
                ('r_beat','rd',8736+pc*4,4), ('rv','rd',8864+pc,1)]:
            for b, pin in enumerate(rec['ports'][port]['pins']):
                xs[target][offset+b] = round(pc*265.584+(pin[2]+pin[4])/2, 4)
    assert all(x is not None for v in xs.values() for x in v)
    return xs


def service_pc_bank():
    """Complete boundary composition, NOT a replacement for dsfd_svc.

    Exposes existing quadrant ports; no invented quadrant behavior or IO tie-offs.
    Matching dsfd_svc_pc source is read from TILE by the component regression.
    """
    return '''// Generated service-PC boundary only. Full dsfd_svc quadrant/IO assembly is absent.
module dsfd_svc_pc_bank (
 input wire ck, rst,
 input wire [8895:0] rd,
 output wire [10911:0] rq,
 input wire [31:0] rk, wd,
 input wire [10911:0] qrq,
 output wire [31:0] qrk, qwd,
 output wire [8895:0] qrd
);
 genvar p;
 generate for(p=0;p<32;p=p+1) begin: g_pc
  dsfd_svc_pc u_pc (.ck(ck), .rst(rst),
   .rq(rq[p*341 +: 341]), .qrq(qrq[p*341 +: 341]),
   .rk(rk[p]), .qrk(qrk[p]), .wd(wd[p]), .qwd(qwd[p]),
   .rv(rd[8864+p]), .qrv(qrd[8864+p]),
   .r_data(rd[p*256 +: 256]), .qr_data(qrd[p*256 +: 256]),
   .r_tag(rd[8192+p*17 +: 17]), .qr_tag(qrd[8192+p*17 +: 17]),
   .r_beat(rd[8736+p*4 +: 4]), .qr_beat(qrd[8736+p*4 +: 4]));
 end endgenerate
endmodule
'''


def require_service_top():
    raise ValueError('S81 ctrl joins are component-only: pinned 3f0455126 has no executable dsfd_svc top/quadrant composition. Physical generation is blocked; a wider empty slab is not an endpoint repair.')
