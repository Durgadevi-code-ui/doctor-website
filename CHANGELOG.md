# Changelog

## v3.2 — Single-column redesign: dark theme, new logo, new branding

A larger, deliberate design pivot (per direct request, superseding the
prior split-layout design) rather than an incremental patch - but
still scoped tightly: **only the public intake page**
(`app/templates/index.html`) changed structurally and visually. The
admin login/OTP/dashboard pages, all backend routes, validation,
Supabase models, and authentication are untouched.

### Files changed
- `app/templates/index.html` - full rewrite (layout only; every form
  field id/name/structure copied verbatim from the prior version).
- `app/static/css/style.css` - major edit: removed the obsolete
  two-column classes, added the new single-column layout classes, and
  added a **scoped** dark-theme variable override (see below).
- `app/static/js/script.js` - GSAP entrance-animation selectors
  updated to match the new class names; Three.js colors aligned to
  the exact new brand orange.
- `app/static/images/agentic-atoms-mark.png`,
  `agentic-atoms-full.png`, `favicon-32.png`, `app/static/favicon.ico`
  - replaced with the newly provided logo (same filenames, so no
    template changes were needed for the image paths themselves).
- `CHANGELOG.md` - this entry.

### 1. New brand colors, scoped correctly
Rather than overwriting the shared `:root` palette (which would have
also flipped the admin login/OTP/dashboard to dark mode - explicitly
not requested), the new palette lives in a separate
`body.dark-intake` override block, applied only via a class on
`index.html`'s `<body>`:
```
--bg: #050505;       --primary: #FF6B00;
--panel: #121212;    --text-primary: #FFFFFF;
```
Because every existing component rule in this stylesheet already
read its colors from CSS variables (`var(--bg)`, `var(--primary)`,
etc.), this one override block re-themed the buttons, chips,
checkboxes, progress bar, banners, and success screen correctly with
no per-component edits needed for color alone. A `--primary-rgb`
helper variable was added (`249, 115, 22` light / `255, 107, 0` dark)
so glow effects using `rgba(var(--primary-rgb), 0.4)` also follow
whichever theme is active, instead of being stuck on one hardcoded
orange regardless of page.

**Three real bugs found and fixed during verification**, all from
rules that had a hardcoded `#FFFFFF` background left over from the
light-only design (which would have made white input/chip text
invisible, and shown a stark white bar, on the new dark page):
- `input`/`select`/`textarea` and `.chip` base rules kept their
  original `#FFFFFF` (so admin's inputs/chips are pixel-identical to
  before) and got a new `body.dark-intake input, ... { background:
  var(--panel-raise); }` override instead.
- `.progress-wrap`'s sticky background (only ever rendered on the
  public page) was changed directly from a hardcoded white
  translucent fill to a dark one.
- Confirmed the two other remaining `#FFFFFF` hits in the file
  (`.refresh-btn`, `.pagination button`) are admin-dashboard-only
  components and correctly left untouched.

### 2. New logo
The provided logo image replaced `agentic-atoms-mark.png` (used at
small size across the hero, admin login, OTP, and dashboard topbar)
and `agentic-atoms-full.png`, plus regenerated favicons - same
filenames as before, so every template's `<img>`/`<link rel="icon">`
tag picked it up with zero template edits for the path itself. The
new logo is already a clean, full-bleed circular icon (no wordmark
text baked in), so no re-cropping was needed this time.

### 3. Single centered form (split layout removed)
The old two-column `.shell` (`.brand-panel` left / `.form-panel`
right) grid was removed entirely. The new top-to-bottom order on
`index.html`:
1. Logo (centered, enlarged to 84px for this placement)
2. "Agentic **Atoms**" heading (orange accent on "Atoms")
3. "AMCANA Meet Intake Form" subheading (orange underline/glow accent)
4. Supporting text
5. A compact feature-pill strip (the previous "highlight cards"
   marketing content, moved here from the old left column, restyled
   as slim pills rather than large cards so it stays subordinate to
   the heading hierarchy)
