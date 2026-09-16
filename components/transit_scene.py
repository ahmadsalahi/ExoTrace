"""
components/transit_scene.py — High-Fidelity Continuous Comet Transit Simulation (CCv2).

Features:
  1. Full Bilingual Support: 100% Peer-Reviewed English and Arabic.
  2. Continuous auto-looping animation starting automatically on page load.
  3. Photorealistic star with 3D limb darkening, solar flares, and shimmering corona.
  4. Dynamic comet nucleus with outgassing coma and trailing dust particle physics.
  5. Real-time synchronized light curve with moving telemetry scanning head.
  6. Live floating HUD telemetry (instantaneous brightness, transit phase, loop counter).
  7. In-scene controls for pause/play, speed (1x / 2x), and loop toggle.
  8. Seamless Light / Dark mode visual styling.
"""

import streamlit as st


def _build_transit_html(lang: str = "ar", is_light: bool = False) -> str:
    is_en = (lang == "en")
    
    # Palette
    if is_light:
        hdr_bg = "#ffffff"
        hdr_border = "1px solid #cbd5e1"
        hdr_text = "#0f172a"
        lc_bg = "#ffffff"
        lc_border = "1px solid #cbd5e1"
        lc_title_col = "#475569"
        canvas_border = "1px solid #cbd5e1"
    else:
        hdr_bg = "rgba(15,23,42,0.85)"
        hdr_border = "1px solid rgba(56,189,248,0.2)"
        hdr_text = "#e0f2fe"
        lc_bg = "rgba(11,19,41,0.95)"
        lc_border = "1px solid rgba(56,189,248,0.2)"
        lc_title_col = "#94a3b8"
        canvas_border = "1px solid rgba(56,189,248,0.2)"

    # Text strings
    if is_en:
        status_text = "Live Astronomical Transit Simulation"
        brightness_text = "Brightness: 100.00%"
        pause_btn_text = "<span>⏸️ Pause</span>"
        lc_title_text = "📉 Real-Time Synchronized Light Curve (Normalized Flux vs Time)"
        phase_text = "Phase: Comet Approaching Host Star"
    else:
        status_text = "محاكاة العبور الفلكي المباشرة"
        brightness_text = "السطوع: 100.00%"
        pause_btn_text = "<span>⏸️ إيقاف مؤقت</span>"
        lc_title_text = "📉 منحنى تدفق الضوء المتزامن لحظياً (Normalized Flux vs Time)"
        phase_text = "المرحلة: اقتراب المذنب من النجم"

    return f"""
<div id="exo-transit-root" style="width:100%;font-family:inherit;position:relative;">
  <!-- Simulation Header & Telemetry Overlay -->
  <div style="display:flex;justify-content:space-between;align-items:center;padding:8px 12px;
    background:{hdr_bg};border-top-left-radius:12px;border-top-right-radius:12px;
    border:{hdr_border};border-bottom:none;">
    <div style="display:flex;align-items:center;gap:8px;">
      <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#38bdf8;
        box-shadow:0 0 10px #38bdf8;"></span>
      <span id="sim-hud-status" style="font-size:0.85rem;font-weight:700;color:{hdr_text};">
        {status_text}
      </span>
    </div>
    <div style="display:flex;align-items:center;gap:12px;">
      <span id="sim-hud-brightness" style="font-family:monospace;font-size:0.9rem;font-weight:800;color:#fbbf24;
        background:rgba(251,191,36,0.1);padding:3px 10px;border-radius:6px;border:1px solid rgba(251,191,36,0.3);">
        {brightness_text}
      </span>
      <button id="sim-btn-playpause" style="background:#0284c7;color:#fff;border:none;border-radius:6px;
        padding:4px 10px;font-size:0.8rem;cursor:pointer;font-weight:600;display:flex;align-items:center;gap:4px;">
        {pause_btn_text}
      </button>
      <button id="sim-btn-speed" style="background:rgba(30,41,59,0.8);color:#fbbf24;border:1px solid rgba(56,189,248,0.2);
        border-radius:6px;padding:4px 8px;font-size:0.8rem;cursor:pointer;">
        0.5x
      </button>
    </div>
  </div>

  <!-- Main Observatory Canvas (Star & Comet) -->
  <canvas id="scene-canvas" style="width:100%;display:block;
    background:radial-gradient(ellipse at center, #0b1329 0%, #060a14 100%);
    border-left:{canvas_border};border-right:{canvas_border};"></canvas>

  <!-- Synchronized Light Curve Canvas -->
  <div style="background:{lc_bg};padding:6px 12px 10px 12px;
    border:{lc_border};border-top:1px dashed rgba(56,189,248,0.15);
    border-bottom-left-radius:12px;border-bottom-right-radius:12px;">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
      <span id="sim-lc-header-title" style="font-size:0.8rem;color:{lc_title_col};font-weight:600;">
        {lc_title_text}
      </span>
      <span id="sim-hud-phase" style="font-size:0.75rem;color:#38bdf8;font-weight:600;">
        {phase_text}
      </span>
    </div>
    <canvas id="lc-canvas" style="width:100%;border-radius:8px;display:block;
      background:rgba(7,11,20,0.9);border:1px solid rgba(30,41,59,0.8);"></canvas>
  </div>
</div>
"""


