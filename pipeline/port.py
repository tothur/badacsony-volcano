import re
import os
HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, '..', '..', 'borzsony', 'index.html')).read()
s = src
def rep(a, b, count=1):
    global s
    assert a in s, 'MISSING: ' + a[:90]
    s = s.replace(a, b) if count == 0 else s.replace(a, b, count)
def cut(a, b, new):
    global s
    i = s.index(a); j = s.index(b, i)
    s = s[:i] + new + s[j:]

# ---------- page text ----------
rep('<title>Börzsöny Time Machine</title>', '<title>Badacsony Time Machine</title>')
rep('aria-label="3D view of the Börzsöny Mountains"', 'aria-label="3D view of Badacsony and the Tapolca Basin"')
rep('<div class="eyebrow">High Börzsöny · North Hungary</div>', '<div class="eyebrow">Badacsony · Balaton Uplands</div>')
cut('<span class="long">', '</span>', '<span class="long">Speculative reconstruction. Today\'s terrain and imagery are real. The maar, tuff ring, cinder cone and lava lake are modelled from the outline of today\'s basalt cap; the age (about 3.5 million years) and the eruption sequence are simplified, and fine detail below the data resolution is generated.')
cut('        <option value="overview">Overview</option>', '      </select>', '''        <option value="overview">Overview</option>
        <option value="summit">Badacsony crater</option>
        <option value="eruption">Eruption view</option>
        <option value="lake">Lava lake close-up</option>
        <option value="hills">Witness hills</option>
        <option value="walk">Walk the tuff ring</option>
''')

# ---------- data ----------
rep("let loaded = 0; const toLoad = SMALL ? 5 : 12;", "let loaded = 0; const toLoad = SMALL ? 6 : 9;")
cut("const hiLoad = SMALL", "const Q = v =>", """const hiRaw = null;
const loads = [
  fetch('data/meta.json', { cache: 'no-store' }).then(r => r.json()).then(m => (tick(), m)),
  loadPng16('data/d2048.png'),
  loadPng16('data/aux1024.png'),
  new THREE.TextureLoader().loadAsync('data/sat.jpg').then(t => (tick(), t)),
  loadPng16('data/shape2048.png'),
  ...(SMALL ? [loadPng16('data/k2048.png')] : ['00', '01', '10', '11'].map(k => loadPng16(`data/k4096_${k}.png`))),
];
const [META, dRaw, auxRaw, satTex, shRaw, ...pRaw] = await Promise.all(loads)
  .catch(err => { $('loading').textContent = 'Could not load the terrain data. Reload the page to try again.'; throw err; });
""")
rep("const NA = 1024, AUX", """// shape layers at 2048: ring, bowl, cone, older rings | crater, ash blanket, older lava fills, valleys
const SN = 2048, SNN = SN * SN, SF = new Float32Array(SNN * 8), s1h = new Uint16Array(SNN * 4), s2h = new Uint16Array(SNN * 4);
for (let k = 0; k < 8; k++) { const [lo, hi] = META.shapeRanges[k];
  for (let i = 0; i < SNN; i++) { const v = lo + shRaw.data[k * SNN + i] / 65535 * (hi - lo); SF[i * 8 + k] = v; (k < 4 ? s1h : s2h)[i * 4 + (k & 3)] = THREE.DataUtils.toHalfFloat(v); } }
const mkH = a => { const t = new THREE.DataTexture(a, SN, SN, THREE.RGBAFormat, THREE.HalfFloatType); t.magFilter = t.minFilter = THREE.LinearFilter; t.needsUpdate = true; return t; };
const tS1 = mkH(s1h), tS2 = mkH(s2h);
const NA = 1024, AUX""")
rep("const DOME = { x: CX + 90, z: CZ - 60 };", "const DOME = { x: CX, z: CZ };                 // the vent\nconst BAD = META.bad;")

