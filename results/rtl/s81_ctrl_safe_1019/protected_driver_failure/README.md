# Protected input-hold CTS failure

Source `7a5c1bc93` retains every HB/port/link protection and protects the 1,243 enumerated BUFx4f forward drivers. The exact saved-ODB census and negative guard tests pass, but actual CTS repeats ODB-0373 on protected net ot_inhold_n00001. Gate result and PNG are preserved at `physical/ref_tile/s81ctrl_rg2_sram` in commit `4d703fda7`.

A separate checkpoint-copy diagnostic loads the same actual 3_5 ODB and changes setup repair only to skip buffer removal. It confirms net=1 and driver=1 protection and executes the sequence SizeUpMove, SwapPinsMove, BufferMove, CloneMove, SplitLoadMove. The same ODB-0373 occurs before the first successful repair iteration. Thus skipping UnbufferMove does not fix the issue. Original frozen snapshot is read-only; hold repair, margins, uncertainty and STA checks remain unchanged. This diagnostic is not a production policy or timing qualification.
