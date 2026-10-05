#!/usr/bin/env python3
"""Owner-directed two kept parallel completion banks, default off."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'rtl/experimental/dsrom_reindex_kc7_20261005'
OUT=ROOT/'rtl/experimental/dsrom_reindex_kc7_split_20261005'
def once(s,a,b):
    assert s.count(a)==1,a[:90]
    return s.replace(a,b)
def emit():
    model=json.loads((ROOT/'results/uarch/dsrom_reindex_parallel_20261005/model.json').read_text())
    assert model['split']['new_ff_bits']==128 and model['split']['remaining_buffer_budget_um2']>0
    pins=json.loads((ROOT/'results/uarch/dsrom_reindex_kc7_20261005/source_manifest.json').read_text())
    donor=BASE/'ot_hdc_v41x_idx_kgather_kc7.sv'
    assert hashlib.sha256(donor.read_bytes()).hexdigest()==pins[str(donor.relative_to(ROOT))]
    s=donor.read_text().replace('_kc7','_kc7_split')
    s=s.replace('parameter integer OPT_KC7 = 0,','parameter integer OPT_KC7 = 0,\n    parameter integer OPT_SPLIT_CMP = 0,')
    s=s.replace('.OPT_KC7(OPT_KC7),','.OPT_KC7(OPT_KC7), .OPT_SPLIT_CMP(OPT_SPLIT_CMP),')
    s=once(s,'    reg [WB-1:0]   cmp;                     // registered completion: adm_q && &cpart', '''    reg [WB-1:0] cmp_base;
    (* keep = 1 *) reg [WB-1:0] cmp_lo, cmp_hi;
    wire [WB-1:0] cmp = OPT_SPLIT_CMP ? (cmp_lo & cmp_hi) : cmp_base;
    // Two PARALLEL kept comparison banks. Same edge, no added stage.
    // Both carry the same adm_q mask and reset0; invalid cpart cannot escape.''')
    s=once(s,'cmp <= 0;', '''if (OPT_SPLIT_CMP) begin cmp_lo <= 0; cmp_hi <= 0; end
            else cmp_base <= 0;''')
    s=once(s,'                cmp[e] <= adm_q[e] && &cpart[e];', '''                if (OPT_SPLIT_CMP) begin
                    cmp_lo[e] <= adm_q[e] && &cpart[e][3:0];
                    cmp_hi[e] <= adm_q[e] && &cpart[e][7:4];
                end else cmp_base[e] <= adm_q[e] && &cpart[e];''')
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'ot_hdc_v41x_idx_kgather_kc7_split.sv').write_text(s)
    for name in ['ot_hdc_v41x_idx_kgctl_kc7_ctx.sv','tb_hdc_v41x_idx_kgather_kc7.sv']:
        t=(BASE/name).read_text().replace('_kc7','_kc7_split')
        t=t.replace('parameter integer OPT_KC7 = 0,','parameter integer OPT_KC7 = 0,\n    parameter integer OPT_SPLIT_CMP = 0,')
        t=t.replace('.OPT_KC7(OPT_KC7),','.OPT_KC7(OPT_KC7), .OPT_SPLIT_CMP(OPT_SPLIT_CMP),')
        (OUT/name.replace('_kc7','_kc7_split')).write_text(t)
    paths=[donor,ROOT/'tools/dsrom_reindex_kc7_split_emit.py',*sorted(OUT.glob('*.sv'))]
    (ROOT/'results/uarch/dsrom_reindex_parallel_20261005/source_manifest.json').write_text(json.dumps({str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},indent=2)+'\n')
if __name__=='__main__':emit()