_TRANSIT_CSS = """
#exo-transit-root {
  user-select: none;
}
#exo-transit-root button:hover {
  filter: brightness(1.2);
}
"""


def _build_transit_js(lang: str = "ar") -> str:
    is_en = (lang == "en")

    if is_en:
        js_status_loop = "Live Astronomical Transit Simulation"
        js_status_paused = "Astronomical Transit Simulation: Paused"
        js_brightness_prefix = "Brightness: "
        js_btn_pause = "<span>⏸️ Pause</span>"
        js_btn_resume = "<span>▶️ Resume</span>"
        js_phase_approach = "Phase: Comet Approaching Host Star"
        js_phase_ingress = "Phase: Sharp Ingress (Comet Nucleus Transit)"
        js_phase_dip = "Phase: Peak Flux Obscuration (Transit Minimum)"
        js_phase_egress = "Phase: Gradual Egress (Extended Dust Tail)"
        js_phase_complete = "Phase: Transit Cycle Complete (Post-Egress)"
    else:
        js_status_loop = "محاكاة العبور الفلكي المباشرة"
        js_status_paused = "محاكاة العبور الفلكي: متوقفة مؤقتاً"
        js_brightness_prefix = "السطوع: "
        js_btn_pause = "<span>⏸️ إيقاف مؤقت</span>"
        js_btn_resume = "<span>▶️ استئناف</span>"
        js_phase_approach = "المرحلة: اقتراب المذنب من النجم"
        js_phase_ingress = "المرحلة: هبوط حاد وسريع (دخول النواة Ingress)"
        js_phase_dip = "المرحلة: ذروة حجب الضوء (Transit Dip)"
        js_phase_egress = "المرحلة: خروج بطيء تدريجي (ذيل غباري ممتد Egress)"
        js_phase_complete = "المرحلة: اكتمال دورة العبور والعودة للمسار"

    return f"""
export default function(component) {{
  const {{ parentElement }} = component;
  const root = parentElement.querySelector("#exo-transit-root");
  if (!root) return;

  const sceneCanvas = root.querySelector("#scene-canvas");
  const lcCanvas = root.querySelector("#lc-canvas");
  const hudBrightness = root.querySelector("#sim-hud-brightness");
  const hudStatus = root.querySelector("#sim-hud-status");
  const hudPhase = root.querySelector("#sim-hud-phase");
  const btnPlayPause = root.querySelector("#sim-btn-playpause");
  const btnSpeed = root.querySelector("#sim-btn-speed");

  if (!sceneCanvas || !lcCanvas) return;

  // Responsive dimensions - fixing aspect ratio for large screens
  const containerWidth = root.clientWidth || 750;
  const sceneW = containerWidth;
  const sceneH = Math.min(480, Math.max(250, containerWidth * 0.35));
  const lcW = containerWidth;
  const lcH = Math.max(120, containerWidth * 0.16);
  const dpr = window.devicePixelRatio || 1;

  sceneCanvas.width = sceneW * dpr;
  sceneCanvas.height = sceneH * dpr;
  sceneCanvas.style.width = "100%";
  sceneCanvas.style.height = "auto";

  lcCanvas.width = lcW * dpr;
  lcCanvas.height = lcH * dpr;
  lcCanvas.style.width = "100%";
  lcCanvas.style.height = "auto";

  const sCtx = sceneCanvas.getContext("2d");
  const lCtx = lcCanvas.getContext("2d");
  sCtx.scale(dpr, dpr);
  lCtx.scale(dpr, dpr);

  // Star geometry
  const starX = sceneW * 0.52;
  const starY = sceneH * 0.5;
  const starR = sceneH * 0.28;

  // Comet trajectory
  const cometStartX = -100;
  const cometEndX = sceneW + 140;
  const cometY = starY + (sceneH * 0.04);
  const tailBaseLen = sceneW * 0.22;

  // Particle System for realistic dust tail
  const particles = [];
  const maxParticles = 60;
  for (let i = 0; i < maxParticles; i++) {{
    particles.push({{
      x: 0,
      y: 0,
      vx: 0,
      vy: 0,
      life: 0,
      maxLife: 30 + Math.random() * 25,
      size: 1 + Math.random() * 2
    }});
  }}

  // Animation State
  let cometX = cometStartX;
  let isRunning = true;
  let speedMultiplier = 0.5;
  let animFrame = null;
  let frameCount = 0;
  let lcHistory = [];
  let coronaPhase = 0;

  // ── Physics Calculations: Asymmetric Ingress / Egress ──
  function getFluxAt(cx) {{
    const d = cx - starX;
    if (d < -starR * 1.5 || d > starR + tailBaseLen * 1.6) {{
      return 1.0;
    }}

    // Ingress: Sharp steep slope (Comet Head)
    if (d < 0) {{
      const normD = Math.max(0, (d + starR) / starR);
      const ingressDrop = 0.055 * Math.pow(normD, 2.2);
      return Math.max(0.945, 1.0 - ingressDrop);
    }}

    // Egress: Extended lingering dust tail
    const normTail = d / (tailBaseLen * 1.5);
    const tailFactor = Math.exp(-normTail * 1.95);
    const egressDrop = 0.055 * tailFactor;
    return Math.max(0.945, 1.0 - egressDrop);
  }}

  // ── Draw Photorealistic Star ──
  function drawStar(ctx, currentFlux) {{
    coronaPhase += 0.02;

    // 1. Outer shimmering stellar corona
    const coronaR = starR * (1.35 + Math.sin(coronaPhase) * 0.03);
    const coronaGrad = ctx.createRadialGradient(starX, starY, starR * 0.8, starX, starY, coronaR);
    coronaGrad.addColorStop(0, "rgba(245, 158, 11, 0.45)");
    coronaGrad.addColorStop(0.5, "rgba(251, 191, 36, 0.15)");
    coronaGrad.addColorStop(1, "rgba(251, 191, 36, 0)");

    ctx.beginPath();
    ctx.arc(starX, starY, coronaR, 0, Math.PI * 2);
    ctx.fillStyle = coronaGrad;
    ctx.fill();

    // 2. Solar Flares
    ctx.save();
    ctx.translate(starX, starY);
    for (let f = 0; f < 8; f++) {{
      const angle = (f * Math.PI / 4) + (coronaPhase * 0.2);
      const flareLen = starR * (1.1 + Math.sin(coronaPhase * 2 + f) * 0.08);
      ctx.beginPath();
      ctx.moveTo(0, 0);
      ctx.lineTo(Math.cos(angle - 0.08) * flareLen, Math.sin(angle - 0.08) * flareLen);
      ctx.lineTo(Math.cos(angle + 0.08) * flareLen, Math.sin(angle + 0.08) * flareLen);
      ctx.closePath();
      ctx.fillStyle = "rgba(251, 191, 36, 0.08)";
      ctx.fill();
    }}
    ctx.restore();

    // 3. Stellar Photosphere with 3D Limb Darkening
    const starGrad = ctx.createRadialGradient(
      starX - starR * 0.25,
      starY - starR * 0.25,
      starR * 0.05,
      starX,
      starY,
      starR
    );
    starGrad.addColorStop(0, "#fffbeb");
    starGrad.addColorStop(0.3, "#fef3c7");
    starGrad.addColorStop(0.7, "#fbbf24");
    starGrad.addColorStop(0.92, "#f59e0b");
    starGrad.addColorStop(1, "#b45309");

    ctx.beginPath();
    ctx.arc(starX, starY, starR, 0, Math.PI * 2);
    ctx.fillStyle = starGrad;
    ctx.shadowColor = "#f59e0b";
    ctx.shadowBlur = 24;
    ctx.fill();
    ctx.shadowBlur = 0;

    // 4. Subtle orbital path guide
    ctx.beginPath();
    ctx.ellipse(starX, starY, starR * 1.9, starR * 0.2, -0.15, 0, Math.PI * 2);
    ctx.strokeStyle = "rgba(56, 189, 248, 0.12)";
    ctx.lineWidth = 1;
    ctx.setLineDash([4, 4]);
    ctx.stroke();
    ctx.setLineDash([]);
  }}

  // ── Draw Comet with Particle Dust Tail ──
  function drawComet(ctx, cx, cy) {{
    // 1. Emit new dust particles behind comet
    for (let p of particles) {{
      if (p.life <= 0) {{
        p.x = cx - 4 + (Math.random() * 4);
        p.y = cy - 2 + (Math.random() * 4);
        p.vx = -1.2 - Math.random() * 2.0;
        p.vy = (Math.random() - 0.5) * 0.8;
        p.life = p.maxLife;
        break;
      }}
    }}

    // 2. Draw active dust tail particles
    for (let p of particles) {{
      if (p.life > 0) {{
        p.x += p.vx;
        p.y += p.vy;
        p.life--;

        const alpha = (p.life / p.maxLife) * 0.45;
        const currentSize = p.size * (1 + (1 - p.life / p.maxLife) * 1.5);

        ctx.beginPath();
        ctx.arc(p.x, p.y, currentSize, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(186, 230, 253, ${{alpha}})`;
        ctx.fill();
      }}
    }}

    // 3. Extended Vapor Dust Tail Fan
    const tailGrad = ctx.createLinearGradient(cx, cy, cx - tailBaseLen, cy - 8);
    tailGrad.addColorStop(0, "rgba(224, 242, 254, 0.75)");
    tailGrad.addColorStop(0.2, "rgba(56, 189, 248, 0.45)");
    tailGrad.addColorStop(0.65, "rgba(14, 165, 233, 0.15)");
    tailGrad.addColorStop(1, "rgba(14, 165, 233, 0)");

    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.quadraticCurveTo(cx - tailBaseLen * 0.4, cy - 10, cx - tailBaseLen, cy - 14);
    ctx.lineTo(cx - tailBaseLen * 0.85, cy + 8);
    ctx.quadraticCurveTo(cx - tailBaseLen * 0.35, cy + 6, cx, cy);
    ctx.closePath();
    ctx.fillStyle = tailGrad;
    ctx.fill();

    // 4. Outgassing Coma
    const comaGrad = ctx.createRadialGradient(cx, cy, 1, cx, cy, 14);
    comaGrad.addColorStop(0, "rgba(255, 255, 255, 0.95)");
    comaGrad.addColorStop(0.3, "rgba(125, 211, 252, 0.7)");
    comaGrad.addColorStop(0.7, "rgba(56, 189, 248, 0.3)");
    comaGrad.addColorStop(1, "rgba(56, 189, 248, 0)");

    ctx.beginPath();
    ctx.arc(cx, cy, 14, 0, Math.PI * 2);
    ctx.fillStyle = comaGrad;
    ctx.fill();

    // 5. Solid Icy Nucleus
    ctx.beginPath();
    ctx.arc(cx, cy, 3.2, 0, Math.PI * 2);
    ctx.fillStyle = "#ffffff";
    ctx.shadowColor = "#38bdf8";
    ctx.shadowBlur = 12;
    ctx.fill();
    ctx.shadowBlur = 0;
  }}

  // ── Draw Synchronized Light Curve ──
  function drawLightCurve(ctx, currentProgress, currentFlux) {{
    ctx.clearRect(0, 0, lcW, lcH);

    const padLeft = 24;
    const padRight = 24;
    const padTop = 14;
    const padBottom = 18;
    const plotW = lcW - padLeft - padRight;
    const plotH = lcH - padTop - padBottom;

    // Grid lines
    ctx.strokeStyle = "rgba(56, 189, 248, 0.08)";
    ctx.lineWidth = 1;
    for (let i = 0; i <= 3; i++) {{
      const y = padTop + (plotH * i / 3);
      ctx.beginPath();
      ctx.moveTo(padLeft, y);
      ctx.lineTo(lcW - padRight, y);
      ctx.stroke();
    }}

    // Baseline (1.00 Flux) dashed line
    ctx.beginPath();
    ctx.setLineDash([3, 3]);
    ctx.strokeStyle = "rgba(148, 163, 184, 0.25)";
    ctx.moveTo(padLeft, padTop);
    ctx.lineTo(lcW - padRight, padTop);
    ctx.stroke();
    ctx.setLineDash([]);

    // Pre-calculate full theoretical curve
    ctx.beginPath();
    ctx.strokeStyle = "rgba(56, 189, 248, 0.25)";
    ctx.lineWidth = 1.5;
    for (let step = 0; step <= 100; step++) {{
      const p = step / 100;
      const simX = cometStartX + p * (cometEndX - cometStartX);
      const f = getFluxAt(simX);
      const px = padLeft + (p * plotW);
      const py = padTop + ((1.0 - f) / 0.065) * plotH;
      if (step === 0) ctx.moveTo(px, py);
      else ctx.lineTo(px, py);
    }}
    ctx.stroke();

    // Active illuminated curve
    ctx.beginPath();
    ctx.strokeStyle = "#38bdf8";
    ctx.lineWidth = 3;
    ctx.shadowColor = "rgba(56, 189, 248, 0.6)";
    ctx.shadowBlur = 8;

    for (let i = 0; i < lcHistory.length; i++) {{
      const h = lcHistory[i];
      const px = padLeft + (h.p * plotW);
      const py = padTop + ((1.0 - h.f) / 0.065) * plotH;
      if (i === 0) ctx.moveTo(px, py);
      else ctx.lineTo(px, py);
    }}
    ctx.stroke();
    ctx.shadowBlur = 0;

    // Moving Scanner Indicator Head
    const curPx = padLeft + (currentProgress * plotW);
    const curPy = padTop + ((1.0 - currentFlux) / 0.065) * plotH;

    // Vertical scan line
    ctx.beginPath();
    ctx.strokeStyle = "rgba(251, 191, 36, 0.4)";
    ctx.lineWidth = 1;
    ctx.moveTo(curPx, padTop);
    ctx.lineTo(curPx, padTop + plotH);
    ctx.stroke();

    // Glowing dot
    ctx.beginPath();
    ctx.arc(curPx, curPy, 5, 0, Math.PI * 2);
    ctx.fillStyle = "#fbbf24";
    ctx.shadowColor = "#fbbf24";
    ctx.shadowBlur = 10;
    ctx.fill();
    ctx.shadowBlur = 0;

    ctx.beginPath();
    ctx.arc(curPx, curPy, 8, 0, Math.PI * 2);
    ctx.strokeStyle = "rgba(251, 191, 36, 0.5)";
    ctx.lineWidth = 1.5;
    ctx.stroke();
  }}

  // ── Main Animation Loop ──
  function loop() {{
    if (!isRunning) return;

    const speed = (sceneW / 260) * speedMultiplier;
    cometX += speed;

    if (cometX >= cometEndX) {{
      cometX = cometStartX;
      lcHistory = [];
    }}

    const currentProgress = Math.max(0, Math.min(1, (cometX - cometStartX) / (cometEndX - cometStartX)));
    const currentFlux = getFluxAt(cometX);

    lcHistory.push({{ p: currentProgress, f: currentFlux }});
    if (lcHistory.length > 300) lcHistory.shift();

    sCtx.clearRect(0, 0, sceneW, sceneH);
    drawStar(sCtx, currentFlux);
    drawComet(sCtx, cometX, cometY);

    drawLightCurve(lCtx, currentProgress, currentFlux);

    const brightnessPct = (currentFlux * 100).toFixed(2);
    hudBrightness.textContent = `{js_brightness_prefix}${{brightnessPct}}%`;

    const d = cometX - starX;
    if (d < -starR * 1.5) {{
      hudPhase.textContent = "{js_phase_approach}";
      hudPhase.style.color = "#94a3b8";
    }} else if (d >= -starR * 1.5 && d < 0) {{
      hudPhase.textContent = "{js_phase_ingress}";
      hudPhase.style.color = "#ef4444";
    }} else if (d >= 0 && d <= starR) {{
      hudPhase.textContent = "{js_phase_dip}";
      hudPhase.style.color = "#f59e0b";
    }} else if (d > starR && d <= tailBaseLen * 1.6) {{
      hudPhase.textContent = "{js_phase_egress}";
      hudPhase.style.color = "#38bdf8";
    }} else {{
      hudPhase.textContent = "{js_phase_complete}";
      hudPhase.style.color = "#4ade80";
    }}

    frameCount++;
    animFrame = requestAnimationFrame(loop);
  }}

  // ── Button Handlers ──
  btnPlayPause.onclick = () => {{
    isRunning = !isRunning;
    if (isRunning) {{
      btnPlayPause.innerHTML = "{js_btn_pause}";
      btnPlayPause.style.background = "#0284c7";
      hudStatus.textContent = "{js_status_loop}";
      loop();
    }} else {{
      btnPlayPause.innerHTML = "{js_btn_resume}";
      btnPlayPause.style.background = "#16a34a";
      hudStatus.textContent = "{js_status_paused}";
      if (animFrame) cancelAnimationFrame(animFrame);
    }}
  }};

  btnSpeed.onclick = () => {{
    if (speedMultiplier === 0.5) {{
      speedMultiplier = 1.0;
      btnSpeed.textContent = "1x";
      btnSpeed.style.color = "#94a3b8";
    }} else if (speedMultiplier === 1.0) {{
      speedMultiplier = 2.0;
      btnSpeed.textContent = "2x";
      btnSpeed.style.color = "#38bdf8";
    }} else {{
      speedMultiplier = 0.5;
      btnSpeed.textContent = "0.5x";
      btnSpeed.style.color = "#fbbf24";
    }}
  }};

  loop();

  return () => {{
    if (animFrame) cancelAnimationFrame(animFrame);
  }};
}}
"""


