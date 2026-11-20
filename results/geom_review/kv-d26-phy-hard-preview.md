# KV D26 PHY hard-wrapper reset preview

The routed control path in the preview stays in the open region east of the signed PHY macro. Its two added relay sites are [548.213, 760.32] and [440.16, 574.187] µm. The second site is 5.813 µm from the existing first writer site. The three upstream legs are 294.187, 294.186 and 294.187 µm. Existing writer and FSTART consumer positions are preserved.

The private RTL preview replaces only the existing raw relay input with a two-relay prefix. The three original writer and FSTART raw consumers keep their connections. The bound relay primitive readback confirms the raw release changes from one to three edges. The exact D26 emitter, boot calendar, and mapped placement remain open.

Image SHA-256 18f37699bf7959502fe55b85f98de1afcb0d04ecf005f57dd68404dab1fb6bb7.
