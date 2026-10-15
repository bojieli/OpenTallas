Full released HC checkpoint image export
========================================

The exporter stages exact F32 tensor byte ranges from 40 backbone and 3 MTP layers, both HC attn/ffn tensors. It streams all 2064 rows (169082880 bytes) into the actual 4b9 Lower.hc_row_load descriptor order at local byte address 20 GiB. Eight 10240-byte bank segments per row are scattered onto stack k%4.

The positive verifier compares every payload row and all 16512 physical bank segments against staged checkpoint bits, checks descriptor provenance and complete image hashes. The negative fixture flips the final byte and observes rejection at ordinal2063. Export peak RSS was41940 KiB; remote disk retained479366262784 bytes, above the required1 GiB headroom.

Image files and logs remain under the remote directory recorded in receipt.json. rows.jsonl.gz is the complete reproducible scatter manifest; its uncompressed SHA is in manifest.json. input_catalog.json records every tensor, checkpoint shard offset and SHA. The payload and four sparse physical windows are too large for source control; manifest.json records exact hashes.

This gate proves exported image preparation. Hardware installation, loader ACK and whole-chip qualification remain false. The actual native controller component and parent434-SRAM composition are separate proofs.
