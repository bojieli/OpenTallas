# Actual default-off identity

Both actual canonical GEN modes PASS with PYTHONHASHSEED=0. Original and TLD-source default-off output RTL, all lane records, parameters, relay stages, LEFs, SDCs and pin JSON files are byte-identical. Of 339 compared files, 336 are byte-identical. The three raw differences are retained explicitly: manifest producer source path; pin_align_rows.json.gz header (decompressed bytes identical); relay_run.json runtime, source-path traceback and split_compute source provenance. This is emitted hardware identity, not blanket byte identity of every run/provenance report.

Actual normal16GB run gold1 oth-ubuntu-216708-1792733303 terminal exit0. Original outputs preserved at /srv/opentallas-scratch/claude/codex-tld-gen-deterministic-1022/{base_off,tld_off}. The earlier uncontrolled-hash-seed pair is preserved separately and did not establish identity.