# ---------- timeline ----------
cut("const P1 = 0.06, P2 = 0.30, P3 = 0.60, TA = 14.3;", "// ---------- CPU height ----------", """const P1 = 0.03, P2 = 0.06, P3 = 0.58, TA = 3.5;
function state(p) {
  const st = { grow: 1 };
  if (p < P2) Object.assign(st, { phase: 'before', t: TA, u: 0 });
  else if (p <= P3) { const u = (p - P2) / (P3 - P2); Object.assign(st, { u, t: TA, phase: u < 0.3 ? 'maar' : u < 0.6 ? 'fountain' : u < 0.84 ? 'lake' : 'cooling' }); }
  else { const k = (p - P3) / (1 - P3), t = TA * (1 - k); Object.assign(st, { t, u: 1, phase: t < 0.06 ? 'today' : 'erosion' }); }
  const u = st.u;
  st.ring = smooth(0.0, 0.26, u); st.cone = smooth(0.3, 0.6, u); st.fill = smooth(0.34, 0.72, u);
  st.hot = u < 0.32 ? 0 : u < 0.84 ? smooth(0.32, 0.38, u) : 1 - 0.92 * smooth(0.84, 1.0, u);
  st.s = (st.phase === 'erosion' || st.phase === 'today') ? st.t / TA : 1;
  if (st.s < 1) st.hot = 0;
  st.lvl = META.floor + (BAD.L - META.floor) * st.fill;
  st.water = st.t < 0.06 ? META.water : -1000;
  st.cw = smooth(0.02, 0.22, st.s); st.fresh = smooth(0.94, 1.0, st.s);
  return st;
}
const STAGES = {
  before: ['Before the eruption', 'No Lake Balaton yet. A plain of sand and clay left by Lake Pannon lies roughly 250 m above today\\u2019s shore, cut by stream valleys, and its sands are soaked with groundwater. Szent György-hegy, Gulács and Csobánc have already erupted.'],
  maar: ['Maar explosions', 'Rising basalt magma meets the wet sands. The water flashes to steam and blasts a crater down into the sediment. Black jets of tephra shoot up, and ground-hugging base surges pile layered ash into a tuff ring.'],
  fountain: ['Lava fountains', 'Once the groundwater near the vent is used up, the eruption turns dry. Fountains of glowing lava build a cinder cone, and molten basalt starts to pond inside the crater.'],
  lake: ['A lava lake', 'Fluid basalt fills the crater almost to the rim of the tuff ring. Its surface is a black skin of crust that keeps tearing apart along glowing seams as the lava underneath churns. Switch to Night to see it best.'],
  cooling: ['The lake freezes', 'The eruption stops. The lake cools from the top and sides over years to decades and shrinks into the tall basalt columns still visible on Badacsony\\u2019s flanks.'],
  erosion: ['Erosion turns the land inside out', 'Streams strip away the soft sediment far faster than the hard basalt. The tuff ring goes first. The lava-lake fill stays put while the land around it drops, until the old crater stands as a hill.'],
  today: ['Badacsony today', 'The flat-topped hill is the old crater fill, now 437 m high. Lake Balaton formed only in the last few tens of thousands of years, at the foot of a hill that started as a hole in the ground.'],
};
const maAt = t => P3 + (TA - t) / TA * (1 - P3);
const TICKS = [
  ['Before', 0], ['Maar', P2 + 0.13 * (P3 - P2)], ['Fountains', P2 + 0.45 * (P3 - P2)], ['Lava lake', P2 + 0.72 * (P3 - P2)], ['Cooling', P2 + 0.92 * (P3 - P2), 'minor'],
  ['3 Ma', maAt(3), 'minor'], ['2 Ma', maAt(2), 'minor'], ['1 Ma', maAt(1), 'minor'], ['Today', 1],
];

""")

