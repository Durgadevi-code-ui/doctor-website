/*
 * app/static/js/script.js
 * -------------------------
 * Public intake page only. The customer records dashboard (search,
 * filter, pagination, CSV export, table) that used to live on this
 * page was REMOVED - not hidden, removed - per the Washington DC
 * Doctors Meet privacy requirement that submitted customer data must
 * never be publicly viewable. That functionality now lives at
 * /admin/dashboard (see app/static/js/admin.js), behind a
 * username+password+OTP login.
 *
 * This file still contains, unchanged in behavior: the progress bar,
 * chip/checkbox group handling, the conditional "specify your
 * practice" field, and the success screen. New in this revision: a
 * lightweight Three.js particle-network hero background and GSAP
 * scroll-triggered reveals.
 */

const API_BASE = '/api/customers';

const form = document.getElementById('customer-form');
const submitBtn = document.getElementById('submit-btn');
const submitBtnLabel = submitBtn.querySelector('.submit-btn-label');
const banner = document.getElementById('banner');

const formBody = document.getElementById('form-body');
const successScreen = document.getElementById('success-screen');
const successResetBtn = document.getElementById('success-reset-btn');

const practiceTypeSelect = document.getElementById('practice_type');
const practiceTypeOtherWrap = document.getElementById('practice_type_other_wrap');
const practiceTypeOtherInput = document.getElementById('practice_type_other');

const progressFill = document.getElementById('progress-fill');
const progressPercent = document.getElementById('progress-percent');

const TEXT_FIELDS = [
  'customer_name', 'phone_number', 'email', 'business_name',
  'locations', 'daily_calls', 'additional_notes', 'practice_type_other',
];
const SELECT_FIELDS = ['customer_role', 'practice_type', 'specialty'];
const CHIP_GROUPS = { pain_point: 'pain-group' };
const CHECKBOX_GROUPS = { interested_service: 'service-group' };

// Mirrors the backend's REQUIRED_FIELDS in app/utils/validators.py
// (practice_type_other is conditionally required only when
// practice_type === "Other").
const PROGRESS_REQUIRED_FIELDS = [
  'customer_name', 'phone_number', 'email', 'business_name',
  'practice_type', 'specialty',
];

/* ---------- Chip group (single-select: pain point) ---------- */

function setupChipGroup(groupId) {
  const group = document.getElementById(groupId);
  const chips = group.querySelectorAll('.chip');
  chips.forEach((chip) => {
    chip.addEventListener('click', () => {
      chips.forEach((c) => c.classList.remove('selected'));
      chip.classList.add('selected');
      updateProgress();
    });
  });
}
setupChipGroup('pain-group');

function getChipValue(groupId) {
  const el = document.querySelector('#' + groupId + ' .selected');
  return el ? el.dataset.value : '';
}

function clearChipGroup(groupId) {
  document.querySelectorAll('#' + groupId + ' .selected').forEach((el) => el.classList.remove('selected'));
}

/* ---------- Checkbox group (multi-select: interested services) ---------- */

function setupCheckboxGroup(groupId) {
  const group = document.getElementById(groupId);
  const checkboxes = group.querySelectorAll('input[type="checkbox"]');
  checkboxes.forEach((checkbox) => {
    checkbox.addEventListener('change', () => {
      checkbox.closest('.checkbox-chip').classList.toggle('selected', checkbox.checked);
      updateProgress();
    });
  });
}
setupCheckboxGroup('service-group');

function getCheckedValues(groupId) {
  const checked = document.querySelectorAll('#' + groupId + ' input[type="checkbox"]:checked');
  return Array.from(checked).map((cb) => cb.value).join(', ');
}

function clearCheckboxGroup(groupId) {
  document.querySelectorAll('#' + groupId + ' input[type="checkbox"]').forEach((cb) => {
    cb.checked = false;
    cb.closest('.checkbox-chip').classList.remove('selected');
  });
}

/* ---------- Practice type: conditional "specify" textbox ---------- */

function togglePracticeTypeOther() {
  const isOther = practiceTypeSelect.value === 'Other';
  practiceTypeOtherWrap.hidden = !isOther;
  if (!isOther) practiceTypeOtherInput.value = '';
}
practiceTypeSelect.addEventListener('change', () => {
  togglePracticeTypeOther();
  updateProgress();
});