6. The centered form card (max-width 640px, rounded, subtle
   orange-tinted border/glow via `--shadow-raised`)
7. A simple centered text footer ("Agentic Atoms · AMCANA Meet · 2026")

### 4. Animations
- Page load: header content (logo, heading, subheading, supporting
  text) fades + rises in via GSAP (`gsap.from(...)`, staggered); the
  feature pills keep their own existing CSS keyframe stagger
  (deliberately left out of the GSAP call to avoid double-animating
  them); the form card fades + rises in via a dedicated CSS
  `@keyframes formEnter`.
- Existing effects unchanged: GSAP ScrollTrigger section reveals,
  progress bar (sticky, left-aligned, slide-from-left step
  transition), input focus glow, button hover, loading spinner,
  validation icons, success screen.
- Three.js background: same particle/node/connection/glow
  implementation as before, colors aligned to `#FF6B00`, opacity
  raised (0.62 → 0.75) since it now sits against a true black page
  background rather than a light one, so it can be more prominent
  without hurting text contrast (the form card itself is a fully
  opaque surface, independent of canvas brightness).

### Explicitly unchanged
- All Flask routes, the admin authentication/2FA flow, the admin
  dashboard's own layout/theme, Supabase/SQLAlchemy models, CRUD
  logic, form validation, and every form field's id/name/behavior.

---

## v3.1.3 — Progress indicator: sticky + left-position hardening

Follow-up fix to v3.1.1/v3.1.2. Only `app/static/css/style.css` and
`app/static/js/script.js` touched - no other files in this patch.

### 1. Left position hardened
- The label was already first in DOM order with `flex-shrink: 0` from
  v3.1.1, which should already render on the left - but to remove any
  ambiguity, `.progress-label`/`.progress-track` now also carry
  explicit `order: 0` / `order: 1`, and `.progress-wrap` explicitly
  sets `flex-direction: row`. The label's position no longer depends
  on DOM order alone.
- Also found and removed a leftover **duplicate** `.progress-label`
  CSS block further down the same file (from before the horizontal
  layout existed) - harmless since it repeated the same property
  values, but removed for a clean single source of truth.

### 2. Sticky scroll behavior (the real fix in this patch)
- `.progress-wrap` changed to `position: sticky; top: 0;` with a
  translucent white + `backdrop-filter: blur()` background, a bottom
  border for separation, and `z-index: 5`. Previously the indicator
  had no special positioning and simply scrolled away with the rest
  of `.form-card`'s (very tall) content - meaning it was really only
  visible for Step 1, exactly as reported.
- It now stays pinned to the top of the viewport for the entire
  scroll through the form (from the moment the "Intake Form" title
  scrolls past, until the last field), then scrolls away naturally
  once the form card itself ends - no JS/IntersectionObserver
  needed, this is a pure CSS fix.
- Verified `.form-card` (its containing block) has no `overflow`
  property that would break sticky positioning.

### 3. Animation adjusted to slide-from-left
- `setProgressStep()` in `script.js` changed from a vertical fade
  (fade + slight upward move) to a fade + **slide-from-left** (`x: -6
  → 0`), matching the more specific animation request. Still GSAP-
  driven with an instant-swap fallback if GSAP isn't loaded, and still
  only fires when the step number actually changes.

### Explicitly unchanged
- Form fields, validation, backend logic, Supabase, authentication,
  the existing theme/logo, and every other animation - only the
  progress indicator's CSS and its step-change transition function
  were touched.

---

## v3.1.2 — Heading text correction

Text-only change, nothing else touched.

