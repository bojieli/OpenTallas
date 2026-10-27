"""Zero-cycle kit-only ES ownership copies for geographically separate consumers."""
from pathlib import Path

def transform(text, mutant=False):
    old = "    reg own;\n    always @(posedge ck or negedge rs_q) if (!rs_q) own <= 1'b1; else own <= !emb_boot_ready;"
    new = """    // Same next-state/reset, independently retained for three consumer regions.
    (* keep *) reg own;
    (* keep *) reg own_face;
    (* keep *) reg own_emb;
    always @(posedge ck or negedge rs_q) if (!rs_q) begin
        own <= 1'b1; own_face <= 1'b1; own_emb <= 1'b1;
    end else begin
        own <= !emb_boot_ready; own_face <= !emb_boot_ready;
        own_emb <= !emb_boot_ready;
    end"""
    assert text.count(old) == 1, "ES ownership source changed"
    text = text.replace(old, new)
    text = text.replace("wire [260:0] er_e = (own &&", "wire [260:0] er_e = (own_emb &&")
    text = text.replace("wire sl = own ||", "wire sl = own_face ||")
    for n in ["her[0]", "her[259]", "her[260]"]:
        text = text.replace(n + " <= own &&", n + " <= own_face &&")
    if mutant:
        text = text.replace("own_face <= !emb_boot_ready;", "own_face <= emb_boot_ready;")
    return text

def apply_kit(rtl_dir, mutant=False):
    p=Path(rtl_dir)/"qkd_static_kv_pc_es_merge_b.sv"
    p.write_text(transform(p.read_text(), mutant))
