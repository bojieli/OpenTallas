Native HCOL regional input boundary repair (PREP)

Original native q_b[567:0], key[543:0] and qv_b feed capture flops in BOTH g_rgn branches, on different clk_pair inputs. This accounts for all1113 ordinary face_guard shared-input failures. Combining those capture flops would change the clock semantics. The additive master instead exposes two independently captured copies of each broadcast input. Existing source and production bindings are unchanged.

No arithmetic, control, reset, state count or cycle count changes; reversing just the module name, three declarations and three capture expressions reproduces the donor body byte for byte. Parent wiring duplicates the original query/key buses at the physical boundary. Pin count1216→2329; an explicit capacity/fanout/clock/reset/parent event is required before GEN/P&R. No route or STA has been launched.
