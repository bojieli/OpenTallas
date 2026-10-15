import assert from 'node:assert/strict';
import { normalizeDataflow, connectionLabel, formatRate, filterConnections, connectionSegments } from '../../dataflow.js';
const d = normalizeDataflow({ connections: [
  { id: 'shared', src: 'a', dst: 'b', width_bits: 512, bytes: 1024, endpoints: [{instance:'a'}, {instance:'b'}, {instance:'c'}] },
  { id: 'mapped', src: 'a', dst: 'b', src_node: 'op1', dst_node: 'op2', width_bits: 32, required_bps: 0, direction: 'forward', critical: true },
  { id: 'unknown', width_bits: null }, { id: 'invalid', width_bits: -2, capacity_bps: '200' },
] });
assert.equal(d.edges[0].direction, 'unknown', 'endpoint list must not imply a producer');
assert.equal(d.edges[0].capacity_bps, null, 'width and transfer size must not imply bandwidth');
assert.equal(connectionLabel(d.edges[2]), 'width unknown');
assert.equal(d.edges[3].width_bits, null);
assert.equal(d.edges[3].capacity_bps, null);
assert.equal(formatRate(0), '0 b/s'); assert.equal(formatRate(null), 'unknown');
assert.equal(d.coverage.token_mapped, 1);
assert.deepEqual(filterConnections(d.edges, {mode:'current',activeNodes:['op1']}).map(e=>e.id), ['mapped']);
assert.deepEqual(filterConnections(d.edges, {mode:'selected',selected:'a'}), [], 'physical instance name is not token mapping');
const inst = ['a','b','c'].map((name,i)=>({name,x:i*20,y:0,w:10,h:10}));
assert.equal(connectionSegments(d.edges[0], inst).length, 2, 'retain every hypernet endpoint');
assert.ok(connectionSegments(d.edges[0], inst).every(s=>!s.directed&&!s.pin_located));
assert.equal(connectionSegments(d.edges[1], inst)[0].directed, true);
assert.equal(connectionSegments(d.edges[2], inst).length, 0, 'unknown endpoint must not appear at origin');
console.log('Dataflow semantics: PASS');