/* ---------- Progress bar ---------- */

let currentProgressStep = null;

/* v3.1.1: fade/slide transition for the step-ratio text, per the
   "add smooth transition... GSAP if already available" requirement.
   Only fires when the step number actually changes (not on every
   keystroke), and falls back to an instant text swap if GSAP hasn't
   loaded (e.g. CDN blocked) so the indicator still works either way. */
function setProgressStep(step) {
  if (step === currentProgressStep) return;
  currentProgressStep = step;

  if (typeof gsap === 'undefined') {
    progressPercent.textContent = step;
    return;
  }

  // Fade + slide-from-left: the old number fades out in place, the
  // new one enters from a few pixels to the left and settles - subtle
  // on purpose, matching "do not add heavy animations."
  gsap.timeline()
    .to(progressPercent, { opacity: 0, duration: 0.1, ease: 'power1.in' })
    .call(() => { progressPercent.textContent = step; })
    .fromTo(
      progressPercent,
      { opacity: 0, x: -6 },
      { opacity: 1, x: 0, duration: 0.25, ease: 'power2.out' },
    );
}

function updateProgress() {
  let completed = 0;
  let total = PROGRESS_REQUIRED_FIELDS.length + 2; // + pain point + interested service

  PROGRESS_REQUIRED_FIELDS.forEach((field) => {
    if (document.getElementById(field).value.trim()) completed += 1;
  });
  if (practiceTypeSelect.value === 'Other') {
    total += 1;
    if (practiceTypeOtherInput.value.trim()) completed += 1;
  }
  if (getChipValue('pain-group')) completed += 1;
  if (getCheckedValues('service-group')) completed += 1;

  const percent = Math.round((completed / total) * 100);
  progressFill.style.width = percent + '%';
  // v3.1: the bar-fill math above is unchanged - only the displayed
  // text changed, from "N% complete" to a "Step X / 4" ratio, mapping
  // each 25% band of completion to one of 4 steps.
  const step = percent <= 0 ? 1 : Math.min(4, Math.ceil(percent / 25));
  setProgressStep(step);
  progressFill.classList.toggle('complete', percent === 100);
}
form.addEventListener('input', updateProgress);
updateProgress();

/* ---------- Validation icons (UX feedback only - the backend in
   app/utils/validators.py remains the authoritative check) ---------- */

function attachValidationIcons() {
  const controls = form.querySelectorAll('input[required], select[required]');
  controls.forEach((el) => {
    el.addEventListener('blur', () => {
      if (!el.value) {
        el.classList.remove('valid', 'invalid');
        return;
      }
      el.classList.toggle('valid', el.checkValidity());
      el.classList.toggle('invalid', !el.checkValidity());
    });
    el.addEventListener('input', () => {
      if (el.classList.contains('invalid') && el.checkValidity()) {
        el.classList.remove('invalid');
        el.classList.add('valid');
      }
    });
  });
}
attachValidationIcons();

/* ---------- Form: errors + banner ---------- */

function allFieldNames() {
  return [...TEXT_FIELDS, ...SELECT_FIELDS, ...Object.keys(CHIP_GROUPS), ...Object.keys(CHECKBOX_GROUPS)];
}

function clearFieldErrors() {
  allFieldNames().forEach((field) => {
    const errorEl = document.getElementById('err-' + field);
    const input = document.getElementById(field);
    if (errorEl) {
      errorEl.textContent = '';
      errorEl.classList.remove('show');
    }
    if (input) input.classList.remove('invalid');
  });
}

function showFieldErrors(errors) {
  Object.entries(errors).forEach(([field, message]) => {
    const errorEl = document.getElementById('err-' + field);
    const input = document.getElementById(field);
    if (errorEl) {
      errorEl.textContent = message;
      errorEl.classList.add('show');
    }
    if (input) input.classList.add('invalid');
  });
}

function showBanner(message, type) {
  banner.textContent = message;
  banner.className = 'banner show ' + type;
}

function hideBanner() {
  banner.className = 'banner';
  banner.textContent = '';
}

