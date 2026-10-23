# TX y structural region landing replacement

The preserved y route dcd37342d failed setup: parent u_pim0/lv[13] through the lookup-address cone to hard ga/ra[6], raw -502.89 ps, normalized -439.559 ps, 782 endpoints, TNS -94703.41 ps. Parent launch clock 1120.91 ps versus hard ga clock 355.45 ps creates about 765 ps adverse boundary skew. Write m_wd to ga also has adverse clock skew; a read-only RIC change cannot fix the complete interface.

The default-off RING variant carries all 300 input bits per column (re/ra, we/wa/wd, and wm_next) through fixed calendar rings, and all 256 output bits back through separate return rings. Column clocks are internal kept unary branches of the existing ck port. External TX ports remain unchanged. All existing functionality remains present. No old routed receipt qualifies this source.

MAIN uses D=4,K=2: three input plus three return edges, six added lookup edges, reference LPX=8 (prior y LPX=2). ALT uses D=8,K=3: four plus four, eight added lookup edges, LPX=10. Both columns have equal latency; read/write/mask ordering moves together. No calendar adoption until actual physical closure and compiler/die integration. The external clocks and operating period remain frozen.

MAIN ring data storage: 2*(4+1)*(300+256)=5560 bits distributed among narrow ring slices; ALT 10008 bits. Each individual slice stores at most128 bits, below2kb. MAIN slices <=16 bits; ALT <=8 bits keeps the first eight-way mux select to <=32 actual data loads. Reset relays are hierarchical when the slice count exceeds30. The RING-only TX reset forest has nine same-edge leaves (default remains seven): one new leaf owns the longer lookup-valid pipe and one owns the ring reset entry. Their release edge is unchanged; this avoids adding both the lookup valids and six ring-entry reset sinks to the former24-load leaf. No data reset. Both variants retain two existing IDX SRAM macros, all eight score SRAMs (five inside hard ga), all transaction fields, and all output logic.

Safe design checklist before native/layout admission:

1. Ports: fixed external boundary retained; all newly regional data crosses fixed-latency rings. PASS by source construction, exact port check pending receipt.
2. Reach: rings and corresponding hard/soft bank group must share local boundary bands; physical topology lane owns exact placement. OPEN until native placement.
3. Fanout: narrow kept slice hierarchy and parameter IDs; mapped native maximum32 required before layout. OPEN until census.
4. Depth: read address cone terminates at input-ring capture; local ring slices have 4/8-way muxes on <=16/8 data bits. Mapped/CTS timing remains OPEN.
5. Storage: each ring slice <=128 bits, all production score/IDX storage remains SRAM. PASS source inventory.
6. Floorplan: inherited SRAM/ga bodies remain fixed; local ring bands must be sized from synthesis area. OPEN until area/native result.
7. Clock: one external ck, internal kept ga/gb branches. Physical regional subtree helper requires ROOT validation. No false-path or setup/hold relaxation. OPEN.
8. Schedule: MAIN+6 and ALT+8 lookup edges explicitly priced above; defaults off. DIE/TOK informed through steward; adoption remains OPEN.

MUT=7 omits real rings while keeping the priced consumer lookup pipe. It must produce an actual TX_MISMATCH witness. Existing mask/bank mutants remain available. The small phase bench exercises the slot mechanism at phase0,+0.9T,-0.4T and two reset epochs; it does not qualify full tile clocks or reset station placement.

Clock-local reset repair (source6): source pointer reset releases only on src_ck; read pointer/warm reset releases only on dst_ck. Each local group has two asynchronously cleared synchronizer flops; the first stage asynchronously asserts at most19 relay leaves and the second releases them, preserving three local release edges. The shared reset therefore drives at most8 reset pins and no source pointer is released by a destination-clock register. Actual full TX phase runs, not just a direct slice, cover phase0,0.1T,0.9T with two reset epochs. The sim-only phase branch transports every edge using delayed nonblocking assignment; the earlier delayed continuous assignment filtered the0.9T clock pulses and is retained as a harness failure. Production still contains only the kept BUFx24 branch.