- **`app/templates/index.html`**: the first form section's heading
  changed from "Who We're Talking To" to "Whom We're Talking To" (one
  `<legend>` element). No design, layout, animation, icon, or
  functionality changes - verified it's the only occurrence of that
  string in the template, and that the sibling section headings
  ("Practice Information", "Business Information", "Interested
  Services", "Anything Else") are unaffected.

---

## v3.1.1 — Orange theme refinement, Three.js glow improvements, progress bar layout

Follow-up refinement to v3.1 (requested and labeled "v3.1" in the
brief, filed here as v3.1.1 to distinguish it from the prior entry
without overwriting that history). UI-only, no architecture/backend
changes - same scope discipline as v3.1.

### 1. Fixed the "brown/muddy" orange look
- **Root cause identified**: `.brand-panel`'s dark background was
  ~93% opacity sitting *over* the light, mostly-transparent canvas/
  page background - a dark translucent layer blended with a light
  one desaturates toward brown/gray, which is exactly the dullness
  reported. This wasn't a wrong color choice so much as a wrong
  layering approach.
- **Fix**: `.brand-panel` is now a clean, nearly opaque (97%) deep
  espresso-black gradient (`rgba(20,11,4)` → `rgba(43,22,8)`) instead
  of relying on transparency to reveal the canvas through a dark
  wash. The premium "glow" moment in the hero now comes from three
  brighter, larger CSS glow blobs (two existing ones enlarged and
  intensified, one new central glow added) rather than from a muddied
  canvas bleed-through.
- **Palette values updated** to the exact refined spec: added a
  dedicated `--light-orange: #FFEDD5` token, `--panel-raise` aligned
  to the same value (was a slightly different `#FFF1E0`).
- Everything downstream of `--primary`/`--primary-deep`/`--teal`
  (buttons, chips, focus rings, progress fill, admin cards, etc.)
  automatically stays correct since those were already CSS variables
  - no per-component edits needed for the color fix itself.

### 2. Logo
- Untouched, as instructed - no logo files were modified.

### 3. Three.js background improvements
- **Particle glow**: points now use a soft radial-gradient canvas
  texture (generated at runtime, no new asset file) with additive
  blending, instead of flat square dots - this is what actually reads
  as "glow" rather than plain dots.
- **Connection visibility**: line opacity raised (0.18 → 0.34) and
  also switched to additive blending so the network connections read
  clearly against both the light form area and the now-darker hero.
- **Depth effect**: added a slow sine-wave "breathing" pulse to the
  particle glow's opacity and size in the render loop - a subtle,
  continuous effect rather than a one-time animation.
- **Canvas visibility**: overall canvas opacity raised 0.4 → 0.62, and
  the `.hero-canvas` CSS rewritten to the exact
  `position: fixed; top:0; left:0; width:100%; height:100%;`
  form requested (functionally identical to the prior `inset: 0`
  shorthand, just literal per spec).
- **Performance**: node count intentionally left at 60 (not
  increased) - the glow/blend/pulse improvements above affect
  rendering quality, not particle quantity, so GPU cost stays flat.

### 4. Scroll persistence
- Already fixed in v3.1 (`position: fixed` canvas) and unchanged
  here - re-verified still correct after the opacity/z-index edits
  above.

### 5. Progress indicator: layout + transition
- **Layout**: `.progress-wrap` changed from a stacked (bar, then
  label below) to a horizontal flex layout - "Step X / 4" now sits to
  the **left** of the bar, matching the
  `Step 2 / 4     █████████░░░░` example exactly.
- **Transition**: step-number changes now fade+slide via GSAP
  (`setProgressStep()` in `script.js`) - a quick fade-out/up, text
  swap, fade-in/settle - instead of an instant text replacement. Falls
  back to an instant swap if GSAP hasn't loaded, so the indicator
  never breaks if a CDN is blocked. Only fires when the step number
  actually changes (not on every keystroke), so it doesn't animate
  needlessly while a field is being typed into.
- The underlying bar-fill percentage math is still completely
  unchanged from v3.1, per "keep the existing progress bar."

### Explicitly unchanged
- Logo, GSAP ScrollTrigger reveals, glassmorphism cards, chip/
  checkbox groups, validation icons, loading spinner, success screen,
  admin authentication/2FA/dashboard, Supabase/SQLAlchemy models and
  CRUD logic, routes, and the overall project structure.

---

## v3.1 — Orange theme, full-page background, step-ratio progress

UI-only enhancement patch on top of v3.0. No architecture changes, no
new files, no backend/database/auth changes - see the "Explicitly
unchanged" note at the end of this entry.

### 1. Color theme: blue → orange
- `app/static/css/style.css` - every color token in `:root` updated:
  `--primary: #F97316` (was `#2563EB`), `--primary-deep: #C2410C`
  (was `#1D4ED8`), `--teal: #FB923C` (was `#0E7C86`, still used only
  by the progress-bar gradient), `--bg: #FFF7ED` (light cream, was a
  cool gray-blue `#F4F7FA`), `--panel-raise: #FFF1E0`,
  `--text-secondary: #78716C` (warm stone, was a blue-gray).
  Because every button, input focus ring, chip, checkbox accent,
  link/hover color, card accent border, and progress fill already
  referenced these variables (not hardcoded hex), the whole site -
  buttons, nav-style elements, cards, form controls, icons, hover/
  focus states, borders, shadows, and the progress bar - re-themes
  from this one edit.
- Hardcoded (non-variable) colors also swapped: the hero panel's dark
  gradient (`#10233F/#123655` navy → `#241206/#3D230F` warm espresso,
  in both `style.css` and `admin.css`), the hero eyebrow badge,
  brand-mark accent, stat values, highlight-card copy, and glow-sphere
  colors (all previously blue-tinted hex/rgba, now orange/warm-tinted).
  Success (green) and error (red) colors were deliberately left
  unchanged - those are semantic, not part of the brand palette, and
  changing them would reduce clarity, not improve it.
- `app/static/js/script.js` - the Three.js particle color (`0x7db8ff`
  → `0xfdba74`) and connecting-line color (`0x2563eb` → `0xf97316`)
  updated so the animated background matches the new theme too, not
  just the static UI.
- Shadows (`--shadow`, `--shadow-raised`) shifted from a neutral
  cool-gray tint to a warm dark tint, so drop shadows read as part of
  the same warm palette rather than clashing with it.

### 2. Logo replacement
- **Completed in this follow-up** - the official Agentic Atoms logo
  (a circular badge: atom-orbit + robot mark, "AGENTIC ATOMS" wordmark,
  and the company URL) was provided as an image and processed into two
  assets:
  - `app/static/images/agentic-atoms-mark.png` - the icon cropped out
    of the full badge (atom/robot only, no text), used everywhere the
    logo appears at small size (hero, admin login, admin OTP, admin
    dashboard topbar) - the wordmark text is already shown separately
    next to it in all four places, so cropping out the now-redundant
    (and illegible-at-that-size) text keeps the small badge crisp.
  - `app/static/images/agentic-atoms-full.png` - the untouched original
    badge, kept available for any future larger placement.
  - `app/static/favicon.ico` (16/32/48px) and
    `app/static/images/favicon-32.png`, generated from the same crop.
- **`app/templates/index.html`, `admin_login.html`, `admin_otp.html`,
  `admin_dashboard.html`**: the inline-SVG/plain-text `.logo-placeholder`
  content replaced with `<img src=".../agentic-atoms-mark.png">` in
  each; a `<link rel="icon">` pair added to each page's `<head>` for
  the favicon. No layout changes - the image fills the exact same
  34px circular frame the placeholder already occupied.
- **`app/static/css/style.css`**: added `.logo-img` (fills the circular
  frame via `object-fit: cover` + `border-radius: 50%`) and gave
  `.atom-logo` `overflow: hidden` so the image is clipped to the
  circle rather than the frame's own background color/glow ring
  showing through unclipped corners.
- There's no separate "footer logo" slot in the current design - the
  hero panel's bottom row (`.brand-foot`) is a text-only line
  ("Customer records" / date), not a logo placement, so nothing was
  added there in order to avoid changing that element's layout.

### 3 & 4. Full-page Three.js background + persists through scroll
- **`app/templates/index.html`**: `<canvas id="hero-canvas">` moved
  out of `.brand-panel` to be a direct child of `<body>`, before
  `.shell` - so it's a page-level layer, not scoped to one column.
- **`app/static/css/style.css`**:
  - `.hero-canvas` changed from `position: absolute` (sized to its
    old parent, `.brand-panel`) to `position: fixed; inset: 0; width:
    100vw; height: 100vh;` - a fixed element never scrolls with the
    page, which is what fixes the "background disappears while
    scrolling" issue (previously, `.brand-panel` fell back to
    `position: relative` below the 860px breakpoint, so its canvas
    scrolled away with it on tablet/mobile).
  - `.shell` given `position: relative; z-index: 1` so all page
    content explicitly paints above the fixed canvas (z-index: 0).
  - `.brand-panel`'s background changed from a fully opaque gradient
    to the same gradient at ~93% opacity (`rgba(...)`), and
    `.form-panel`'s background changed from opaque `var(--bg)` to
    `transparent` - both so the canvas is actually visible behind the
    hero and the form, not just present-but-hidden underneath an
    opaque layer. The `.form-card` itself (where the actual form
    content lives) stays fully opaque white, so text contrast is
    completely unaffected.
  - Canvas opacity reduced slightly (0.55 → 0.4) since it's now
    visible behind readable form text across the full page, not just
    behind the hero's headline.