/* ---------- Form submission ---------- */

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  hideBanner();
  clearFieldErrors();

  const payload = {
    customer_name: document.getElementById('customer_name').value.trim(),
    customer_role: document.getElementById('customer_role').value,
    phone_number: document.getElementById('phone_number').value.trim(),
    email: document.getElementById('email').value.trim(),
    business_name: document.getElementById('business_name').value.trim(),
    practice_type: practiceTypeSelect.value,
    practice_type_other: practiceTypeOtherInput.value.trim(),
    specialty: document.getElementById('specialty').value,
    locations: document.getElementById('locations').value,
    pain_point: getChipValue('pain-group'),
    daily_calls: document.getElementById('daily_calls').value,
    interested_service: getCheckedValues('service-group'),
    additional_notes: document.getElementById('additional_notes').value.trim(),
  };

  submitBtn.disabled = true;
  submitBtn.classList.add('is-loading');
  submitBtnLabel.textContent = 'Submitting…';

  try {
    const res = await fetch(API_BASE, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const body = await res.json();

    if (res.status === 201) {
      showSuccessScreen();
    } else if (res.status === 400 && body.errors) {
      showFieldErrors(body.errors);
      showBanner('Please fix the highlighted fields.', 'error');
    } else if (res.status === 409) {
      showBanner(body.message || 'This email or contact number is already registered.', 'error');
    } else {
      showBanner(body.message || 'Something went wrong. Please try again.', 'error');
    }
  } catch (err) {
    showBanner('Network error. Please check your connection and try again.', 'error');
  } finally {
    submitBtn.disabled = false;
    submitBtn.classList.remove('is-loading');
    submitBtnLabel.textContent = 'Submit';
  }
});

/* ---------- Success screen ---------- */

function showSuccessScreen() {
  formBody.hidden = true;
  successScreen.hidden = false;
}

function resetIntakeForm() {
  form.reset();
  clearFieldErrors();
  hideBanner();
  clearChipGroup('pain-group');
  clearCheckboxGroup('service-group');
  togglePracticeTypeOther();
  updateProgress();
  successScreen.hidden = true;
  formBody.hidden = false;
}

successResetBtn.addEventListener('click', resetIntakeForm);

/* ==================================================================
   Full-page background: Three.js particle / node network
   ==================================================================
   v3.1: promoted from a hero-only canvas to a single, fixed,
   full-viewport background that stays visible behind the hero, the
   intake form, and the rest of the page through the entire scroll
   (see .hero-canvas in style.css - position: fixed, pointer-events:
   none). Still deliberately small and cheap: a capped device pixel
   ratio and a full pause when the tab isn't visible, so it reads as
   "quiet ambient motion," not a showpiece that competes with the form
   for attention or battery. Fails silently (falls back to the CSS
   gradient/glow already in style.css) if Three.js didn't load, e.g.
   an offline/CDN-blocked network. */
