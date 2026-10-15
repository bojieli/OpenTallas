This publishes source-bound component ports and a candidate recipient map,
not existing die wiring. The old die has no demonstrated tile-ID straps and
no adopted 32-root/phase cache fill protocol. Expected profiles imply6 QKV,
12 O/down or24 GU recipients per root/phase. An ACK must cover them all.

The current cache lacks instruction/version tags and registered accepted-load,
response-capture or epoch-quiescent outputs. The JSON marks these absent rather
than inventing an ACK from load_v or cache_hit. Resolving the opaque dictionary
token does not make overlapping instruction cache entries safe. Add context
banking/retirement or prove and price a drain before reusing current tags.
Any registered request/status return must declare its actual latency, related
clock phase family, coherent pause/lookahead and source freshness contract.
The local arithmetic fixtures do not establish those global obligations.
