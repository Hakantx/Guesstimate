# Guesstimate — Mobile and App Store Strategy

Read alongside `ROADMAP.md` and `FEATURES.md`. This document covers shipping
Guesstimate to the App Store and Google Play, and the constraints that shape
how.

---

## The constraint that decides everything

The development machine is a 2017 Intel MacBook Pro. It runs macOS Ventura at
best — Sonoma and later dropped 2017 hardware.

Since April 28, 2026, App Store Connect rejects any upload not built with
Xcode 26 and the iOS 26 SDK. Xcode 26 requires a macOS this machine cannot
install.

**Native Swift development is therefore off the table**, and so is any local
iOS build of any kind — Capacitor, React Native, Flutter, all of them
ultimately shell out to Xcode.

Two consequences:

1. The app is a web app first, wrapped second. Not a compromise — it means one
   codebase serves the site, the iOS app, and the Android app.
2. The iOS build and submission happen on a GitHub Actions macOS runner, which
   ships with current Xcode. Public repositories get free minutes. Local
   development never touches Xcode.

Android has no such problem. Android Studio runs on Intel macOS. Build,
debug, and submit entirely from this machine.

---

## Stack decision

| Layer | Choice | Why |
|---|---|---|
| Game | React + TypeScript + Vite | already the Phase 7 stack, no change |
| Solver | TypeScript port, or Python compiled to WASM | must run on-device for offline play |
| Shell | Capacitor | thin native wrapper, web assets bundled, real plugin access |
| iOS build | GitHub Actions `macos-latest` runner | the only path to Xcode 26 from this hardware |
| Android build | Android Studio, locally | works on Intel macOS |

Capacitor over React Native because the web app already exists and would have
to be rewritten for RN. Capacitor over a plain PWA-only approach because the
App Store does not list PWAs.

### The solver has to move client-side

Phase 6 puts game state on the server so the secret never reaches the browser.
That is correct for the web, and wrong for a mobile app that must work on a
plane. For the app build, the solver runs on-device and the secret lives in
app memory.

This is a real architectural fork and it needs deciding before Phase 7 code is
written. The cleanest answer: port `core/` and `solvers/` to TypeScript, keep
the Python as the reference implementation, and add a test that runs the same
1000 seeded games through both and asserts identical results. That
cross-language equivalence suite is a genuinely strong thing to have in a repo.

---

## App Store review: the 4.2 problem

Apple rejects apps that are a website in a shell. Guideline 4.2, "minimum
functionality," is the single most likely reason this gets bounced.

The app must therefore do things a browser tab cannot:

- **Full offline play.** No network required for any mode. This is the biggest
  single signal and it follows from moving the solver on-device.
- **Haptics.** A light tap per bull, a different pattern for cows, a solid one
  for the win. Capacitor Haptics plugin.
- **Local notifications.** A daily challenge reminder, opt-in, scheduled
  locally — no push server needed.
- **Native share sheet** for the result grid, not a clipboard copy.
- **Home screen widget** showing the daily challenge and current streak. Real
  work, and about as clear a "this is a native app" signal as exists.
- **Game Center** leaderboards and achievements, optional but it makes the app
  legibly a game to a reviewer.
- Proper app icon, launch screen, safe-area handling, dark mode, Dynamic Type.

Do not submit until offline play and haptics are both working. Those two alone
clear most of the 4.2 risk.

---

## Order of operations

**Ship Android first.** $25 one-time versus $99/year, review measured in days,
and it builds locally on this hardware. Get the whole pipeline — signing,
store listing, screenshots, privacy policy — working there where iteration is
cheap. Then do iOS with everything already proven.

### Phase 12 — PWA foundation

Comes right after Phase 9. Before any store work:

- Service worker, offline-first, full asset caching
- Web app manifest, maskable icons, splash screens
- Installable from Safari and Chrome — "Add to Home Screen" works and plays
  offline
- Solver ported to TypeScript with the cross-language equivalence test
- Touch targets sized properly, no hover-dependent interactions, safe areas
- Test on a real phone, not a resized desktop browser

**Done when:** you can install it from Safari, turn on airplane mode, and play
a full game.

This phase is worth doing even if the store apps never happen. It is most of
the value for none of the cost.

### Phase 13 — Capacitor and Google Play

- `npx cap add android`, wire the web build into the shell
- Haptics, local notifications, share sheet, status bar styling
- App icon and adaptive icon set, splash screens at every density
- Signing key generated and backed up somewhere that is not this laptop
- Play Console: $25, store listing, screenshots at required sizes, feature
  graphic, privacy policy URL, data safety form, content rating
- Internal testing track first, then production

**Done when:** it is installable from the Play Store.

### Phase 14 — iOS via CI

- `npx cap add ios` — the project generates fine on this machine, it just
  cannot be built here
- GitHub Actions workflow on `macos-latest`: install pods, build, sign,
  upload to TestFlight via `xcrun altool` or `fastlane pilot`
- Signing certificates and provisioning profiles stored as encrypted repo
  secrets. This is the fiddliest part of the whole project; expect a day of
  failed runs.
- TestFlight on your own device is the only debugging loop available. Budget
  for slow iteration — every fix is a full CI round trip.
- App Store Connect: listing, screenshots for each required device size,
  privacy nutrition labels, age rating, review notes
- In the review notes, state plainly that the app plays fully offline and list
  the native features. Reviewers do read these.

**Done when:** it is live on the App Store.

---

## Costs

| Item | Cost |
|---|---|
| Google Play Developer | $25, once |
| Apple Developer Program | $99/year, recurring |
| GitHub Actions macOS minutes | free for public repos |
| Domain, hosting | ~$15/year, optional |

Apple enrollment requires being the age of majority. If that is a problem,
Android alone is still a real shipped app.

---

## Build-time data, not startup-time data

The feedback matrices are precomputed and cached, and they must be produced
when an artefact is *built*, never when it starts.

For the server that is a Dockerfile step: a container spending 28.5 seconds
building a matrix before it can answer a health check gets killed and retried,
which reads as a crash loop rather than as slow warmup. For the mobile build
the same rule applies for a stronger reason — a phone should not spend half a
minute of CPU and battery recomputing something the build machine could have
shipped, and offline play means there is no server to fall back to while it
does.

That points at a constraint for the TypeScript port. A 3024-code matrix is 9 MB
as `uint8`, which is too much to bundle casually into an app or a service
worker cache. The options are to ship a compressed matrix, to ship the opening
book only and score the rest on demand, or to build the matrix once on first
launch and store it — and only the third preserves offline play on first run
without a large download. Whichever it is, it is a decision to make before
Phase 12 rather than during it.

## What this changes upstream

- **Phase 1** — the TypeScript port is easier if `core/` is written with a
  port in mind. Keep it small and dependency-free.
- **Phase 6** — server-authoritative state stays for the web, but the API must
  not be the only way to play. Design the game logic so the same interface can
  be backed by a local solver or a remote one.
- **Phase 7** — mobile is not an afterthought. The candidate grid is the
  signature element and it has to work at 360px. Design it there first, then
  scale up.
- **DESIGN.md** — needs an app icon. The punch-card grid collapsing to a single
  lit cell is the obvious mark, and it reads at 60px.

---

## The honest tradeoff

A polished PWA with a live URL gets most of the portfolio value for none of the
cost, none of the review risk, and none of the annual fee. The App Store
listing is worth it for one reason: almost nobody has one, and the story of
shipping to it from a machine incapable of building for it is a better
engineering anecdote than the listing.

Do not start Phase 12 until Phases 1 through 9 are done. A half-built game in
two app stores is worse than a finished one on the web.
