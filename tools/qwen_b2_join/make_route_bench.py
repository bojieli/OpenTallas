#!/usr/bin/env python3
"""Q-B2 10-16: route-register composed temporal bench for the b2 phase calibration.

Built from the qualified actual composition tb_b2_rom_e3.sv (released ROM -> 384 hard multipliers -> six restored
ports -> source copy -> issuer -> six 24-bank halftrains -> native E3 VM).  Changes, each a counted exact substitution:
  * the controller tree and the issuer are the NEW parameter-free calibrated successors (calibration_sources.json);
  * every allocated die route is a register chain of its ACTUAL allocated edge count (allocator_ledger.json):
      tc controller->port (TC), am port->controller (AM), rq port->train (RQ), source ME fields / tags -> issuer
      (ME / TAG), issuer command -> trains (CMD, the registered fork tree incl. its 3 fork registers), rb train->VM (RB);
  * the issuer start is checked at the TRAIN face against the RQ arriving there (14 + TC + RQ edges after the tag),
    every RB beat at the VM face (+RB).  No ready/credit: a phase error is a $fatal, never absorbed.
Defines: OT_B2_ROUTE_TC ... (set by the generator from the ledger).  Gold arrays remain observers only.
"""
import argparse, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = 'tools/qwen_b2_join/tb_b2_rom_e3.sv'

DLY = '''
module tb_b2_route_dly #(parameter integer W=1, D=0)(input wire clk, input wire [W-1:0] d, output wire [W-1:0] q);
 // one register per allocated relay edge (die relays are plain registers on the same clock; no enable, no ready)
 generate if(D==0)begin:g0 assign q=d; end else begin:gd
  reg [W-1:0] r[0:D-1];
  always @(posedge clk)begin r[0]<=d; for(integer i=1;i<D;i=i+1) r[i]<=r[i-1]; end
  assign q=r[D-1];
 end endgenerate
endmodule
'''


def once(t, a, b, what):
    n = t.count(a)
    if n != 1:
        raise ValueError(f'{what}: expected exactly one occurrence, found {n}: {a[:80]!r}')
    return t.replace(a, b)