# ---------- CPU height ----------
cut("function heightAt(x, z) {", "// ---------- renderer ----------", """function shAt(ch, x, z) {
  const fx = clamp((x + HALF) / SIZE, 0, 1) * (SN - 1), fz = clamp((z + HALF) / SIZE, 0, 1) * (SN - 1);
  const x0 = Math.min(fx | 0, SN - 2), z0 = Math.min(fz | 0, SN - 2), u = fx - x0, v = fz - z0, i = (z0 * SN + x0) * 8 + ch;
  return mix(mix(SF[i], SF[i + 8], u), mix(SF[i + SN * 8], SF[i + SN * 8 + 8], u), v);
}
// same surface as the shader: plain + maar (ring, bowl) + lava lake + cinder cone, then erosion toward today
function heightAt(x, z) {
  const d = bil(D, ND, x, z), k = bil(PH, NP, x, z), c = auxAt(1, x, z);
  const ring = shAt(0, x, z), bowl = shAt(1, x, z), cone = shAt(2, x, z), ringO = shAt(3, x, z), crater = shAt(4, x, z);
  let h = k + S.ring * (ring - bowl);
  if (crater > 0.5 && S.fill > 0 && h <= S.lvl) h = S.lvl;
  const cn = S.cone * cone; h += cn;
  const ringPart = ringO + S.ring * ring + Math.max(cn, 0), core = h - ringPart, cr = Math.min(c + 0.22, 0.85);
  return d + (core - d) * smooth(c - 0.18, c + 0.18, S.s) + ringPart * smooth(cr - 0.18, cr + 0.18, S.s);
}

""")
rep("camera.position.set(CX - 9500, 4300, CZ + 9500);", "camera.position.set(CX + 3800, 1900, CZ + 5200);")
rep("controls.target.set(CX, 700, CZ);", "controls.target.set(CX - 600, 380, CZ - 1500);")

# ---------- uniforms ----------
rep("  uH10: { value: new THREE.Vector2(H1 ? H1.x0 : 0, H1 ? H1.z0 : 0) }, uH1N: { value: H1 ? H1.N : 1 }, uH1Scale: { value: H1 ? H1.scale : 0 },\n};",
    "  uH10: { value: new THREE.Vector2(H1 ? H1.x0 : 0, H1 ? H1.z0 : 0) }, uH1N: { value: H1 ? H1.N : 1 }, uH1Scale: { value: H1 ? H1.scale : 0 },\n  tS1: { value: tS1 }, tS2: { value: tS2 }, uRing: { value: 0 }, uCone: { value: 0 }, uFill: { value: 0 }, uLvl: { value: 0 },\n};")

# ---------- COMMON ----------
rep("uniform sampler2D tHi; uniform float uHiOn, uHiN, uHiExt; uniform vec2 uHi0;\n",
    "uniform sampler2D tHi; uniform float uHiOn, uHiN, uHiExt; uniform vec2 uHi0;\nuniform sampler2D tS1, tS2; uniform float uRing, uCone, uFill, uLvl;\n")
cut("// vegetation on the active volcano:", "float hash12(vec2 p)", "")
rep("float blockMask(vec2 xz, vec4 aux) { return paleoW(aux) * max(max(smoothstep(1.2, 0.95, domeQ(xz)) * uFresh, aux.b * 0.22 * uFresh), win(xz).z * 0.3); }",
    "float blockMask(vec2 xz, vec4 aux) { return paleoW(aux) * win(xz).z * 0.3; }")