- **`app/static/js/script.js`**: `initHeroScene()`'s resize logic
  changed from sizing against `canvas.parentElement` (no longer
  meaningful now that the canvas isn't nested in `.brand-panel`) to
  `window.innerWidth`/`innerHeight`. Particle count increased 42 → 60
  and the spatial spread widened, so the network still reads as full
  and intentional across the now much wider full-page canvas rather
  than looking sparse. `pointer-events: none` was already present
  from v3.0 and is unchanged - clicking through to form fields was
  never at risk.

### 5. Progress indicator: percentage → Step ratio
- **`app/templates/index.html`**: label markup changed from
  `<span id="progress-percent">0</span>% complete` to `Step
  <span id="progress-percent">1</span> / 4`.
- **`app/static/js/script.js`**, `updateProgress()`: the bar-fill
  width calculation is **completely unchanged** (still the same
  completed-required-fields ÷ total-required-fields ratio it always
  was). Only the text written into `#progress-percent` changed - from
  the raw percentage to a step number 1-4, computed as
  `Math.ceil(percent / 25)` (clamped to 1-4), so each quarter of
  completion advances one step.

### Explicitly unchanged (per this request's scope)
- GSAP ScrollTrigger reveals, glassmorphism highlight cards, floating
  glow spheres, chip/checkbox groups, validation icons, loading
  spinner, success screen, admin authentication/2FA/dashboard,
  Supabase/SQLAlchemy models and CRUD logic, and the overall project
  structure - none of these were touched. The only backend-adjacent
  file affected at all is `app/static/css/admin.css` (color values
  only, inherited from the shared theme - no layout or logic change),
  and `app/templates/index.html`/`app/static/js/script.js` (canvas
  placement, resize logic, and progress label text only).

---

## v3.0 — Branding, hero redesign, privacy lockdown, and admin 2FA

This release patches the existing v2.1 project. No new top-level
folders were created; new files were added only where the requested
functionality genuinely didn't exist before (an admin auth system
can't be "just a CSS change") - every new file is called out below
with why it was necessary.

### Branding
- Every "Agentic Items" occurrence replaced with "Agentic Atoms"
  (page title, brand wordmark, success-screen copy, code comments).
- Added an atom-icon logo placeholder (inline SVG, orbiting-ellipse
  mark) in the hero, admin login, OTP, and dashboard pages. Swap it
  for the real logo file by replacing the `.atom-logo` markup with an
  `<img>` tag - no other changes needed (see the comment in
  `app/static/css/style.css` right above `.atom-logo`).

### Hero section redesign
- Full visual rebuild of the left panel: large logo, "AI Built For
  Modern Healthcare Practices" headline, a small eyebrow badge, and
  four glassmorphism highlight cards (`backdrop-filter: blur()`,
  translucent borders).
- **Three.js** (`app/static/js/script.js`, `initHeroScene()`): a
  lightweight particle/node network (42 points, sparse connecting
  lines, slow rotation) rendered into a `<canvas>` behind the hero
  content. Capped pixel ratio, pauses via the Page Visibility API when
  the tab isn't active, and respects `prefers-reduced-motion`.
- **GSAP + ScrollTrigger** (same file, `initScrollAnimations()`): a
  staggered entrance for the hero copy on load, and a fade/slide-in
  for each form section as it scrolls into view.
- Both libraries load from CDN (cdnjs) and the hero scene/animations
  fail silently (falling back to the static CSS gradient/glow) if a
  CDN is blocked or the libraries don't load - this was not testable
  end-to-end in the offline sandbox this patch was written in; see
  the final summary for what to verify once deployed.
- Two CSS-only floating glow spheres (`.brand-panel::before/::after`)
  add ambient motion with no JS/GPU cost.

### Page title & label capitalization
- `<h2>` "Agentic Items Entry Form" → `<h1 class="intake-title">Intake
  Form</h1>`, large centered typography per spec.
- Every legend/label reviewed for Title Case: "Who We're Talking To",
  "Practice Information", "Business Information", "Interested
  Services", "Anything Else", and all field labels ("Your Name",
  "Phone Number", "Practice Type", etc.).

