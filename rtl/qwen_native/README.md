# Static Qwen embedding ROM provider

`ot_qwen_embedding_static_provider` is a new, unqualified static provider; it
preserves the historical credit based bank and gateway RTL. It instantiates the
complete 151936 x 4096 W8 code inventory and one BF16 scale per vocabulary row:
2374 code banks, two real `ot_rom_4096x266_m8` macros per bank, and three packed
scale macros. Macro spare bits do not carry payload or ECC.

The physical macro simulation model loads `+OT_ROM_DIR` using immutable INSTANCE
identities `qembed_code_b0_c0` through `qembed_code_b2373_c1` and
`qembed_scale_b0` through `qembed_scale_b2`. Every bank explicitly rejects missing
files at initialization. The released image producer is owned by native memories;
no generated hash fixture or C++ memory backs this provider.

The input is `{i_v,i_kind,i_addr}`. Kind zero addresses global 512 bit code words
`token*64+chunk`; kind one addresses scale token rows. Response is
`{o_v,o_kind,o_addr,o_data}`; scale uses only low 16 bits. Invalid addresses or
consecutive requests set sticky `fault`. These checks never reschedule a request.
The compiler must reserve an idle edge between reads. Payload is defined only
with valid; faults invalidate qualification of the program.

An input sampled at edge E traverses twelve request tree stages, a bank input
register, the real synchronous macro, the two-edge macro capture, and the bank
output register, then twelve gather tree stages. Its response appears at E+28.
The bank alone responds at E+4. `tools/qwen_embedding_static_schedule.py` emits
65 fixed reservations per row (scale, then 64 code chunks), with responses at
cycles 28 through 156 relative to the first issue. Expansion arithmetic and VM
write visibility are separate consumer obligations, not supplied by the compiler.

The recursive binary tree pads to 4096 leaves and registers every branch and
gather. At most one response arrives at any gather in a valid static program;
a collision faults. Bank0/1 and scale0/1 subtree tests exercise the identical
routing primitive with the real macro model and actual image expectations,
including complete code rows on the token63/64 bank boundary. A passing subtree
is a component result, not all-vocabulary or full-token native qualification.
The image producer runs separate full inventory bank cohorts.

4751 macros occupy 36.4114 mm2 before routing or logic; 60% occupancy requires at
least 60.6857 mm2 before the tree's roughly 2.5 million pipeline flops and die
corridors are added. The current KV die owner reports that the selected embedding
boot path initializes off-chip HBM, and that this resident ROM has no authoritative
floorplan slot, TP8 ownership partition, or native clock phase assignment. This
provider therefore must not be substituted silently into that boot format or
presented as a closed or die-bound component. Physical jobs require an explicit
home region, cut analysis, pin contract and clock family from the die lead.