cut("float baseH(vec2 xz, out vec4 aux) {", "// fractal detail below the data resolution", """vec2 suv(vec2 xz) { return (wuv(xz) * 2047.0 + 0.5) / 2048.0; }
// plain + maar (ring, bowl) + lava lake + cinder cone; then erosion toward today. aux.b returns the lava-lake flag
float baseH(vec2 xz, out vec4 aux) {
  vec2 uv = wuv(xz);
  float d = bilF(tD, uv, uND), k = bilF(tP, uv, uNP);
  aux = auxAt(xz);
  vec4 s1 = textureLod(tS1, suv(xz), 0.0); float crater = textureLod(tS2, suv(xz), 0.0).r;
  float h = k + uRing * (s1.r - s1.g);
  float lk = smoothstep(0.45, 0.55, crater) * step(0.001, uFill) * step(h, uLvl);
  h = mix(h, uLvl, lk);
  float cone = uCone * s1.b; h += cone;
  float ringPart = s1.a + uRing * s1.r + max(cone, 0.0), core = h - ringPart;
  float c = aux.g, cr = min(c + 0.22, 0.85);
  aux.b = lk;
  return d + (core - d) * smoothstep(c - 0.18, c + 0.18, uS) + ringPart * smoothstep(cr - 0.18, cr + 0.18, uS);
}
float terrRough(vec2 xz, vec4 aux) {
  float coneW = smoothstep(2200.0, 700.0, length(xz - uCenter)) * uRing;
  return mix(0.55, 1.3, uFresh * coneW) * (1.0 - aux.b);
}
// how much of the 1 m detail (made for the finished eruption) applies yet: ring and cone detail grow with them
float edW(vec2 xz) { vec4 s1 = textureLod(tS1, suv(xz), 0.0); return mix(1.0, uRing, smoothstep(3.0, 15.0, s1.r)) * mix(1.0, uCone, smoothstep(2.0, 10.0, s1.b)); }
// vegetation: the ash blanket and the crater surroundings are stripped; everything else is open Pliocene woodland
float paleoVeg(vec2 xz, float valley, float ridge, vec4 aux) {
  float rN = length(xz - uCenter);
  float n1 = textureLod(tNoise, xz / 2600.0, 0.0).r, n2 = textureLod(tNoise, xz / 420.0, 0.0).r, n3 = textureLod(tNoise, xz / 37.0, 0.0).r;
  float ash = textureLod(tS2, suv(xz), 0.0).g;
  float dist = uFresh * uRing * clamp(max(ash * 1.15, smoothstep(1200.0, 700.0, rN + 250.0 * (n1 - 0.5))) + 0.15 * valley - 0.15 * ridge, 0.0, 1.0);
  float patchV = smoothstep(0.35, 0.65, n2 * 0.6 + n3 * 0.4);
  return clamp(1.0 - dist * 1.2 + (patchV - 0.5) * 0.55, 0.0, 1.0);
}
""")
rep("  vec4 w1 = win(xz) * paleoW(aux);\n", "  vec4 w1 = win(xz) * paleoW(aux) * edW(xz);\n")
rep("    vec4 w0 = win(vW.xz) * paleoW(vAux);", "    vec4 w0 = win(vW.xz) * paleoW(vAux) * edW(vW.xz);")
rep("      float pwf = paleoW(vAux), rx", "      float pwf = paleoW(vAux) * edW(vW.xz), rx")
rep("vec3 lin(vec3 c) { return pow(c, vec3(2.2)); }\n`;", """vec3 lin(vec3 c) { return pow(c, vec3(2.2)); }
// crust plates on the lava lake, drifting and slowly turning with the convection
vec3 lakePlates(vec2 xz) {
  vec2 q = xz - uCenter; float ang = uTime * 0.004 * uHot;
  q = mat2(cos(ang), -sin(ang), sin(ang), cos(ang)) * q + vec2(sin(uTime * 0.03), cos(uTime * 0.023)) * 8.0 * uHot;
  return voro(q / 9.0);
}
`;""")