### Form UI modernization
- Rounded inputs, soft shadows, and hover/focus states already existed
  from v2.1's Google-Forms-inspired redesign and are unchanged here.
- **New:** a loading spinner inside the Submit button
  (`.submit-spinner`, driven by `.is-loading` toggled in
  `script.js`) - the button previously only showed disabled text.
- **New:** lightweight validation icons - a green check or red X
  appears inside required fields based on native `checkValidity()`
  (see `attachValidationIcons()` in `script.js`). This is UX feedback
  only; `app/utils/validators.py` remains the authoritative check.

### Stronger email/phone validation
- Email regex tightened to reject a local-part or domain that starts/
  ends with a dot, and consecutive dots (`user@.com`, `a@b..com`,
  `.abc@example.com` now correctly rejected; verified against 9 cases
  including every example from the spec).
- Phone validation unchanged in shape (digits + `+ - ( )`, minimum 7
  digits) - already correct for the "reject incorrect length" and
  "accept a leading country code" requirements from v2.1.

### Duplicate identification & messaging
- Confirmed email + phone are still the two unique identifiers
  (`app/models/customer.py` - both columns already `UNIQUE`).
- Duplicate message text updated everywhere (service layer, JS
  fallback, tests) from "Customer already exists." to **"This email
  or contact number is already registered."**

