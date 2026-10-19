"""Header-only component at the existing LP-reader/core-input capture edges."""
from pathlib import Path
import collections,json
ROOT=Path(__file__).resolve().parents[2]
def generate():
    rows=json.loads((ROOT/'results/arch/safe_qw_slice_w_1019/stream_header_producer/header_boundary.json').read_text())
    counts=collections.Counter((r['source_port'],r['source_bit']) for r in rows)
    assert counts=={('sw_i',1087):90,('sw_i',1084):2,('sw_i',1085):2,('sw_i',1086):2,('se_i',1087):50}
    L=['''// PRIVATE GENERATED HEADER COMPONENT. Not a parent/consumer adoption.
// Model edaa82b7a: zero new data edges,201 FFs excluding parent reset forests.
`default_nettype none
module qfd_dv_stream_header_producer (
    input wire ck,
    input wire [4:0] rst_read,
    input wire [6:0] rst_capture,
    input wire [4*1088-1:0] sw_bank,se_bank,
    input wire [11:0] sw_epo,se_epo,
    input wire [4*46-1:0] sw_vld,se_vld,
    output wire [95:0] sw_i_copies,
    output wire [49:0] se_i_copies
);''']
    groups=[('sw_i',1087,4),('sw_i',1084,1),('sw_i',1085,1),('sw_i',1086,1),('se_i',1087,3)]
    names={}
    for g,(port,bit,n) in enumerate(groups):
        side=port[:2];name=f'{side}_bit{bit}_pre';names[port,bit]=(name,n)
        bank='{'+','.join(f'{side}_bank[{1088*s+bit}]' for s in reversed(range(4)))+'}'
        L += [f'    wire [{n-1}:0] {name};',f'    ot_pl_land_field_copies #(.COPIES({n}),.D(4),.K(2)) u_pre{g}(',
              f'        .ck(ck),.rsi(rst_read[{g}]),.bank({bank}),.epo({side}_epo),',
              f'        .vld({side}_vld[{4*(bit//24)}+:4]),.o({name}));']
    reset_group=0
    for port,total in [('sw_i',96),('se_i',50)]:
        prows=[r for r in rows if r['port']==port+'_copies']
        assert sorted(r['copy_bit'] for r in prows)==list(range(total))
        occurrence=collections.Counter();expressions={}
        for row in sorted(prows,key=lambda r:r['copy_bit']):
            assert row['source_port']==port and 1<=row['loads']<=24
            name,n=names[port,row['source_bit']];i=occurrence[row['source_bit']];occurrence[row['source_bit']]+=1
            expressions[row['copy_bit']]=f'{name}[{i%n}]'
        for base in range(0,total,24):
            width=min(24,total-base);d='{'+','.join(expressions[x] for x in reversed(range(base,base+width)))+'}'
            L += [f'    qfd_dv_header_capture_group #(.W({width}),.ID({reset_group})) u_capture{reset_group}(',
                  f'        .ck(ck),.rst_n(rst_capture[{reset_group}]),.d({d}),.q({port}_copies[{base}+:{width}]));']
            reset_group+=1
    assert reset_group==7
    L += ['''endmodule
(* keep_hierarchy="yes" *)
module qfd_dv_header_capture_group #(parameter integer W=24,ID=0)(
    input wire ck,rst_n,input wire [W-1:0] d,output wire [W-1:0] q
);
    generate for(genvar b=0;b<W;b=b+1) begin:g_bit
        (* keep_hierarchy="yes" *) qfd_dv_header_capture_bit #(.ID(ID*24+b)) u_bit(
            .ck(ck),.rst_n(rst_n),.d(d[b]),.q(q[b]));
    end
    if(W<1||W>24) begin:g_invalid
        QFD_HEADER_CAPTURE_GROUP_REQUIRES1_TO24 u_bad();
    end endgenerate
endmodule
(* keep_hierarchy="yes" *)
module qfd_dv_header_capture_bit #(parameter integer ID=0)(
    input wire ck,rst_n,d,output wire q
);
    (* keep=1 *) reg value;
    always @(posedge ck or negedge rst_n) if(!rst_n)value<=0;else value<=d;
    assign q=value;
endmodule
`default_nettype wire
''']
    return '\n'.join(L)
if __name__=='__main__':
    p=ROOT/'rtl/qwen_dv/qfd_dv_stream_header_producer.sv';p.write_text(generate());print(p)
