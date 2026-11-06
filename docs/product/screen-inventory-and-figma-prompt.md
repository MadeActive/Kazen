# Kazen — Complete Screen Inventory and Figma Flowchart Prompt

Companion to `ux-spec.md`. Sept 2026. Supersedes the earlier 35-item feature list.

**Framing (agreed):** Kazen is the companion app. It is a **second screen**, never a required screen. The Goal runs every game on its own via kicks and the one post button. Kazen makes setup, players, scores and sharing easier and more visual. Football first; arcade, throwing and party effects are secondary and sit lower in every list.

**How to read this:** every numbered line is one screen, sheet, or state that has to be designed. Bold = a full screen. Plain = a sheet, banner, dialog or state layered on a screen. `(v2)` = second release. `(hw)` = depends on an open hardware question. `(OS)` = a system dialog we trigger but don't design.

---

## Part 1 — Screen inventory (v1)

### 0. Outside the app
- 0.1 App Store / Play Store listing, reached from the QR on the Goal. (Screenshots and copy still need designing.)
- 0.2 (OS) Local network permission. Triggered on first Goal search.
- 0.3 (OS) Bluetooth permission. Triggered only if the network search fails. `(hw)`
- 0.4 (OS) Camera permission. Triggered only when the in-app QR scanner opens.
- 0.5 (OS) Notifications permission. Triggered late: the first time a new best is set, or when the parent enables a notification in Settings. Never on launch.
- 0.6 (OS) Photos permission. Triggered on first "Save clip".

### 1. Launch and pairing
- **1.1 Splash.** Wordmark, under one second. No copy.
- 1.2 Deep-link handler. QR opened the app: "Connecting to your Goal" with a spinner. Reads Goal ID + one-time token.
- 1.3 Pairing success → 2.1 (first run) if no players exist, else → 3.1 Home.
- 1.4 Pairing failed. Token expired or Goal not reachable. One line: "Look at your Goal and scan again." Buttons: **Scan again** (→ 1.7), **Find my Goal instead** (→ 1.8).
- **1.5 Welcome (cold open, nothing paired).** One sentence, two buttons: **Scan the QR on your Goal**, **Find my Goal**. Small link: "Don't have a Goal yet?" → 1.6.
- 1.6 No Goal yet. One paragraph and a link to the website. Dead end by design.
- **1.7 QR scanner.** Full-screen camera with a viewfinder. Cancel. On read → 1.2.
- **1.8 Find my Goal: searching.** Animated, "Stand near your Goal." Tries home network first, then Goal hotspot, then Bluetooth. `(hw)`
- 1.9 Find my Goal: results. List of Goals found (usually one). Tap → 1.10.
- 1.10 Confirm it's yours. The Goal flashes a colour; the app asks "Which colour is your Goal showing?" with four swatches. Correct → 1.3. Wrong → back to 1.9.
- 1.11 Find my Goal: nothing found. Three checks with pictures: plugged in and rippled, phone on same Wi-Fi, stand within 5 m. **Try again**, **Get help** (→ 7.15).
- 1.12 Cold open, Goal already paired → 3.1 Home directly, with connection state resolved in the background.
- 1.13 Connection state (global, not a screen). Direct / Home Wi-Fi / Offline. Every screen below respects it.

### 2. First run (under 90 seconds, three taps)
- **2.1 Last three kicks.** Three tiles: impact cross on a goal outline, speed, GOAL / SAVED. One button: **Keep these**.
- 2.2 Last three kicks, empty. Nobody has kicked yet: "Go and take three kicks, then come back." Button **Skip for now** → 2.3. (Rare path but the QR can be scanned early.)
- **2.3 Who kicked?** Name field, four colour swatches, **Done**. Creates a local profile on the Goal.
- 2.4 Name validation. Empty → "Player 1". Over 6 characters → inline note: "Shows as JONATH on the Goal" (truncation preview). Name already used → "That name's taken."
- 2.5 Add another kicker? Small link under Done: "Someone else kicked too" → repeats 2.3. Max once during first run.
- **2.6 Calibrate: instruction.** Illustration of the ball on the spot. "Put the ball on the spot and take one kick." Buttons: **I'm ready**, **Skip**. `(hw)`
- 2.7 Calibrate: waiting for the kick. Live, listens to the Goal. Cancel returns to 2.6.
- 2.8 Calibrate: success. "Speed calibrated." Auto-advances after 1.5 s → 3.1.
- 2.9 Calibrate: failed / skipped. "No problem, we'll show power instead of speed." → 3.1. Sets the speed-vs-power-bar flag globally.