# ---------- fragment colour ----------
rep("  p = mix(p, lava, uFresh * smoothstep(0.3, 0.6, vAux.b) * (1.0 - smoothstep(0.4, 0.9, veg)) * 0.85);\n", "")
rep("  p = mix(p, debris * 0.85, uFresh * uGrow * smoothstep(0.6, 0.9, vAux.a) * 0.6);\n", "")
cut("  {\n    float dq = domeQ(vW.xz);\n    float dm = uGrow * uFresh", "  {\n    vec2 duv = (vW.xz - uDepXZ) / uDepS;", """  {
    vec4 s1 = texture(tS1, suv(vW.xz)), s2 = texture(tS2, suv(vW.xz));
    // tuff ring: pale yellow-brown palagonitised tuff in thin beds
    float bed = 0.86 + 0.14 * step(0.5, fract(h / 1.8 + n3 * 0.5));
    vec3 tuff = mix(lin(vec3(0.66, 0.58, 0.42)), lin(vec3(0.55, 0.46, 0.32)), n2) * bed * (0.85 + 0.3 * n5);
    p = mix(p, tuff, clamp(uRing * (s1.r - 3.0) / 10.0, 0.0, 1.0) * uFresh * (1.0 - 0.5 * smoothstep(0.5, 0.9, veg)));
    p = mix(p, tuff * 0.95, uRing * s2.g * 0.45 * uFresh * (1.0 - 0.6 * veg));
    // older volcanoes: weathered olive tuff rings, vegetated basalt fills
    p = mix(p, lin(vec3(0.42, 0.40, 0.27)) * (0.85 + 0.3 * n3), clamp(s1.a / 22.0, 0.0, 1.0) * 0.45);
    p = mix(p, mix(lin(vec3(0.24, 0.24, 0.20)), forest, 0.55), s2.b * 0.8);
    // maar floor before the lava arrives: wet grey lapilli and mud
    p = mix(p, lin(vec3(0.33, 0.31, 0.29)) * (0.8 + 0.4 * n4), clamp(uRing * (s1.g - 10.0) / 30.0, 0.0, 1.0) * (1.0 - vAux.b) * uFresh);
    // cinder cone: black and red-brown scoria
    vec3 scoria = mix(lin(vec3(0.13, 0.11, 0.10)), lin(vec3(0.42, 0.18, 0.11)), smoothstep(0.4, 0.8, n2 * 0.5 + n4 * 0.5)) * (0.75 + 0.5 * n5);
    p = mix(p, scoria, clamp(uCone * s1.b / 6.0, 0.0, 1.0) * uFresh);
    // lava lake: glassy black crust plates while molten; once cold, the polygonal tops of basalt columns
    if (vAux.b > 0.01) {
      vec3 pl = lakePlates(vW.xz);
      vec3 crust = mix(lin(vec3(0.06, 0.055, 0.05)), lin(vec3(0.15, 0.145, 0.14)), pl.z) * (0.8 + 0.4 * n4);
      crust *= 1.0 - 0.6 * (1.0 - smoothstep(0.0, 0.12, pl.y));
      vec3 cj = voro(vW.xz / 1.4);
      vec3 cold = mix(lin(vec3(0.20, 0.19, 0.18)), lin(vec3(0.28, 0.27, 0.25)), cj.z) * (1.0 - 0.5 * (1.0 - smoothstep(0.0, 0.08, cj.y)));
      p = mix(p, mix(cold, crust, smoothstep(0.0, 0.3, uHot)), vAux.b);
    }
  }
""")

# ---------- emissive ----------
cut("    float dq = domeQ(vW.xz);\n    float domeM = smoothstep(1.05, 0.9, dq);", "    vec2 duv = (vW.xz - uDepXZ) / uDepS;", """    float fp = length(fwidth(vW.xz));
    if (vAux.b > 0.01 && uHot > 0.0) {
      // molten lava showing through: seams between crust plates, crust-free upwellings, the hot shoreline
      vec3 pl = lakePlates(vW.xz);
      float w1 = 0.06 + fp / 9.0 * 0.8;
      float seam = (1.0 - smoothstep(0.0, w1, pl.y)) * 0.06 / w1 * (0.6 + 0.4 * sin(uTime * 0.8 + pl.z * 30.0));
      float up = smoothstep(0.78, 0.95, texture(tNoise, vW.xz / 45.0 + vec2(uTime * 0.006, uTime * 0.004)).r);
      float shore = 1.0 - smoothstep(0.5, 0.8, texture(tS2, suv(vW.xz)).r);
      float lg = seam + up * 0.9 + shore * 0.5 + 0.02;
      totalEmissiveRadiance += mix(vec3(1.0, 0.15, 0.02), vec3(1.0, 0.5, 0.12), clamp(lg, 0.0, 1.0)) * uHot * vAux.b * lg * 3.5;
    }
    {
      float cn = uCone * texture(tS1, suv(vW.xz)).b;          // throat of the cinder cone while it is erupting
      totalEmissiveRadiance += vec3(1.0, 0.35, 0.06) * uHot * uCone * smoothstep(42.0, 52.0, cn) * 2.5;
    }
""")