(function initHeroScene() {
  const canvas = document.getElementById('hero-canvas');
  if (!canvas || typeof THREE === 'undefined') return;

  const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(55, 1, 0.1, 100);
  camera.position.z = 18;

  const NODE_COUNT = 60;
  const positions = new Float32Array(NODE_COUNT * 3);
  for (let i = 0; i < NODE_COUNT; i += 1) {
    positions[i * 3] = (Math.random() - 0.5) * 40;
    positions[i * 3 + 1] = (Math.random() - 0.5) * 20;
    positions[i * 3 + 2] = (Math.random() - 0.5) * 10;
  }

  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));

  // v3.1.1: soft glow sprite (a small radial-gradient canvas texture)
  // instead of a flat square dot, combined with additive blending -
  // this is what gives each particle a genuine glow instead of a hard
  // point, without pulling in a full postprocessing/bloom pipeline.
  const glowCanvas = document.createElement('canvas');
  glowCanvas.width = 64;
  glowCanvas.height = 64;
  const glowCtx = glowCanvas.getContext('2d');
  const glowGradient = glowCtx.createRadialGradient(32, 32, 0, 32, 32, 32);
  glowGradient.addColorStop(0, 'rgba(255, 255, 255, 1)');
  glowGradient.addColorStop(0.35, 'rgba(255, 158, 92, 0.92)');
  glowGradient.addColorStop(1, 'rgba(255, 107, 0, 0)');
  glowCtx.fillStyle = glowGradient;
  glowCtx.fillRect(0, 0, 64, 64);
  const glowTexture = new THREE.CanvasTexture(glowCanvas);

  const material = new THREE.PointsMaterial({
    map: glowTexture,
    color: 0xff9e5c,
    size: 0.4,
    transparent: true,
    opacity: 0.95,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
    sizeAttenuation: true,
  });
  const points = new THREE.Points(geometry, material);
  scene.add(points);

  // Sparse connecting lines between nearby nodes - a subtle "network"
  // read without an expensive all-pairs distance check every frame
  // (computed once, since the layout is static apart from a slow
  // overall rotation).
  const linePositions = [];
  const maxDistance = 7;
  for (let i = 0; i < NODE_COUNT; i += 1) {
    for (let j = i + 1; j < NODE_COUNT; j += 1) {
      const dx = positions[i * 3] - positions[j * 3];
      const dy = positions[i * 3 + 1] - positions[j * 3 + 1];
      const dz = positions[i * 3 + 2] - positions[j * 3 + 2];
      const dist = Math.sqrt(dx * dx + dy * dy + dz * dz);
      if (dist < maxDistance) {
        linePositions.push(
          positions[i * 3], positions[i * 3 + 1], positions[i * 3 + 2],
          positions[j * 3], positions[j * 3 + 1], positions[j * 3 + 2],
        );
      }
    }
  }
  const lineGeometry = new THREE.BufferGeometry();
  lineGeometry.setAttribute('position', new THREE.BufferAttribute(new Float32Array(linePositions), 3));
  const lineMaterial = new THREE.LineBasicMaterial({
    color: 0xff6b00,
    transparent: true,
    opacity: 0.34,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
  });
  const lines = new THREE.LineSegments(lineGeometry, lineMaterial);
  scene.add(lines);

  function resize() {
    const width = window.innerWidth;
    const height = window.innerHeight;
    renderer.setSize(width, height, false);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
  }
  resize();
  window.addEventListener('resize', resize);

  let frameId = null;
  let visible = true;
  document.addEventListener('visibilitychange', () => {
    visible = document.visibilityState === 'visible';
    if (visible) animate();
  });

  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  let pulseT = 0;

  function animate() {
    if (!visible) return;
    if (!prefersReducedMotion) {
      points.rotation.y += 0.0009;
      lines.rotation.y += 0.0009;
      points.rotation.x += 0.0002;
      lines.rotation.x += 0.0002;

      // Slow breathing pulse on the glow, for a sense of depth rather
      // than a perfectly static particle brightness.
      pulseT += 0.012;
      const pulse = 0.85 + Math.sin(pulseT) * 0.12;
      material.opacity = pulse;
      material.size = 0.4 + Math.sin(pulseT) * 0.05;
    }
    renderer.render(scene, camera);
    frameId = requestAnimationFrame(animate);
  }
  animate();
})();

/* ==================================================================
   GSAP scroll-triggered reveals
   ================================================================== */
(function initScrollAnimations() {
  if (typeof gsap === 'undefined') return;
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

  if (typeof ScrollTrigger !== 'undefined') {
    gsap.registerPlugin(ScrollTrigger);
  }

  // Header content: a gentle staggered entrance on load (not
  // scroll-tied - it's above the fold, so it should greet the
  // visitor immediately). .feature-pill already has its own CSS
  // keyframe stagger (see @keyframes highlightIn in style.css) so
  // it's deliberately left out here to avoid double-animating it.
  // .form-wrap has its own separate fade+rise too (@keyframes formEnter).
  gsap.from('.logo-row-center, .main-heading, .sub-heading, .supporting-text', {
    opacity: 0,
    y: 16,
    duration: 0.65,
    stagger: 0.1,
    ease: 'power2.out',
  });

  if (typeof ScrollTrigger !== 'undefined') {
    // Each form section fades/slides in as it enters the viewport,
    // and the whole form card lifts in once when it first appears.
    gsap.utils.toArray('.form-card-section').forEach((section, index) => {
      gsap.fromTo(
        section,
        { opacity: 0, y: 18 },
        {
          opacity: 1,
          y: 0,
          duration: 0.5,
          delay: index * 0.03,
          ease: 'power2.out',
          scrollTrigger: {
            trigger: section,
            start: 'top 88%',
            toggleActions: 'play none none none',
          },
        },
      );
    });
  }
})();