### Success page
- Copy updated to match the spec exactly: a ✅ mark, "Thank You!", and
  "Your information has been received successfully." The existing
  "Add Another Customer" button/reset behavior (built in v2.1) was
  kept as-is - it already does everything requested (clears the form,
  returns to a fresh intake form) without a page reload/redirect,
  which is a smoother experience than a hard redirect and was judged
  not worth downgrading.

### Public dashboard removed (privacy requirement)
- **`app/routes/customer_routes.py`**: trimmed from 7 endpoints down
  to 1 (`POST /api/customers` only). The public `GET`/`PUT`/`DELETE`/
  `/stats`/`/export` endpoints are gone, not just hidden in the UI -
  verified with a regression test
  (`test_public_read_update_delete_endpoints_removed`).
- The public intake page's customer-count/specialty-breakdown display
  was also removed from the hero panel, on the reasoning that even an
  aggregate count is customer-submission data and the requirement was
  read as "no customer data on the public page," not just "no table."
- All of that functionality (list/search/filter/paginate/get/update/
  delete/export/stats) still exists, unchanged in its business logic
  - it moved to the new authenticated `/admin/api/*` routes.

### New: Admin authentication + 2FA + dashboard
New files were required here because none of this existed before:
- `app/models/admin_user.py` - `AdminUser` model: hashed password
  (werkzeug), hashed OTP with expiry + attempt-limit (5 tries).