### 3. Home ("Play")
- **3.1 Home.** Player chips row, game grid (football group first, arcade / party group second), Today's clips strip (hidden if none).
- 3.2 Home banner: Goal offline. "Can't reach your Goal." Tap → 8.2.
- 3.3 Home banner: Goal asleep. "Your Goal is asleep." Tap → wakes it (sends a wake command). Games can still be sent; the Goal wakes on send.
- 3.4 Home banner: Goal updating. Grid disabled, progress shown. → 7.9.
- 3.5 Home banner: game already running. Someone started a game from the post button. Tap → 4.2 Playing. (The app joins, it never interrupts.)
- 3.6 Player chip: tap toggles playing / not playing. At least one must stay selected; if all are off, Guest is implied.
- 3.7 Player chip: long-press → 5.2 Player detail.
- 3.8 Add player chip (+) → 5.4.
- 3.9 Game tile → the game's options sheet (3.10 to 3.18). Every sheet has the same layout: title, one or two controls, selected players echoed, **Start on Goal**.
- 3.10 Keeper options. Kicks (5, fixed for v1). Shows each selected player's current keeper as a read-only line ("Jake vs The Wall"). No difficulty control.
- 3.11 Shootout options. Needs 2+ players; if fewer are selected, the sheet shows the chips inline to add one. Kicks each (5).
- 3.12 Corners options. Kicks (10). Toggle: shrinking corners.
- 3.13 Targets options. Difficulty: Easy / Normal / Hard (a fade-out timer, but shown as three words).
- 3.14 Power options. Kicks (3). Shows the player's current best beneath.
- 3.15 Passing options. Passes (10).
- 3.16 Invaders options. Speed: Slow / Normal / Fast.
- 3.17 Whack-a-Mole options. Time (60 s, fixed).
- 3.18 Dodgeball options. Time (60 s, fixed). Note: "Use a soft ball."
- 3.19 Game unavailable state (on the tile). Greyed with a one-word reason: "2 players", "Needs full Goal" (single-panel prototype), "Coming soon" (v2 games shown but locked).
- 3.20 Sending to Goal. Brief overlay, "Sending…" → 4.1. Failure → toast "Couldn't reach your Goal" and stay on the sheet.

### 4. Playing ("Put me down", the second screen)
- **4.1 Waiting for first kick.** Game name, first player's name and colour, "Kick when ready." Nothing else.
- **4.2 Live.** Large score, large current player, kick n of N, last result block (result word, speed or power bar, impact cross on a small goal outline). Readable from 2 m. Small **End** link only.
- 4.3 WHO? pending. The Goal is asking who's kicking (someone walked up without a phone). The app mirrors it: player chips, tap to answer, or let the Goal's 5-second guest fallback run.
- 4.4 Turn change. The next player's name fills the screen for 1.5 s, then returns to 4.2.
- 4.5 Result flash. GOAL / SAVED / MISS / HIT / NEW BEST in the player's colour, 1.5 s, then back to 4.2. Matches the Goal's RESULT timing.
- 4.6 Keeper anticipation (Keeper and Shootout only). The keeper's silhouette and his current tell, shown small, purely for spectators. Optional to ship.
- 4.7 Connection lost mid-game. Overlay: "Lost your Goal. The game carries on without the phone." Reconnect automatically; on reconnect, resync score.
- 4.8 End confirm. Small sheet: "End the game for everyone?" **End**, **Keep playing**.
- **4.9 Round result.** Scores per player, winner, any NEW BEST, keeper beaten (if Keeper), count of clips kept. Buttons: **Play again**, **Share**, **Home**.
- 4.10 New keeper offer. Appears on 4.9 when a player has earned the next keeper: name, silhouette, one line. **Bring him on**, **Not yet**. Mirrors the Goal's NEW KEEPER? prompt; either place can answer.
- 4.11 Guest clip prompt. Appears on 4.9 when a Guest played: "Guest's best: 68 km/h. Send them the clip?" **Send** (→ 6.3), **No thanks**.
- 4.12 Play again → 3.20 with the same options. Share → 6.2 with the round's best clip. Home → 3.1.

