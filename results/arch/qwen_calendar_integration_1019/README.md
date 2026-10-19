Finite calendar integration is opt-in CALENDAR_ROM=0 by default. The actual
cal_mu now reads two native266-bit ROMs, accounts for one additional capture
edge through in-flight FIFO state, accepts CALR10 counts, and retains exact
scheduled output edges. Legacy CALD9 and TLOAD paths remain the default.
The immutable path rejects old TLOAD commands; native table loading is separate.

The fresh source lowerer emits406decode commands,320head commands,64embedding
commands, plus3 source-extracted cap0 token-start commands. The aligned image,
one BOOT command and67-entry INIT copy total867 entries/217 rows. INIT replaces
only the ordinary AMAX emit by NOP and exports FIRST800/CNT67 for this image.
Those values are an image receipt, not production CTLM parameters.
The prior390decode/774body summary is not the count for this exact lowerer.

Native5.050 playback through actual cal_mu passes3920 exact output events with
fault=0. MUT1 shifts issue edges and fails3920 comparisons; MUT11 changes user
ownership and fails3904. BOOT SETID and DONE are also checked. This tests command
playback; it does not execute numerical engines or qualify a whole token.

Source body parameters embed/head word0=300 are explicitly diagnostic. Public
cap0 prefix is hash-pinned (canonical DW5/6 mask0/tag4D43), not a production
cap1 manifest. Phase source is unbound; head/finalnorm payload is absent.
BOUNDARY_RELOC remains0. Physical source, clock, preload/lifetime joins and
actual production receiver/body installation remain open.

All four users play all four segments on exact edges; count1024 and invalid explicit ranges reject. Legacy NU1 lockstep/NU4 regression passes with zero mismatches and1536 landed words.