def make(cal, ages, out):
    t = (ROOT / SRC).read_text()
    tm = cal['calibrated_sources']['controller']['module'].replace('qfd_tt_ctlm_b2_', 'qfd_tt_ctlm_tree_b2_')
    im = cal['calibrated_sources']['issuer']['module']
    t = once(t, 'module tb_b2_rom_e3;', 'module tb_b2_route;\nparameter integer DTC=`OT_B2_ROUTE_TC,DAM=`OT_B2_ROUTE_AM,DRQ=`OT_B2_ROUTE_RQ,'
             'DME=`OT_B2_ROUTE_ME,DTAG=`OT_B2_ROUTE_TAG,DCMD=`OT_B2_ROUTE_CMD,DRB=`OT_B2_ROUTE_RB;', 'module')
    t = once(t, 'qfd_tt_ctlm_tree_b2 tree(', f'{tm} tree(', 'calibrated tree')
    t = once(t, 'wire[340:0]tc[0:5];', 'wire[340:0]tc[0:5],tcd[0:5];wire[51:0]amd[0:5];', 'tc decl')
    t = once(t, '.tc(tc[h])', '.tc(tcd[h])', 'port tc')
    t = once(t, 'assign pam[51*h+:51]=am[h][50:0];assign p_fault[h]=am[h][51];',
             'tb_b2_route_dly #(341,DTC) r_tc(clk,tc[h],tcd[h]);tb_b2_route_dly #(52,DAM) r_am(clk,am[h],amd[h]);\n'
             ' assign pam[51*h+:51]=amd[h][50:0];assign p_fault[h]=amd[h][51];', 'am route')
    # source copy -> issuer (ME fields and tags are separate allocator equal-age groups)
    t = once(t, 'wire ig,io,itv,itl;wire[17:0]itiles;wire[23:0]its;wire[3:0]isplit;',
             'wire ig,io,itv,itl;wire[17:0]itiles;wire[23:0]its;wire[3:0]isplit;\n'
             'wire ig_d,io_d,itv_d,itl_d;wire[17:0]itiles_d;wire[23:0]its_d;wire[3:0]isplit_d;\n'
             'tb_b2_route_dly #(1+18+24+4+1,DME) r_me(clk,{ig,itiles,its,isplit,io},{ig_d,itiles_d,its_d,isplit_d,io_d});\n'
             'tb_b2_route_dly #(2,DTAG) r_tag(clk,{itv,itl},{itv_d,itl_d});\n'
             'wire start_d,payload_d;wire[3:0]count_d,nh_d;wire[31:0]stride_d;\n'
             'tb_b2_route_dly #(1+4+32+1+4,DCMD) r_cmd(clk,{start,count,stride,payload,nh},{start_d,count_d,stride_d,payload_d,nh_d});\n'
             'wire[2212:0]rqd[0:5];wire[550:0]rbd[0:5];\n'
             'for(genvar h=0;h<6;h=h+1)begin:g_route tb_b2_route_dly #(2213,DRQ) r_rq(clk,rq[h],rqd[h]);'
             'tb_b2_route_dly #(551,DRB) r_rb(clk,rb[h],rbd[h]); end', 'issuer routes')
    t = once(t, 'qfd_res_train_issue_b2 #(.TRAIN_EDGES(13),.MUT(ISSUE_MUT))issuer(.ck(clk),.rst_n(rs),.me_go(ig),.me_tiles(itiles),'
                '.me_ts(its),.me_split(isplit),.me_oen(io),.tag_v(itv),.tag_last(itl),',
             f'{im} issuer(.ck(clk),.rst_n(rs),.me_go(ig_d),.me_tiles(itiles_d),.me_ts(its_d),.me_split(isplit_d),'
             '.me_oen(io_d),.tag_v(itv_d),.tag_last(itl_d),', 'calibrated issuer')
    for h in range(6):
        t = once(t, f'.train_start(start),.train_count(count),.capture_stride(stride),.payload_write(payload),.slot_count(nh),.rq(rq[{h}])',
                 f'.train_start(start_d),.train_count(count_d),.capture_stride(stride_d),.payload_write(payload_d),.slot_count(nh_d),.rq(rqd[{h}])',
                 f'train {h}')
        t = once(t, f'.rb{h}(rb[{h}]),', f'.rb{h}(rbd[{h}]),', f'vm rb{h}')
    t = once(t, ' if(start)begin\n  if(!rq[0][2212]||firsttag<0||cycle-firsttag!=14)',
             ' if(start_d)begin\n  if(!rqd[0][2212]||firsttag<0||cycle-firsttag!=14+DTC+DRQ)', 'start check at train face')
    t = once(t, 'if(cycle==startcycle+2+h*ens', 'if(cycle==startcycle+DRB+2+h*ens', 'rb at vm face')
    t = once(t, '  if(rb[h]!==erb)$fatal(1,"actual ROM/E3 exactRB pc%0d h%0d cycle%0d got%h want%h",op_pc,h,cycle,rb[h],erb);\n'
                '  if(rb[h][550]&&rb[h][549])opends=opends+1;',
             '  if(rbd[h]!==erb)$fatal(1,"actual ROM/E3 exactRB at VM face pc%0d h%0d cycle%0d got%h want%h",op_pc,h,cycle,rbd[h],erb);\n'
             '  if(rbd[h][550]&&rbd[h][549])opends=opends+1;', 'rb check')
    t = once(t, 'repeat(3000)@(negedge clk)', 'repeat(3000+4*(DTC+DAM+DRQ+DME+DTAG+DCMD+DRB))@(negedge clk)', 'drain')
    t = t.replace('$display("PASS actualROMport', '$display("ROUTE TC%0d AM%0d RQ%0d ME%0d TAG%0d CMD%0d RB%0d",DTC,DAM,DRQ,DME,DTAG,DCMD,DRB);\n $display("PASS actualROMport')
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(DLY + t)
    defs = {f'OT_B2_ROUTE_{k}': int(ages[k]) for k in ('TC', 'AM', 'RQ', 'ME', 'TAG', 'CMD', 'RB')}
    return defs


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('calibration_sources', type=Path)
    ap.add_argument('ledger', type=Path)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args(argv)
    cal = json.loads(a.calibration_sources.read_text()); L = json.loads(a.ledger.read_text())
    k = L['constants']
    ages = dict(TC=k['TC'], AM=k['AM'], RQ=k['RQ'], TAG=k['TAG'], CMD=k['CMD'], RB=k['RB'], ME=k.get('ME', k['TAG']))
    defs = make(cal, ages, a.out)
    (a.out.with_suffix('.defines')).write_text(' '.join(f'+define+{d}={v}' for d, v in defs.items()) + '\n')
    print(json.dumps(defs))


if __name__ == '__main__':
    sys.exit(main())