### 5. Players ("Us")
- **5.1 Player list.** One row per player: avatar, name, this week in one sentence. Guest row at the bottom. **+** → 5.4.
- **5.2 Player detail.** Bests (speed, goals in a row, best target score, longest streak), keepers beaten row, heatmap (small), clips (grid). Edit (pencil) → 5.3.
- 5.3 Edit player sheet. Name, colour, **Save**. Link: **Remove player** → 5.6.
- 5.4 Add player sheet. Name, colour, **Done**. Same validation as 2.4.
- 5.5 Colour taken. If all four colours are in use, the sheet shows a fifth and sixth. (Goal WHO? screen only shows four; the rest are chosen by name in the app.)
- 5.6 Remove player confirm. "Remove Jake and his 212 kicks? This can't be undone." **Remove**, **Cancel**.
- **5.7 Keeper detail.** From the keepers row: name, silhouette, one-line description, beaten or not, date beaten. Rename link (local nickname, never shipped as a real name).
- **5.8 Heatmap full view.** Goal outline with hit density. Filter chips: All time / This week / by game.
- 5.9 Player detail, empty. New player with no kicks: "No kicks yet." Nothing else.
- 5.10 Guest detail. Read-only: this session's Guest bests and clips, with the clip-send button.

### 6. Clips and sharing
- 6.1 Today's clips strip (on Home). Horizontal, newest first, thumbnail with result word.
- **6.2 Clip viewer.** Plays the 4 s clip with the overlay (goal outline, impact cross, keeper dive, speed, result word). Buttons: **Share**, **Save**, **Delete**. One line: "Clips stay on your Goal until you share them."
- 6.3 (OS) Share sheet.
- 6.4 Fetching from Goal. Progress bar while the clip downloads or renders. `(hw: renders on Goal or on phone)`
- 6.5 Clip gone. Overwritten by the rolling buffer: "This clip is no longer on your Goal." Only happens if not opened within the retention window.
- 6.6 Delete clip confirm. **Delete**, **Cancel**.
- **6.7 All clips.** From 5.2: grid, grouped by day.
- 6.8 Beat my score link. `(v2)` Score → link → web page with clip + "Beat it on your Goal."