# ---------- trees ----------
rep("float dens = mix(presD * 0.95, paleoD * smoothstep(900.0, 1100.0, length(wp - uCenter)) * (1.0 - tw.y) * (1.0 - tw.z), uCW) * step(uWater + 1.5, th);",
    "float dens = mix(presD * 0.95, paleoD * mix(1.0, smoothstep(700.0, 950.0, length(wp - uCenter)), uRing) * (1.0 - aux.b) * (1.0 - tw.y) * (1.0 - tw.z), uCW) * step(uWater + 1.5, th);")

# ---------- state / HUD ----------
cut("function apply(p) {", "// ---------- HUD ----------", """function apply(p) {
  S = state(p);
  U.uGrow.value = 1; U.uS.value = S.s; U.uCW.value = S.cw; U.uFresh.value = S.fresh; U.uHot.value = S.hot; U.uWater.value = S.water;
  U.uRing.value = S.ring; U.uCone.value = S.cone; U.uFill.value = S.fill; U.uLvl.value = S.lvl;
  const PH = ['before', 'maar', 'fountain', 'lake', 'cooling', 'erosion', 'today'], phIdx = PH.indexOf(S.phase);
  if (phIdx < lastPhIdx) resetEruption();
  lastPhIdx = phIdx;
  if (!['maar', 'fountain', 'lake', 'cooling'].includes(S.phase)) resetEruption();
  U.uDepOn.value = 0;
  appliedP = p; updateHud();
}

""")
rep("z.title = 'One eruption: weeks to hours, stretched out';", "z.title = 'One eruption: weeks to years, stretched out';")
cut("  else if (S.phase === 'growth') clock = 'cone growing';", "  $('time').textContent = time;", """  else if (S.phase === 'maar') clock = 'eruption · week ' + (1 + Math.floor(S.u / 0.3 * 6));
  else if (S.phase === 'fountain') clock = 'eruption · month ' + (2 + Math.floor((S.u - 0.3) / 0.3 * 6));
  else if (S.phase === 'lake') clock = 'eruption · month ' + (8 + Math.floor((S.u - 0.6) / 0.24 * 8));
  else if (S.phase === 'cooling') clock = 'years to decades later';
  else clock = 'million years ago';
""")

# ---------- views / labels ----------
cut("function eruptionView() {", "controls.addEventListener('start'", """function eruptionView() {
  const h = heightAt(CX, CZ) * exag;
  flyTo(new THREE.Vector3(CX + 2300, h + 700, CZ + 2700), new THREE.Vector3(CX, h + 200, CZ));
}
""")
cut("const VIEWS = {", "$('views').addEventListener", """const VIEWS = {
  overview: () => flyTo(V3(CX + 3800, 1900, CZ + 5200), V3(CX - 600, 380, CZ - 1500)),
  summit: () => { const h = groundAt(CX, CZ) * exag; flyTo(V3(CX + 750, h + 420, CZ + 950), V3(CX, h, CZ)); },
  eruption: () => eruptionView(),
  lake: () => { const h = Math.max(S.lvl, heightAt(CX, CZ)) * exag; flyTo(V3(CX + BAD.Rc * 0.95, h + 70, CZ + BAD.Rc * 0.55), V3(CX - 120, h, CZ - 80)); },
  hills: () => flyTo(V3(CX + 1800, 2400, CZ + 6200), V3(CX - 2300, 360, CZ - 3000)),
  walk: () => { const x = CX + BAD.Rc * 1.08, z = CZ + 180; if (camMode !== 'orbit') setMode('orbit', true); fly = null; controls.target.set(x, groundAt(x, z) * exag, z); setMode('walk'); yaw = Math.atan2(-(CX - x), -(CZ - z)); pitch = -0.05; },
};
""")
rep("  { text: 'Summit (reconstructed)', x: CX, z: CZ, kind: 'peak', past: true },", "  { text: 'Badacsony vent (reconstructed)', x: CX, z: CZ, kind: 'peak', past: true },")
rep("  if (S.phase === 'explosion' || S.phase === 'collapse') { fogCol.lerp(fogAsh, 0.4); fogD *= 1.8; sunI *= 0.7; }\n  else if (S.phase === 'aftermath') { fogCol.lerp(fogAsh, 0.25); fogD *= 1.3; sunI *= 0.85; }",
    "  if (S.phase === 'maar') { fogCol.lerp(fogAsh, 0.3); fogD *= 1.5; sunI *= 0.8; }\n  else if (S.phase === 'fountain') { fogCol.lerp(fogAsh, 0.15); fogD *= 1.2; }")

