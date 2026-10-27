"""Opt-in one-edge boot phase delivery from the input band to the core centre."""
from pathlib import Path
def transform(text, mutant=False):
    old="    reg own;\n    always @(posedge ck or negedge rs_q) if (!rs_q) own <= 1'b1; else own <= !emb_boot_ready;"
    new="""    // N-face input capture remains local; the second phase register is
    // constrained to the clear centre band by kvspc_phase_delivery.tcl.
    (* keep *) reg own_pin;
    (* keep *) reg own;
    always @(posedge ck or negedge rs_q)
        if (!rs_q) own_pin <= 1'b1; else own_pin <= !emb_boot_ready;
    always @(posedge ck or negedge rs_q)
        if (!rs_q) own <= 1'b1; else own <= own_pin;"""
    assert text.count(old)==1, "ES ownership source changed"
    if mutant:new=new.replace("else own <= own_pin;","else own <= !emb_boot_ready;")
    return text.replace(old,new)
def apply_kit(rtl_dir, mutant=False):
    p=Path(rtl_dir)/"qkd_static_kv_pc_es_merge_b.sv"
    p.write_text(transform(p.read_text(),mutant))
