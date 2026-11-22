const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const test = require('node:test');
const context = vm.createContext({});
vm.runInContext(fs.readFileSync('eon/ui/hybrid.js','utf8'), context);
const png = Buffer.from('89504e470d0a1a0a0000000d4948445200000030000000300806000000','hex');

test('icon headers must match MIME and dimension bounds are visible before decoding',()=>{
  assert.deepEqual(Array.from(context.iconDimensions(png,'image/png')),[48,48]);
  assert.equal(context.iconDimensions(png,'image/jpeg'),null);
  assert.equal(context.iconDimensions(Buffer.from('<svg></svg>'),'image/png'),null);
  const large=Buffer.from(png);
  large.writeUInt32BE(30000,16);
  assert.ok(context.iconDimensions(large,'image/png')[0]>1024);
});

test('animated PNG and multi-image ICO are rejected',()=>{
  const animated=Buffer.concat([png,Buffer.alloc(16)]);
  animated.write('acTL',37);
  assert.equal(context.iconDimensions(animated,'image/png'),null);
  const ico=Buffer.alloc(30);
  ico.writeUInt32BE(256);ico.writeUInt16LE(2,4);
  assert.equal(context.iconDimensions(ico,'image/x-icon'),null);
});
