#!/usr/bin/env python3
"""One SU tile with physical falling-edge output lockups for clock-root hops.

Same lane arithmetic and same receiving-edge values as the positive-edge tile.
Each output becomes visible half a cycle later. No whole-cycle latency added.
"""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import hbm_hub_quarter_gen as H

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);a=ap.parse_args()
    # The tile bit shape is invariant under the quarter face geometry.
    q=dict(H.QUARTERS['su']);p=H.Plan(q,{'ports':{'in':{'direction':'input','bits':6310},'out':{'direction':'output','bits':5376}}})
    p.tiled=True
    s=H.emit_tile(p).replace('module hfd_su_tile (','module hfd_su_tile_xl (')
    s=s.replace(f'output wire [{p.LB}:0] bc_out',f'output reg  [{p.LB}:0] bc_out')
    s=s.replace('    assign bc_out =',f'    wire [{p.LB}:0] bc_pos;\n    assign bc_pos =')
    s=s.replace('    always @(posedge clk) acc_out <=',f'    reg [{p.WCT-1}:0] acc_pos;\n    always @(posedge clk) acc_pos <=')
    s=s.replace('endmodule','''`ifdef OT_SU_TILE_MUT_NOLOCKUP
    always @(*) begin bc_out = bc_pos; acc_out = acc_pos; end
`else
    always @(negedge clk) begin bc_out <= bc_pos; acc_out <= acc_pos; end
`endif
endmodule''')
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    (out/'hfd_su_tile_xl.sv').write_text(s)
    (out/'hfd_su_tile.sv').write_text(H.emit_tile(p))
    (out/'ot_su12_light_simstub.sv').write_text(H.emit_stub(p))
    tw,th=187.056,164.16
    (out/'io_place.tcl').write_text(H.emit_tile_io(p,tw,th))
    (out/'macro_place.tcl').write_text('place_macro -macro_name {u_lane} -location {100.224 1.080} -orientation R0 -exact\n')
    (out/'tile.json').write_text(json.dumps(dict(master='hfd_su_tile_xl',w_um=tw,h_um=th,LB=p.LB,LO=p.LO,WCT=p.WCT,registered_bits=p.LB+1+p.LO+p.WCT,lockup_bits=p.LB+1+p.WCT,data_cycles_added=0,visibility_half_cycles_added=1),indent=2)+'\n')
if __name__=='__main__':main()