# ---------- eruption ----------
rep("const vent = () => ({ x: DOME.x, z: DOME.z, y: heightAt(DOME.x, DOME.z) * exag });", "const vent = () => ({ x: CX, z: CZ, y: heightAt(CX, CZ) * exag });\nconst K_SURGE = 5, K_BLOCK = 6;")
cut("function emit(dt) {", "let frameNo = 0;", """// phreatomagmatic blast: black cock's-tail jets, a base surge rolling over the rim, blocks of country rock
function maarBlast() {
  const R = Math.random, base = heightAt(CX, CZ) * exag;
  for (let k = 0; k < 170; k++) {
    const a = R() * 6.283, el = 0.95 + R() * 0.55, sp = 90 + R() * 150, rr = R() * BAD.Rc * 0.35;
    smoke.spawn(K_PLUME, CX + Math.cos(a) * rr, base + 10, CZ + Math.sin(a) * rr, Math.cos(a) * Math.cos(el) * sp, Math.sin(el) * sp, Math.sin(a) * Math.cos(el) * sp, 110 + R() * 60, 40 + R() * 50, 0, [0.16, 0.15, 0.14], 0.95, 0);
  }
  for (let k = 0; k < 240; k++) {
    const a = R() * 6.283, sp = 55 + R() * 55, x = CX + Math.cos(a) * BAD.Rc * 0.75, z = CZ + Math.sin(a) * BAD.Rc * 0.75;
    smoke.spawn(K_SURGE, x, heightAt(x, z) * exag + 20, z, Math.cos(a) * sp, 0, Math.sin(a) * sp, 70 + R() * 30, 70 + R() * 50, 350 + R() * 250, [0.70, 0.68, 0.64], 0.75, 0);
  }
  for (let k = 0; k < 70; k++) {
    const a = R() * 6.283, el = 0.6 + R() * 0.8, sp = 50 + R() * 90;
    smoke.spawn(K_BLOCK, CX + (R() - .5) * 120, base + 20, CZ + (R() - .5) * 120, Math.cos(a) * Math.cos(el) * sp, Math.sin(el) * sp, Math.sin(a) * Math.cos(el) * sp, 60, 4 + R() * 5, 4, [0.18, 0.16, 0.14], 1.0, 0);
  }
}
function emit(dt) {
  const ph = S.phase, R = Math.random, v = vent(), now = performance.now() / 1000;
  const lakeR = BAD.Rc * 0.88, ly = S.lvl * exag;
  if (ph === 'maar') {
    ER.blastT -= dt; if (ER.blastT <= 0) { ER.blastT = 2.5 + R() * 2.5; maarBlast(); }
    rate('steam', 22, dt, () => { const a = R() * 6.283, rr = R() * BAD.Rc * 0.4;
      smoke.spawn(K_STEAM, CX + Math.cos(a) * rr, v.y + 30, CZ + Math.sin(a) * rr, 0, 25 + R() * 25, 0, 70, 80, 500 + R() * 300, STEAM, 0.45); });
  }
  const pulse = Math.pow(0.5 + 0.5 * Math.sin(now * 2.4), 4) + 0.3;
  if (ph === 'fountain' || ph === 'lake') {
    const strength = ph === 'fountain' ? 1 : 0.25;
    rate('fount', 650 * pulse * strength, dt, () => { const a = R() * 6.283, sp = R() * 14;
      glow.spawn(0, CX + Math.cos(a) * 15, v.y + 5, CZ + Math.sin(a) * 15, Math.cos(a) * sp + (R() - .5) * 10, 40 + R() * 45 * (0.6 + pulse * 0.4), Math.sin(a) * sp + (R() - .5) * 10, 40, 1.5 + R() * 3.5, 0.9 + R() * 0.1); });
    rate('plume', 22 * strength, dt, () => column(v, 0.4));
  }
  if (ph === 'lake') {
    rate('spatter', 30, dt, () => { const a = R() * 6.283, rr = Math.sqrt(R()) * lakeR, x = CX + Math.cos(a) * rr, z = CZ + Math.sin(a) * rr;
      for (let j = 0; j < 6; j++) glow.spawn(0, x, ly + 1, z, (R() - .5) * 12, 8 + R() * 22, (R() - .5) * 12, 30, 1 + R() * 2, 0.95); });
    rate('lakegas', 8, dt, () => smoke.spawn(K_STEAM, CX + (R() - .5) * lakeR, ly + 5, CZ + (R() - .5) * lakeR, 0, 8 + R() * 8, 0, 50, 40, 300 + R() * 200, [0.78, 0.76, 0.74], 0.3, 0.25));
  }
  if (ph === 'cooling') rate('lakesteam', 10, dt, () => smoke.spawn(K_STEAM, CX + (R() - .5) * lakeR * 1.6, ly + 3, CZ + (R() - .5) * lakeR * 1.6, 0, 6 + R() * 6, 0, 45, 30, 250, STEAM, 0.3, 0.1 * S.hot));
}

""")
rep("  const ds = dt * TS, sm = smoke, R = Math.random, v = vent(), Hn = 6800;", "  const ds = dt * TS, sm = smoke, R = Math.random, v = vent(), Hn = 3400;")
rep("""      } else if (k === K_STEAM) {""", """      } else if (k === K_SURGE) {
        sm.vx[i] *= Math.exp(-0.32 * ds); sm.vz[i] *= Math.exp(-0.32 * ds); sm.vy[i] = 0;
        sm.size[i] = mix(sm.s0[i], sm.s1[i], Math.sqrt(sm.age[i] / sm.life[i])); sm.shade[i] = 0.92;
      } else if (k === K_BLOCK) {
        sm.vy[i] -= 9.8 * ds; sm.size[i] = sm.s0[i]; sm.shade[i] = 1;
      } else if (k === K_STEAM) {""")
