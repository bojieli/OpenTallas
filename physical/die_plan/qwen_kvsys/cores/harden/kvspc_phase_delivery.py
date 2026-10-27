"""Opt-in one-edge boot phase delivery from the input band to the core centre.

nface_ff (TOK-ALL-14, optional hardening, 0 data/token/boot cycles, +1 FF): register (wes[0] && own_pin) at the N
face and OR it into m_fault on the next edge, so a writer word at REOPEN+1 (own still run phase that edge) is flagged
exactly as on main.  Fault report latency for that one case is +1 edge; no data, select or steering path changes.
"""
from pathlib import Path
def transform(text, mutant=False, nface_ff=False):
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
    text=text.replace(old,new)
    if nface_ff:
        old2="            if (wes[0] && own) m_fault <= 1'b1;\n"
        assert text.count(old2)==1, "ES writer-in-boot fault source changed"
        text=text.replace("    reg m_fault;\n","    reg m_fault;\n    // N-face writer-in-boot fault copy against own_pin (+1 FF, fault report +1 edge, 0 data edges)\n"
                          "    (* keep *) reg wpin_f;\n    always @(posedge ck or negedge rs_q) if (!rs_q) wpin_f <= 1'b0; else wpin_f <= wes[0] && own_pin;\n",1)
        text=text.replace(old2,old2+"            if (wpin_f) m_fault <= 1'b1;\n")
    return text
def apply_kit(rtl_dir, mutant=False, nface_ff=False):
    p=Path(rtl_dir)/"qkd_static_kv_pc_es_merge_b.sv"
    p.write_text(transform(p.read_text(),mutant,nface_ff))
