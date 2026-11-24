/*
 * 지표 DB 지도용 아프리카 국경 데이터 생성 (수동 1회 실행, Node.js)
 *   npm i world-atlas@2 topojson-client@3
 *   node scripts/manual/build_africa_map.js
 * → assets/africa_map.json  ({viewBox, countries: {ISO3: {d, cx, cy, small}}, extra})
 * 원자료: Natural Earth 1:50m (public domain), world-atlas 패키지 경유.
 * Somaliland는 국제 통계 관행에 따라 Somalia(SOM)에 합쳐 그린다. 서사하라(ESH)는 회색 배경으로만 그린다.
 */
const path = require('path');
const fs = require('fs');
const topo = require('world-atlas/countries-50m.json');
const { feature } = require('topojson-client');

const NUM2ISO = {
  '012':'DZA','024':'AGO','204':'BEN','072':'BWA','854':'BFA','108':'BDI','132':'CPV','120':'CMR','140':'CAF',
  '148':'TCD','174':'COM','178':'COG','180':'COD','384':'CIV','262':'DJI','818':'EGY','226':'GNQ','232':'ERI',
  '748':'SWZ','231':'ETH','266':'GAB','270':'GMB','288':'GHA','324':'GIN','624':'GNB','404':'KEN','426':'LSO',
  '430':'LBR','434':'LBY','450':'MDG','454':'MWI','466':'MLI','478':'MRT','480':'MUS','504':'MAR','508':'MOZ',
  '516':'NAM','562':'NER','566':'NGA','646':'RWA','678':'STP','686':'SEN','690':'SYC','694':'SLE','706':'SOM',
  '710':'ZAF','728':'SSD','729':'SDN','834':'TZA','768':'TGO','788':'TUN','800':'UGA','894':'ZMB','716':'ZWE',
};
const W = 600, LON0 = -26, LON1 = 64, LAT0 = -36, LAT1 = 38.5;
const k = Math.cos(1 * Math.PI / 180);           // 적도 부근이라 거의 1
const sx = W / ((LON1 - LON0) * k);
const H = Math.round((LAT1 - LAT0) * sx);
const proj = ([lon, lat]) => [((lon - LON0) * k * sx), ((LAT1 - lat) * sx)];

function ringPath(ring) {
  let d = '', last = null, n = 0;
  for (const p of ring) {
    const [x, y] = proj(p).map(v => Math.round(v * 2) / 2);
    if (last && last[0] === x && last[1] === y) continue;
    d += (n === 0 ? 'M' : 'L') + x + ' ' + y; last = [x, y]; n++;
  }
  return n > 2 ? d + 'Z' : '';
}
function geomPath(g) {
  const polys = g.type === 'Polygon' ? [g.coordinates] : g.type === 'MultiPolygon' ? g.coordinates : [];
  return polys.map(poly => poly.map(ringPath).join('')).join('');
}
function bbox(g) {
  const polys = g.type === 'Polygon' ? [g.coordinates] : g.coordinates;
  let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9, big = null, bigA = -1;
  for (const poly of polys) {
    let a0 = 1e9, b0 = 1e9, a1 = -1e9, b1 = -1e9;
    for (const p of poly[0]) { const [x, y] = proj(p); a0 = Math.min(a0, x); b0 = Math.min(b0, y); a1 = Math.max(a1, x); b1 = Math.max(b1, y); }
    x0 = Math.min(x0, a0); y0 = Math.min(y0, b0); x1 = Math.max(x1, a1); y1 = Math.max(y1, b1);
    const area = (a1 - a0) * (b1 - b0);
    if (area > bigA) { bigA = area; big = [(a0 + a1) / 2, (b0 + b1) / 2]; }
  }
  return { w: x1 - x0, h: y1 - y0, c: big };
}

const fc = feature(topo, topo.objects.countries);
const out = { viewBox: `0 0 ${W} ${H}`, source: 'Natural Earth 1:50m (public domain) via world-atlas', countries: {}, extra: {} };
for (const f of fc.features) {
  let iso = NUM2ISO[f.id];
  if (!iso && f.properties.name === 'Somaliland') iso = 'SOM';
  if (f.id === '732') { out.extra.ESH = geomPath(f.geometry); continue; }
  if (!iso) continue;
  const d = geomPath(f.geometry), b = bbox(f.geometry);
  const prev = out.countries[iso];
  if (prev) { prev.d += d; continue; }   // Somaliland → Somalia
  out.countries[iso] = { d, cx: Math.round(b.c[0] * 10) / 10, cy: Math.round(b.c[1] * 10) / 10,
                         small: ['CPV','STP','COM','MUS','SYC'].includes(iso) };   // 섬나라는 화면에서 원으로 보강
}
const dest = path.join(__dirname, '..', '..', 'assets', 'africa_map.json');
fs.writeFileSync(dest, JSON.stringify(out));
console.log('✔', dest, Object.keys(out.countries).length, 'countries,', (fs.statSync(dest).size / 1024).toFixed(0), 'KB',
            'small:', Object.entries(out.countries).filter(([, v]) => v.small).map(([k]) => k).join(','));