rep("""      sm.px[i] += sm.vx[i] * ds; sm.py[i] += sm.vy[i] * ds; sm.pz[i] += sm.vz[i] * ds;
      if ((i + frameNo) % 4 === 0) sm.gy[i] = heightAt(sm.px[i], sm.pz[i]) * exag;""", """      sm.px[i] += sm.vx[i] * ds; sm.py[i] += sm.vy[i] * ds; sm.pz[i] += sm.vz[i] * ds;
      if (k === K_BLOCK) {
        const gb = heightAt(sm.px[i], sm.pz[i]) * exag;
        if (sm.py[i] < gb) { if (R() < 0.6) smoke.spawn(K_DUST, sm.px[i], gb + 6, sm.pz[i], (R() - .5) * 8, 5, (R() - .5) * 8, 14, 10, 45, DUST, 0.6); sm.age[i] = 1e9; continue; }
        sm.gy[i] = gb - 1e4; sm.rot[i] += sm.rs[i] * dt; continue;
      }
      if ((i + frameNo) % 4 === 0) sm.gy[i] = heightAt(sm.px[i], sm.pz[i]) * exag;
      if (k === K_SURGE) sm.py[i] = sm.gy[i] + sm.size[i] * 0.3;""")
rep("if (location.search.includes(\"debug\")) window.__dbg = { setLight,", "if (location.search.includes(\"debug\")) window.__dbg = { BAD, S: () => S, setLight,")
open(os.path.join(HERE, '..', 'index.html'), 'w').write(s)
print('ported', len(s))