- `app/routes/admin_routes.py` - `/admin/login` (factor 1) →
  `/admin/verify-otp` (factor 2, email) → session-based dashboard
  access; plus the protected `/admin/api/*` CRUD/search/filter/
  paginate/export/stats endpoints (moved from the old public blueprint).
- `app/utils/security.py` - `send_otp_email()` (logs the code instead
  of failing when SMTP isn't configured - see README), `log_audit()`,
  and the `admin_login_required` decorator.
- `app/templates/admin_login.html`, `admin_otp.html`,
  `admin_dashboard.html` + `app/static/js/admin.js` +
  `app/static/css/admin.css` - the login/OTP forms and the dashboard
  UI (stats cards, search/filter/pagination table, edit modal, CSV
  export, logout).
- `flask create-admin` CLI command (in `app/__init__.py`) to bootstrap
  the first admin account - deliberately not a web route, so account
  creation is an operator action, not something reachable over HTTP.
- `admin_users` table added to `schema.sql`.

### Security hardening
- **CSRF**: Flask-WTF enforced on the three admin form routes (login,
  OTP, logout) via manual `validate_csrf()` calls; the public and
  admin JSON APIs are exempted at the blueprint level since they don't
  submit a session-backed HTML form (see the comment block in
  `app/__init__.py` for the reasoning).
- **Rate limiting**: Flask-Limiter added (`app/database.py`, shared
  `limiter` instance) - 10/minute on login and OTP verification,
  30/hour on the public intake endpoint, 200/hour default elsewhere.
- **Secure headers**: `X-Content-Type-Options`, `X-Frame-Options`,
  `Referrer-Policy`, `Permissions-Policy`, a scoped
  `Content-Security-Policy` (allowing only the specific CDNs this app
  actually loads from), and `Strict-Transport-Security` outside debug
  mode - all added via `after_request` in `app/__init__.py`.
- **Session cookies**: `HttpOnly`, `Secure` (disabled automatically in
  `DevelopmentConfig`/`TestingConfig` so local `http://` testing isn't
  broken), `SameSite=Lax`, 8-hour lifetime.
- **Audit logging**: every admin login attempt (success/failure), OTP
  attempt, customer edit, delete, and CSV export is logged via
  `log_audit()` into the existing rotating `logs/app.log`.
- **Input sanitization**: unchanged from v2.1 - server-side validation
  in `app/utils/validators.py`, HTML-escaping of all customer-supplied
  values before DOM insertion in the frontend JS.

### Tests
- `tests/test_customers_api.py` rewritten for the trimmed public API
  (create + validation + duplicate scenarios + the removed-routes
  regression guard).
- `tests/test_admin_routes.py` (new) - the full password→OTP login
  flow (with `send_otp_email` monkeypatched to capture the code so the
  test doesn't need a real mailbox), wrong-OTP rejection, auth-required
  checks on the dashboard and API, and full CRUD through the admin API.
- `tests/conftest.py` - added an `admin_user` fixture and a
  `extract_csrf_token()` helper the admin tests use to submit a real
  token, the same way a browser would.

### Known trade-offs / follow-ups
- **OTP delivery**: `send_otp_email()` sends real SMTP mail if
  `SMTP_HOST` is configured, otherwise logs the code. This sandbox has
  no mail server or SMTP credentials available, so the email path
  itself could not be exercised end-to-end here - the OTP
  generation/hashing/expiry/attempt-limit logic (the security-critical
  part) is covered by `test_admin_routes.py`; wiring in a real SMTP
  provider is a config change, not a code change.
- **Three.js/GSAP**: could not be visually verified in a real browser
  in this sandbox (no network access to fetch the CDN scripts or
  render a page). The code was written defensively (checks
  `typeof THREE`/`typeof gsap` before using them) so a blocked CDN
  degrades to the static CSS background rather than throwing, but
  please do a visual check after deploying.
- **Admin edit modal**: doesn't expose a "specify your practice"
  field for changing a record's `practice_type` to "Other" after the
  fact (the public intake form's conditional field wasn't duplicated
  into the admin modal). Editing everything else works; this one
  combination needs a direct database edit for now.
- **Stats breakdown by interested service** (carried over from v2.1):
  still groups by the exact comma-joined string rather than splitting
  multi-select values into per-service counts.

---

## v2.1 — Washington DC Doctors Meet intake revision

This release **patches** the existing v2.0 project for use as a booth
intake form. No new folders, no new architecture, no rewritten
backend routes - see the list below for exactly what changed and why.

### Branding
- Page title and form heading changed to "Agentic Items Entry Form".
- Added a logo placeholder + "Agentic Items" wordmark in the brand panel.
- Full color palette swapped from the prior dark/amber theme to a
  professional healthcare palette (clinical blue primary, teal accent,
  light backgrounds), in a Google-Forms-inspired card layout.

### Form fields
- **Customer Role** — options replaced with Doctor (default), Owner,
  Manager, Director.
- **Practice Type** — new required field (Medical Practice, Medical
  Spa, Dental Practice, Orthodontics, Other), with a conditional
  "Please specify your practice" textbox when "Other" is selected.
  *Schema change:* added `practice_type` and `practice_type_other`
  columns (see `app/models/customer.py`, `schema.sql`) - this was the
  one schema change required to support a field requested in the new
  spec that didn't exist before.
- **Specialty** — replaced with the full clinical specialty list
  requested (General Physician, Cardiologist, ... Other). No schema
  change (still a `VARCHAR(100)`).
- **Front-desk pain point** — option list replaced; question label
  for daily call volume updated to "Approximately how many calls does
  your front desk receive each day?"
- **Interested Services** — converted from a single-select chip group
  to multi-select checkboxes (AI Receptionist, AI Chatbot, Custom App,
  Website Enhancement). Stored as a comma-joined string in the
  existing `interested_service` column, widened from `VARCHAR(100)`
  to `VARCHAR(255)` to comfortably fit all four selections joined.

### Duplicate validation
- Simplified from three distinct messages (phone/email/both) down to
  a single **"Customer already exists."** whenever either the phone
  number OR the email matches an existing customer. Customer names
  are never checked for duplicates. See
  `app/services/customer_service.py`, `_find_duplicate()`.

### New UI elements
- **Progress bar** with animated fill and a live percentage, tracking
  completion of the required fields.
- **Company highlights** panel (30-Day Deployment, AI Receptionist,
  AI Chatbot, Custom Solutions) added to the brand panel.
- **Success screen** — "Thank you for submitting the form." with an
  "Add Another Customer" button that fully resets the form.

### Explicitly unchanged
- All API routes and their request/response contracts
  (`app/routes/customer_routes.py`).
- The customer records dashboard's refresh/search/filter/pagination
  behavior (`app/static/js/script.js` - see the block below the
  `/* ---------- Form submission ---------- */` comment, which was
  left untouched apart from the file above it).
- The overall project/folder structure.

### Database: Supabase migration
- See README, "Supabase Setup", for the full walkthrough.
- `app/config.py` now normalizes `DATABASE_URL` (accepts Supabase's
  `postgresql://` scheme, adds `sslmode=require` automatically for
  `*.supabase.co` hosts) - no other database code changed.
- `.env.example` updated with Supabase connection string guidance.

### Known trade-off
- The bonus `/api/customers/stats` endpoint's "by interested service"
  breakdown now groups by the exact comma-joined string (e.g. "AI
  Receptionist, AI Chatbot" is its own bucket, distinct from "AI
  Receptionist" alone), since that endpoint wasn't part of the
  requested changes and reworking it to split multi-select values
  would be a larger change than this patch scope covers. The
  **filter** on `GET /api/customers?interested_service=` was
  adjusted (contains-match instead of exact-match) so filtering still
  works correctly; only the stats breakdown has this cosmetic
  granularity trade-off.