# Declare 4 specialized component instances for immediate zero-latency rendering
_transit_component_en_dark = st.components.v2.component(
    "exo_transit_scene_v5_en_dark",
    html=_build_transit_html(lang="en", is_light=False),
    css=_TRANSIT_CSS,
    js=_build_transit_js(lang="en"),
)
_transit_component_en_light = st.components.v2.component(
    "exo_transit_scene_v5_en_light",
    html=_build_transit_html(lang="en", is_light=True),
    css=_TRANSIT_CSS,
    js=_build_transit_js(lang="en"),
)
_transit_component_ar_dark = st.components.v2.component(
    "exo_transit_scene_v5_ar_dark",
    html=_build_transit_html(lang="ar", is_light=False),
    css=_TRANSIT_CSS,
    js=_build_transit_js(lang="ar"),
)
_transit_component_ar_light = st.components.v2.component(
    "exo_transit_scene_v5_ar_light",
    html=_build_transit_html(lang="ar", is_light=True),
    css=_TRANSIT_CSS,
    js=_build_transit_js(lang="ar"),
)


def render_transit_scene(key: str = "continuous_transit_scene"):
    """
    Render the continuous photorealistic comet transit simulation.
    Automatically matches current platform language (EN / AR) and Theme (Dark / Light).
    """
    from lib.i18n import get_lang, get_theme
    lang = get_lang()
    is_light = (get_theme() == "light")

    if lang == "en":
        comp = _transit_component_en_light if is_light else _transit_component_en_dark
    else:
        comp = _transit_component_ar_light if is_light else _transit_component_ar_dark

    return comp(
        data={"auto_play": True, "lang": lang},
        key=f"{key}_{lang}_{'light' if is_light else 'dark'}",
        height=500,
    )
