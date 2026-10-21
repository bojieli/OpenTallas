KV group s3/s4 mapped native census, 2026-10-20 00:38 PT
All six legacy gates remain active. This is source-synthesis census, not terminal gate results.
Every non-clock, non-constant root counted through BUF/INV trees with the gate snapshot textbook_lint parser. Every root is scanned; threshold32, no reset waiver.
Six source-pinned netlist hashes and exact parser hashes are in native_census.json.
All six FAIL: maximum399 loads; 256 violating roots per tile. No variant may submit under the23:46 rule, even on WARN.
Source redesign must include PC checker select/ticket copies, hop regional reset copies, calendar/phase/drain resets and control copies, HBM boot resets, rowctl request valid copies, and combinational decode roots. Existing s4 response exits are retained.
No source or clock constraints modified; live gates and old verdicts preserved.