### 7. Settings ("Goal", the parent's screen, max two levels)
- **7.1 Settings root.** Grouped list: Goal (brightness, quiet hours, button rotation), Connection (Wi-Fi, updates), Camera and clips, Party lighting, Notifications, Account, This Goal, Help.
- 7.2 Brightness. Slider with live preview on the Goal. Note at max: "Capped for power." (Software limit from the hardware doc.)
- 7.3 Quiet hours. Toggle (default on), start time, end time (default 22:00–07:00). One line: "Your Goal won't light up in this window."
- 7.4 Button rotation. Reorderable list of games with toggles, max 8, football games pre-selected. Preview line: "KEEPER → TARGETS → CORNERS…"
- **7.5 Wi-Fi status.** Connected to X / Not connected. **Change network** → 7.6. One line: "Only needed for updates and sharing with friends."
- 7.6 Choose network. List of networks the Goal can see. Tap → 7.7.
- 7.7 Wi-Fi password. Field, **Connect**.
- 7.8 Wi-Fi connecting → success ("Your Goal is online") or failed ("Wrong password?" with retry).
- **7.9 Updates.** Current version, **Check for updates**. States: up to date / update available (size, one-line what's new, **Update now**) / downloading (progress) / installing ("Your Goal will restart, about 2 minutes") / done.
- **7.10 Camera and clips.** Privacy statement in plain words (three sentences, no legal tone). Toggle: wake on approach. Slider: ignore anything shorter than X cm (the fox problem). Storage used. **Clear all clips** → confirm.
- **7.11 Party lighting.** Scene grid (Fire, Ocean, Aurora and any others that ship), brightness slider, **Stop**. Row of tools beneath: Message, Scoreboard, Timer, Torch.
- 7.12 Message. Text field (40 chars, counter), preview strip, **Send to Goal**, **Stop**.
- 7.13 Scoreboard. Two big counters with + and −, team colours, **Reset**, **Stop**.
- 7.14 Timer. Set minutes, **Start**, **Pause**, **Stop**. Goal shows the countdown.
- 7.15 Torch. One toggle. Overrides quiet hours by design.
- 7.16 Notifications. Two toggles: "New keeper this week", "New best (to me)". First enable triggers 0.5.
- **7.17 Account.** Signed out: "Sign in to back up scores and play friends" + **Sign in** → 8.1. Signed in: email, backup status, **Sign out**.
- **7.18 This Goal.** Name (editable), serial, firmware, panels detected (1 or 3), **Forget this Goal** → 7.19, **Re-pair** → 1.7.
- 7.19 Forget Goal confirm. "Players and clips stay on the Goal. Kazen will forget it on this phone." **Forget**, **Cancel**.
- **7.20 Help.** Setup video (chaptered), "Ripple looks broken?" card, contact address, privacy policy, licences. No FAQ tree.

### 8. Cross-cutting states and flows
- **8.1 Sign-in sheet.** Triggered by a cloud action (backup, share link, friend group), never on launch. Header states the benefit: "Back up Jake's 12 games?" Buttons: Apple, Google, **Email me a link**.
- 8.2 Email link sent. "Check your inbox." Link opens the app → signed in → returns to the action that asked.
- 8.3 Goal offline (full state). Reached from banner 3.2: what still works (history, clips already fetched), what doesn't, three checks, **Try again**.
- 8.4 Update available prompt. Non-blocking sheet the first time an update is seen while on Wi-Fi: **Update now**, **Later**. Shown once per version.
- 8.5 Notification deep links. "New best" → 5.2 for that player. "New keeper" → 5.7.
- 8.6 Generic error toast. One line, auto-dismisses. Used for send failures and network errors.
- 8.7 New best celebration (in-app). If the app is open when a player sets a new best: 4.5 shows NEW BEST; if not in Playing, a small non-blocking banner on Home.

### Deliberately not in v1
News feed, shop, achievements page, tutorial carousel, tips, chat, keeper difficulty slider, multiple Goals per account, settings deeper than two levels, any notification beyond the two in 7.16.

### Count
| Section | Full screens | Sheets / states |
|---|---|---|
| 0 Outside | 1 | 5 (OS) |
| 1 Launch / pairing | 4 | 9 |
| 2 First run | 3 | 6 |
| 3 Home | 1 | 19 |
| 4 Playing | 3 | 9 |
| 5 Players | 4 | 6 |
| 6 Clips | 2 | 6 |
| 7 Settings | 9 | 11 |
| 8 Cross-cutting | 1 | 6 |
| **Total** | **28** | **77** |

---

## Part 2 — Prompt for Figma (paste as-is)

> Create a user-flow diagram in the style of a monochrome app sitemap: light grey background, rounded-rectangle nodes with a thin 1px dark outline, no fills, a primary label in sentence case and a smaller grey secondary label beneath it. Connectors are thin 1px lines with rounded 90° corners, no arrowheads. Three line styles: **solid** = user tap / navigation, **dotted** = automatic transition driven by the Goal's state or a timer, **dashed** = optional, skippable, or second-release. Node styles: **large node** = a full screen, **standard node** = a sheet or sub-screen, **small node with a dotted outline** = a state, banner or dialog layered on another screen, **small grey node** = an OS system dialog. Put a legend in the top-right explaining the line and node styles.
>
> Title the diagram "KAZEN — second screen for the Goal". Under the title list, one per line: "Not required to play", "Pairs from a QR on the Goal", "Football games first", "Live score readable from 2 m", "Clips stay local until shared", "Four screens, no more".
>
> Layout: a narrow vertical swimlane on the far left labelled "ON THE GOAL"; the rest of the canvas labelled "IN KAZEN", arranged in horizontal bands top to bottom in the order below. Number every node exactly as given so the diagram can be cross-referenced with the spec.
>
> **Band 0 — Outside the app.** Grey OS nodes across the top: `0.1 App Store listing`, `0.2 Local network permission`, `0.3 Bluetooth permission`, `0.4 Camera permission`, `0.5 Notifications permission (late)`, `0.6 Photos permission`. Draw dashed lines from each OS node down to the node that triggers it (0.2 → 1.8, 0.3 → 1.8, 0.4 → 1.7, 0.5 → 7.16, 0.6 → 6.2).
>
> **Band 1 — Launch and pairing.** `1.1 Splash` (large) → branches to `1.2 Deep link: connecting` (secondary "Goal ID + token"), `1.5 Welcome` (large, secondary "nothing paired"), and `1.12 Already paired` (dotted to 3.1). `1.2` → `1.3 Paired` (dotted) and `1.4 Pairing failed` (secondary "scan again / find my Goal"). `1.4` → `1.7 QR scanner` (large) and `1.8 Find my Goal: searching` (large, secondary "network → hotspot → Bluetooth"). `1.5` → `1.7`, `1.8`, and dashed → `1.6 No Goal yet` (secondary "link to website"). `1.7` → `1.2`. `1.8` → `1.9 Goals found` → `1.10 Confirm colour` (secondary "which colour is your Goal showing?") → `1.3`. `1.8` → `1.11 Nothing found` (secondary "three checks") → back to `1.8` and → `7.20 Help`. A small dotted-outline node `1.13 Connection state` with three sub-labels "Direct · Home Wi-Fi · Offline" sits at the right edge of this band.
>
> **Band 2 — First run.** `1.3` → `2.1 Last three kicks` (large, secondary "Keep these"). Beside it a dotted-outline `2.2 Empty: go and kick first`. `2.1` → `2.3 Who kicked?` (large, secondary "name + colour, no account"). Attached: `2.4 Name validation` (secondary "shows as JONATH on the Goal") and dashed `2.5 Someone else kicked too` looping back to 2.3. `2.3` → `2.6 Calibrate: instruction` (large, dashed outline, secondary "one kick from the spot") → `2.7 Waiting for kick` (dotted) → `2.8 Calibrated` (dotted) → `3.1`. `2.6` dashed → `2.9 Skipped: power bar instead` → `3.1`.
>
> **Band 3 — HOME "Play" (centre of the diagram, largest node).** `3.1 Home` (secondary "chips · game grid · today's clips"). Above it, four dotted-outline banner nodes in a row: `3.2 Goal offline`, `3.3 Goal asleep`, `3.4 Goal updating`, `3.5 Game already running` (dotted line from the swimlane node "Game running"). Below Home, three children: `3.6 Player chips` (secondary "tap to toggle"), with `3.7 Long-press → player detail` and `3.8 + Add player`; `3.9 Game grid` (secondary "football first"); `6.1 Today's clips strip`. From `3.9 Game grid`, a row of six standard nodes: `3.10 Keeper` (secondary "kicks · current keeper shown"), `3.11 Shootout` (secondary "2+ players · kicks each"), `3.12 Corners` (secondary "kicks · shrinking toggle"), `3.13 Targets` (secondary "Easy / Normal / Hard"), `3.14 Power` (secondary "3 kicks · best shown"), `3.15 Passing` (secondary "10 passes"). Beneath them a lighter row of three: `3.16 Invaders` (secondary "speed"), `3.17 Whack-a-Mole` (secondary "60 s"), `3.18 Dodgeball` (secondary "60 s · soft ball"), with the group label "Arcade / Party — secondary". To the right of that row a dashed node `More games (v2)`. A dotted-outline node `3.19 Unavailable: 2 players / needs full Goal / coming soon` sits beside the grid. All nine game option nodes converge on `3.20 Sending to Goal` (dotted outline) → `4.1`.
>
> **Band 4 — PLAYING "Put me down".** `4.1 Waiting for first kick` (large) → dotted → `4.2 Live` (large, secondary "score · player · kick n/N · last result"). Dotted line into `4.2` from the swimlane node "Game running". Around `4.2`, dotted-outline state nodes: `4.3 WHO? pending`, `4.4 Turn change (1.5 s)`, `4.5 Result flash (1.5 s)`, `4.6 Keeper tell (optional)` dashed, `4.7 Connection lost, game carries on`. `4.2` → `4.8 End confirm` → `4.9 Round result` (large, secondary "scores · NEW BEST · keeper beaten · clips kept"). Also dotted from `4.2` → `4.9` when the round finishes on its own. Attached to `4.9`: `4.10 New keeper offer` (secondary "Bring him on / Not yet", dotted line to the swimlane node "NEW KEEPER?"), `4.11 Guest clip prompt` (→ 6.3). From `4.9`: `4.12 Play again` → 3.20, `Share` → 6.2, `Home` → 3.1.
>
> **Band 5 — PLAYERS "Us".** `3.1` → `5.1 Player list` (large, secondary "one sentence per player · Guest row"). `5.1` → `5.2 Player detail` (large, secondary "bests · keepers · heatmap · clips") and `5.4 Add player`. `5.2` → `5.3 Edit player` → `5.6 Remove confirm`; `5.2` → `5.7 Keeper detail` (large, secondary "name · silhouette · beaten?"); `5.2` → `5.8 Heatmap full view` (large, secondary "All time / This week / by game"); `5.2` → `6.7 All clips`. Dotted-outline nodes: `5.5 Colour taken`, `5.9 Empty: no kicks yet`. `5.1` → `5.10 Guest detail`.
>
> **Band 6 — Clips and sharing.** `6.1 Today's clips strip` → `6.2 Clip viewer` (large, secondary "overlay · Share · Save · Delete"). `6.2` → `6.3 Share sheet` (grey OS node), `6.6 Delete confirm`, and dotted-outline `6.4 Fetching from Goal`, `6.5 Clip gone`. `6.7 All clips` (large) → `6.2`. Dashed node `6.8 Beat my score link (v2)` off `6.2`. `4.11` → `6.3`.
>
> **Band 7 — SETTINGS "Goal".** `3.1` → `7.1 Settings` (large, secondary "parent's screen, two levels max"). Children in three rows. Row one: `7.2 Brightness` (secondary "live preview · capped"), `7.3 Quiet hours` (secondary "default on, 22:00–07:00"), `7.4 Button rotation` (secondary "max 8, football pre-selected"), `7.5 Wi-Fi status` (large) → `7.6 Choose network` → `7.7 Password` → `7.8 Connecting → online / failed`. Row two: `7.9 Updates` (large, secondary "up to date / available / downloading / installing / done"), `7.10 Camera and clips` (large, secondary "privacy statement · wake on approach · height · clear clips"), `7.11 Party lighting` (large, secondary "scenes · brightness · stop") with a lighter row beneath: `7.12 Message`, `7.13 Scoreboard`, `7.14 Timer`, `7.15 Torch`, group label "secondary". Row three: `7.16 Notifications` (secondary "two toggles"), `7.17 Account` (large, secondary "signed out / signed in") → `8.1`, `7.18 This Goal` (large, secondary "name · serial · firmware · panels") → `7.19 Forget confirm` and → `1.7 Re-pair`, `7.20 Help` (large, secondary "setup video · ripple card · contact · privacy").
>
> **Band 8 — States, not screens (bottom right, inside a dotted box).** `8.1 Sign-in sheet` (large, secondary "Apple · Google · email link · only when the cloud is needed") → `8.2 Email link sent`. `8.3 Goal offline (full)` (from 3.2). `8.4 Update available prompt` (once per version). `8.5 Notification deep links` (secondary "new best → 5.2 · new keeper → 5.7"). `8.6 Error toast`. `8.7 New best banner`.
>
> **ON THE GOAL swimlane (far left, top to bottom, dotted connectors between them).** `Power-on ripple`, `KICK`, `Keeper walk-on`, `QR: SAVE YOUR SCORES` (dotted across to 1.2), `Idle / wake`, `WHO?` (dotted across to 4.3), `Game running` (dotted across to 3.5 and 4.2), `RESULT` (dotted across to 4.5), `NEW KEEPER?` (dotted across to 4.10), `Post button rotation` (dotted across to 7.4). Footer label on the swimlane: "Everything here works with no phone."
>
> Make the four screens `3.1 Home`, `4.2 Live`, `5.1 Player list` and `7.1 Settings` visibly the largest nodes and give them a slightly heavier outline. Keep every primary label to three words where possible, keep spacing even, and align to a grid.

---

## Notes for the Figma session

- The Nike Run+ reference chart's flash-screen carousel and six-step sign-up have no equivalent. Kazen's onboarding is bands 1 and 2; the account is band 8 and appears only on demand.
- If the diagram gets too dense, split it into two frames: "Pairing and first run" (bands 0–2) and "Everyday" (bands 3–8), with Home repeated as the link between them.
- v2 additions when needed: The Daily, friend groups, Tournament mode with QR guest join, Free Kick top-down diagram, remaining keepers and weekly rotation, Reaction, Moving Targets, Breakout, Darts, Memory.
