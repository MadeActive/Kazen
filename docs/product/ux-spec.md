# Interactive LED Goal — End-to-End User Experience Spec

Working title for the product in this document: **the Goal**. Working name for the app: **the app**. Swap in real names later.

This document covers the whole experience from the moment someone first hears about the Goal to the moment they're telling other people to buy one. For every stage it sets out what the person is feeling, what they want, what they need to know, what we show them, and — just as importantly — what we deliberately don't show them.

---

## 1. Design principles

Everything below follows from six rules. When a decision is unclear, come back to these.

1. **The Goal is the screen. The phone is the wallet.** During play the phone stays in a pocket. The Goal itself shows targets, scores, the keeper, the result. The phone is for setting up, saving progress, and sharing. If a feature requires someone to look at their phone between kicks, it's designed wrong.
2. **Kick first, everything else later.** No account, no pairing, no tutorial is allowed to stand between a person and their first kick. The first kick is the product demo.
3. **One thing on screen at a time.** The Goal's LED face is 39 × 36 pixels (see section 2.1). It can show one big number, one short word, one shape, or one keeper. Never two of those together. The app follows the same rule: one decision per screen.
4. **Every kick gets an answer.** Within half a second of impact the Goal reacts: where it hit, whether it counted, how fast. Silence after a kick is the worst possible outcome.
5. **Ask only when the answer matters right now.** We ask for an email when there's a score worth keeping. We ask for a name when there's a leaderboard to be on. We never ask up front.
6. **Honest numbers.** The speed shown is an estimate and we present it as one (rounded, no decimals). The keeper "commits" before the ball arrives so results never look rigged. Trust in the numbers is what makes people keep coming back.

---

## 2. What the hardware can actually do (and what that means for the experience)

The experience has to be designed around the real panel, not an imagined one. These are the constraints as currently specified, with the assumptions flagged.

### 2.1 The LED face

**The panel.** Slatted batten panel, 1200 × 900 mm, 13 battens per panel, each 44 mm wide with 27 mm channels between them. Panels butt together seamlessly, so the join between two panels forms another 27 mm channel: 13 battens gives 13 channels once panels are tiled. The battens run along the 1200 mm length.

**Pixel pitch.**
- Across the battens: one channel per batten, so the pitch is 44 + 27 = **71 mm**, 13 channels per panel. (Note: 13 × 71 = 923 mm, not 900. The panel's quoted 900 mm is presumably nominal, or the edge battens are narrower. Measure a real panel; it changes the frame size by about 2 cm per panel.)
- Along the channels: LED strip at 33 mm pitch (30 LEDs/m), so **36 LEDs per 1200 mm channel**.
- **468 LEDs per panel** (13 × 36).

**Orientation and size (decided).** Battens run vertically. The full goal is **three panels side by side**: 2.7 m wide (2.77 m if the true tiled pitch is 923 mm per panel) × 1.2 m tall — roughly a 9 × 4 ft mini-soccer goal.

| | Prototype (1 panel) | Full goal (3 panels) |
|---|---|---|
| Physical face | 0.9 × 1.2 m (portrait) | 2.7 × 1.2 m |
| Pixel grid (W × H) | **13 columns × 36 rows** | **39 columns × 36 rows** |
| Pixel pitch | 71 mm × 33 mm | 71 mm × 33 mm |
| LED count | 468 | 1,404 |
| Text per line, standard 5-col font | 2 characters | 6 characters |
| Text per line, narrow 3-col font | 3 characters | 9 characters |
| Biggest number | 2 digits, 20 rows tall | 3 digits, 20 rows tall (660 mm) |

*The earlier figures in this document (51 × 55 pixels, ~6,000 LEDs) were wrong and are replaced by this table.*

The face is wide and short: 39 pixels across but each is 71 mm apart, and 36 pixels tall at 33 mm. Shapes read well; words are the tight resource. Section 6 sets the word limits accordingly.

- Pixels are more than twice as far apart in one direction as the other. Circles will look like ovals unless the renderer corrects for it. **Every graphic must be drawn on a non-square pixel grid** — build this correction into the rendering layer once so no game has to think about it.
- Text: two fonts, both 5 rows tall with 1-row line spacing. The standard font is 5 columns wide plus a 1-column gap: **6 characters per line** on the full goal. The narrow font is 3 columns plus a gap: **9 characters**, used only for the few words that need it (BULLSEYE, NEW BEST). Up to three lines fit vertically but one is the norm. Numbers up to three digits can be drawn 20 rows tall (660 mm) and read from the penalty spot. Anything longer scrolls.
- LEDs are recessed in channels, so the battens take the impact. That's what allows a full-power shot without killing pixels. *Assumption: the LED strips are set back far enough that a ball compressing into the gap doesn't touch them. Worth testing with a hard strike before finalising the channel depth.*
- Photographic or video content is out. Silhouettes, shapes, targets, numbers, short words, and animated effects are in.

### 2.1a The single-panel prototype

The prototype is one panel, portrait: 13 columns × 36 rows, 0.9 × 1.2 m. It's a third of the final width, so it's the right rig for proving the hard parts and the wrong rig for judging layout.

What it can prove:
- Impact sensing tolerance (section 2.2) — the single most important measurement.
- Kick-moment detection and the speed estimate (2.3).
- Keeper commit-before-impact (8.1): a 13-column keeper is 30 rows tall and can dive to either edge of the panel.
- The power-on ripple and self-test.
- Camera wake, calibration, and clip capture.
- The renderer's non-square pixel correction.

What it can't show: any word longer than 3 characters without scrolling, three-digit speeds in the standard font, or the multi-target games at their real spacing. Build the rendering layer so each game declares a minimum face width and the prototype simply runs the subset that fits (Keeper, Power, Passing with one target, Whack-a-Mole with one column of moles). Design the games for 39 × 36; test the electronics on 13 × 36.

### 2.2 Impact sensing

- Sensors on the panel report where the ball hit. *Assumption: they return an X/Y position with a tolerance somewhere in the 50–150 mm range.* Until that tolerance is measured, every target in every game should be **at least 3 columns × 6 rows (about 210 × 200 mm)**, and hit zones should have a soft edge (a near-miss lights up amber, not red).
- Any strike anywhere on the face registers. A ball that misses the goal entirely does not register. So every game needs a **"miss" fallback**: if a kick was seen by the camera (or the shot clock runs out) and no impact arrives within ~1.5 seconds, the Goal shows MISS and moves on. Without this, a wide shot leaves the Goal waiting forever, which feels broken.
- Two balls hitting in quick succession (e.g. a rebound) need debouncing: ignore impacts within ~300 ms of a registered one.

### 2.3 Speed

- Speed is **estimated**, not measured. Two candidate methods, both worth prototyping:
  - Time-of-flight: detect the kick moment (camera sees the foot strike, or a microphone spike), record the impact time from the sensors, divide by the distance from the kicker to the face. Distance comes from the camera estimating where the person is standing, or from a marked spot on the ground the game tells them to use.
  - Camera tracking: track the ball's apparent size and position over a few frames as it approaches.
- Either way, present speed as a rounded whole number ("72 km/h"), never with decimals, and never claim radar accuracy. Internally, drop any reading that's physically implausible (over 150 km/h, under 10 km/h) rather than displaying it.
- *Assumption to verify: the camera frame rate and the controller are fast enough to get a kick timestamp within ~30 ms. If not, speed becomes a rough "power" bar rather than a km/h number, and the UI should be designed so either works.*

### 2.4 Camera

- Front-facing, sees the kicker and the run-up. Used for: detecting that someone has walked up (wake the Goal), detecting the kick moment, estimating where the kicker is standing (angle and distance for free kicks), giving the keeper an anticipation cue (which way the hips/plant foot suggest), and recording short replay clips.
- Limits to design around: it won't work well in the dark without additional lighting or an IR-capable camera, it can be fooled by two people in frame, and it needs a one-off calibration to know where the pitch is. *All of these need a decision before the first prototype.*
- Privacy: this is a camera in someone's garden. Clips stay on the Goal's controller by default, are overwritten on a rolling basis, and only leave the device when the person taps "Share" on a specific clip. This is stated plainly in the app and is part of the trust story, not a footnote.

### 2.5 Ball size

Small balls (tennis, cricket) hit the batten edges and deflect unpredictably, so any small-ball game is out. Everything below assumes a **size 3, 4, or 5 football, or a soft dodgeball-sized ball.**

### 2.6 Connectivity and control

- The Goal needs a controller with Wi-Fi. *Assumption: garden Wi-Fi is often weak.* So the Goal must be fully playable with **no internet and no phone**: every game runs locally, and the phone connects directly to the Goal (Bluetooth or the Goal's own Wi-Fi hotspot) when the home network isn't reachable. Cloud is for backup, leaderboards with friends, and updates — never for play.
- There is **one physical button** on the Goal (on a post, at adult hip height, inside a rubber bumper): short press = next / confirm, long press = back to the menu, hold 5 s = power off. Everything in the core play loop can be driven by kicks and that one button. The phone is optional.

### 2.7 Things the hardware does not do (and we won't pretend it does)

- It doesn't know which foot you kicked with reliably. No weak-foot features.
- It doesn't sense the crossbar unless sensors are added to it. Crossbar Challenge stays on the "maybe" list, gated on that hardware decision.
- It doesn't have the resolution for faces, photos, or video.
- It can't tell the difference between a shot and a throw. Dodgeball and throwing games are simply "hit the target"; we don't claim to detect technique.

---

## 3. Who is playing

Three people show up repeatedly in the journey. Design for all three at once.

| Person | What they want | What they'll tolerate |
|---|---|---|
| **The kid (7–14)** | To beat the keeper. To be fastest. To play right now. | Zero setup. Zero reading. Pictures and big numbers. |
| **The parent / buyer** | Something the kids will actually use for more than a week. Something that looks great in the garden. Not to be the IT department. | A 5-minute setup once. One app. Notifications only if they're worth it. |
| **The mate at the barbecue** | A go. Then another go. To beat the host. | Nothing. They will not download an app to have a kick. They may download it afterwards to see their clip. |

The kid drives daily use. The parent drives purchase and setup. The mate drives word of mouth. Every stage below notes which of them it's for.

---

## 4. The journey

### Stage 1 — Discovery

**Who:** the parent (buyer), sometimes a kid who saw it somewhere and is now lobbying.

**What they're feeling:** curiosity, then a little disbelief ("does it actually work?"), then "how much?"

**What they want to know, in this order:**
1. What is it? (A goal that shows a keeper and tells you if you scored.)
2. Does it really work, with a real ball, in a real garden?
3. What else does it do? (Party lights, other games, for the whole family.)
4. What does it cost and how big is it?

**What we show:**
- The single most important asset is a **10–15 second clip of a kid beating the keeper**: run-up, the silhouette dives, the ball hits the corner, "GOAL 68 km/h" flashes, the kid loses their mind. Shot in a normal garden, in daylight, no studio. This clip does more than any feature list.
- Second asset: the same Goal at dusk running a party scene, to show it's not just a kids' toy.
- The website answers the four questions above in that order and nothing else above the fold. Sizes, specs, and how the sensors work live further down for the people who want them.

**What we deliberately don't show:** the app. At the discovery stage, the app is a reason to worry ("will it need updates, will it break"). The Goal is the hero.

**How the product itself drives discovery:** the share clips (Stage 8) are the Goal's marketing. Every clip carries a small, tasteful mark and the score overlay. Design that overlay well and it becomes recognisable.

*Assumption: the primary channel is social video plus word of mouth from owners. This document doesn't estimate reach or conversion — there's no data to base a number on yet.*

### Stage 2 — Deciding and buying

**Who:** the parent.

**What they're feeling:** "I want this but it's a lot of money / a lot of space / probably a faff to set up."

**What they need:**
- Exact footprint and whether it fits their garden. A simple **"will it fit?" tool**: enter garden width and depth, see the Goal drawn to scale with the recommended run-up.
- What's in the box, and honestly what they'll need to do (see Stage 3). If it needs a flat surface, a power socket within X metres, or two people to lift a panel, say so before purchase, not after.
- Weather: it lives outside. State the rating and what "leave it out all year" actually means.
- Which balls work (section 2.5). Say plainly that tennis balls don't.
- Delivery lead time and what happens if it arrives damaged.

**What we don't do:** upsell add-ons at checkout. One product, one price, one decision. Extras (spare balls, crossbar sensor if it exists, mounting kits) can be offered after delivery when they've fallen in love with it.

**Order confirmation** does two useful things: gives a delivery date, and sends a link to a 60-second "what to expect on delivery day" video so the parent knows exactly what's coming and where to put it. That's the only email before delivery.

### Stage 3 — Delivery and unboxing

**Who:** the parent, and any kids in the house who have been told "it's coming today."

**What they're feeling:** excitement, mixed with dread about assembly.

**The physical reality:** *Assumption: this ships as flat-packed batten panels with LEDs pre-fitted, plus posts/frame, sensor loom, controller, camera, and power supply.* Panels are large and heavy. Unboxing needs to be designed for a garden, not a living room.

**Unboxing design:**
- **Outer packaging:** opens from the top like a lid, not a slit-along-the-tape box, so panels can be lifted straight up. Inside, the first thing visible is a single card, A5, with **one sentence and one QR code**: "You're about 20 minutes from your first kick. Scan for the setup video, or follow the numbers." Nothing else on that card.
- **Everything is numbered.** Panels 1–N, posts, the controller box. Each component has a big printed number and nothing else. The setup guide is a sequence of numbered pictures, no paragraphs.
- **The controller box is packed on top**, in its own small box that looks and feels like a piece of consumer electronics rather than a component. It's the thing the parent will feel proud of. Inside: controller, camera, one cable, a laminated one-page card.
- **A ball is in the box.** A proper size 5 with the product mark. This matters more than it sounds: it guarantees the first kick happens the same day, and it makes the box feel like a gift rather than hardware.
- **The panels are the last thing.** By the time the parent reaches them they've already seen the controller, the ball, and the card, and they know how long this takes.

**What's on the laminated card** (the only text in the box):
1. Stand the frame. (Picture.)
2. Slot the panels in order 1 → N. (Picture.)
3. Plug the panel loom into the controller. Clip the camera to the top bar. (Picture.)
4. Plug in. Wait for the light. Kick.

That's it. No app mentioned yet. The app appears on the Goal itself when it's relevant (Stage 4).

**Assembly guidance in the app (optional, for those who scan the QR):** a video, chaptered by step, filmable in one take. Each chapter ends on a still of what "done" looks like so they can check against reality.

### Stage 4 — First power-on: the wow moment

**Who:** everyone in the house is standing there. This is the moment the parent finds out whether they made a good decision.

**What they're feeling:** "Please work."

**The sequence, second by second:**

1. **Plug in.** Within 2 seconds, a single pixel at the centre of the face lights up. Then a ripple expands outward to the edges, column by column, like a stone dropped in water. This does three jobs: it proves every LED works, it proves the panels are connected in the right order (the ripple would look broken if not), and it looks like the thing waking up.
2. **The face goes dark except for a small pulsing dot at the centre.** Two seconds of quiet.
3. **The Goal draws a target** — a large ring around the centre — and the word **KICK** appears above it, big enough to read from the penalty spot. Nothing else. No welcome message, no branding, no "download the app."
4. **Someone kicks.** Whoever is holding the ball (it's the kid) will kick within about four seconds of seeing KICK. The instant the ball hits:
   - A bright burst at the impact point, then a ripple out from it.
   - The impact point stays lit as a small cross.
   - A big number appears: the speed. **"61"** and then a small **km/h** beneath it.
   - Half a second later the number is replaced with a single word depending on where they hit: **BULLSEYE**, **NICE**, or **WIDE**.
5. **Then the keeper appears.** Without anyone pressing anything, the target fades, and a silhouette walks into the centre of the goal, bounces on its toes, and spreads its arms. Above it: **BEAT ME**. This is the moment the parent understands the product and the kid understands the rest of their summer.
6. **The next kick is a penalty against the keeper.** He dives, the ball hits, the Goal shows the impact point, the keeper's reach, and **GOAL** or **SAVED** in huge letters. If saved, he does a little celebration. If beaten, he slumps.
7. **After three kicks against the keeper, the Goal shows the first and only setup prompt:** a QR code with the words **SAVE YOUR SCORES** above it and, in small text, "or just keep kicking." The Goal then goes back to BEAT ME and stays playable indefinitely.

Nobody has touched a phone. Nobody has read a manual. The Goal has already proven every subsystem (LEDs, sensors, speed, camera-triggered keeper) in front of the family, and the app has been introduced as a reward, not a requirement.

**Why the QR is on the Goal and not on a card:** a QR on the Goal at that moment links the phone and the Goal in one scan — no searching for the device, no pairing codes. The QR encodes the Goal's identity and a one-time pairing token.

**If something's wrong at step 1:** the ripple animation is diagnostic. A panel out of order, a dead segment, or a loose loom shows up as a visible gap or jump. The laminated card has one line at the bottom: "Ripple looks broken? Check the panel numbers and the loom clip." That handles the most likely failure without support tickets.

### Stage 5 — The app: pairing and the first "signup"

**Who:** the parent, with the kid hovering.

**What they're feeling:** happy (it works), and wanting to lock in the good feeling — save the scores, see the clip.

**What they want:** to see the shots they just took. That's it. They don't want to create a profile yet.

**The flow (target: under 90 seconds, three taps):**

1. Scan the QR on the Goal → app store → install → open. The app opens **directly to the Goal**, already paired via the token in the QR. No "add device," no searching, no Wi-Fi password yet.
2. **First screen: the last three kicks.** Three small tiles, each showing the impact point on a tiny goal outline, the speed, and GOAL/SAVED. Beneath them, one button: **Keep these**.
3. Tap **Keep these** → **one sheet: "Who kicked?"** with a name field and a big **Done**. Optional: pick from four avatar colours. Behind the scenes this creates a local player profile on the Goal. No email, no password, no account.
4. Done. The app now shows the home screen (section 5). The parent can hand the phone to the kid or put it away.

**Where the actual account comes in:** the first time something needs the cloud — backing up scores, joining a friend's leaderboard, sharing a clip — the app asks for a one-tap sign-in (Apple / Google / email link). That may be day one or day thirty. The ask is always attached to a concrete benefit visible on screen ("Back up Jake's 12 games?"), never a wall.

**Wi-Fi:** the app asks for the home Wi-Fi password only when it needs it, which is for updates and cloud features. Until then the phone talks to the Goal directly. If the parent never enters Wi-Fi, the Goal still works fully; the app just shows a quiet "Connect to Wi-Fi for updates" line in settings.

**Camera calibration** happens here too, but it's disguised as a game: the app says "Put the ball on the penalty spot and take one kick" — the Goal already knows the face geometry, the camera sees the ball on the ground, and that single kick calibrates distance for speed estimates. If the person skips it, speed falls back to a "power" bar (section 2.3).

### Stage 6 — Everyday play: pick up and play

**Who:** the kid, daily. The parent occasionally. Mates at weekends.

**What they're feeling:** "I've got ten minutes." They do not want a menu.

**Idle behaviour (the Goal with nobody near it):**
- During the day, off. A dark goal in a garden is fine; a glowing one all day is a waste and annoys neighbours.
- When the camera sees someone walk into the run-up zone, the Goal wakes: the ripple, then the last game they played, ready to go. **The default is always "the game you played last."** A kid who only ever plays penalties never sees a menu.
- If they walk away, it dims after two minutes and sleeps after ten.

**Starting a game without a phone:**
- Kick → play the last game.
- Short press the post button → the Goal cycles through game icons one at a time, each with a one-word name (**KEEPER**, **TARGETS**, **CORNERS**, **INVADERS** …). Kick or press to pick. Six to eight games in this rotation, chosen in the app; the rest live in the app only.
- Long press → back to idle.

**Player identity without a phone:**
- The Goal shows **WHO?** and the avatar colours of known players as four large blocks. Kick your colour. If nobody kicks in five seconds it plays as **GUEST**. Guest scores are shown but not saved, which is the gentle nudge to add a profile later.

**Starting a game with a phone:**
- The app's home screen is the game grid (section 5). Tap a game, and it's on the Goal. Optionally pick players first. The app then shows a **"Playing on the Goal — put me down"** screen with the live score in large text and nothing else, so it can sit on a garden table and be glanced at.

**During play, the app never demands attention.** No notifications, no prompts, no "rate this app." The only thing it does mid-session is keep score and quietly save clips.

**Turn-taking with multiple players:** the Goal shows the next player's colour and name (**JAKE**) before each kick. Anyone can play; the Goal doesn't care who holds the phone.

**Ending a session:** nobody "ends" anything. They walk off. The Goal sleeps. Next time, it wakes with their last game and, if it's a new day, a **DAILY** badge on the button rotation (section 7).

### Stage 7 — Coming back: what brings them to the garden tomorrow

**Who:** the kid (daily), the parent (weekly), the household as a whole.

**What they're feeling by day three:** the novelty is fading slightly. This is where most garden toys die. The Goal has to give them a reason that isn't "play the same penalty game again."

**Retention mechanics, all of which live on the Goal itself (no phone needed):**

- **Personal bests, always visible at the right moment.** When a kid beats their fastest shot, the Goal says **NEW BEST** before it says the number. That single word is worth more than any dashboard. The same for most goals in a row, best target score, longest streak.
- **The keeper rotates.** A new keeper every week, with a different personality (section 8). Mondays the Goal announces **NEW KEEPER** with a name and a silhouette. Beating each keeper is a collectable — a row of small keeper icons on the profile, lit or unlit.
- **The Daily.** One short challenge per day, 5 kicks, same for every Goal in the world: "Top left corner, 5 kicks." The score sits on the profile and, once signed in, on a global daily leaderboard. Kids will do the Daily before school.
- **Streaks, gently.** Playing on consecutive days lights a small flame on the profile. Missing a day doesn't shame anyone — the flame just goes out and can be relit. No streak-loss notifications, ever.
- **Household leaderboard on the idle screen.** When the Goal wakes, before the game, it shows the top three household speeds or Daily scores for three seconds. Siblings will fight over this. That's the point.
- **Seasonal skins for the keeper and the face**: Halloween keeper, Christmas targets, a birthday mode where the Goal shows the name and age of the player when they walk up (set by the parent in the app).

**Notifications — the whole policy:** the app sends at most one notification a week, and only these: "New keeper this week: [name]," or "Jake set a new best today: 74 km/h" (to the parent, so they can say well done). Nothing else. The parent can turn both off. If it's ever tempting to add another notification, the answer is no.

**What the parent sees when they open the app after a week:** one screen, no charts by default. "This week: 42 kicks. Jake's best: 74 km/h. Mia beat The Wall." Tap to see the heatmap and history. The default is a sentence, not a dashboard.

### Stage 8 — Sharing

**Who:** the kid wants to send the clip to a friend. The parent wants to post it. The mate at the barbecue wants their go on record.

**What they're feeling:** pride. The moment to capture is within a minute of the shot, while the feeling is still there.

**The clip:**
- The camera records continuously into a rolling buffer on the Goal. When a kick is detected, the Goal keeps the 4 seconds around it (2 before impact, 2 after). Everything else is discarded.
- The Goal renders the clip with the overlay: a small goal outline in the corner showing the impact point and the keeper's dive, the speed, and GOAL / SAVED / BULLSEYE. The overlay is the brand.
- *Assumption: the controller can encode a 4-second clip with overlay in under 10 seconds. If not, rendering moves to the phone, which is fine — the phone downloads the raw clip and the overlay data.*

**The share flow:**
- On the Goal, after a notable kick (new best, beat the keeper, bullseye), a small **camera icon** pulses in a corner for 10 seconds. It means "this one's been kept." No action needed on the Goal.
- In the app, the home screen shows a **"Today's clips"** strip. Tap a clip, it plays, and there's one button: **Share**. Standard share sheet.
- The clip is never uploaded anywhere until Share is tapped. That's the privacy promise from section 2.4 and the app says it in one line beneath the strip: "Clips stay on your Goal until you share them."

**Beat my score:**
- Any score in the app can be sent as a link. The link opens a page with the clip and a button: "Beat it on your Goal." If the friend has a Goal, tapping it queues the exact same challenge (same game, same targets, same keeper) on their Goal and the result is compared. If they don't, the page has one line about what the Goal is. That's the referral loop, and it's the only place we ask a non-owner to do anything.

**The mate at the barbecue:** they played as GUEST. At the end of the session the host's app shows "Guest's best: 68 km/h — send them the clip?" One tap, share sheet, done. The mate receives a clip of themselves with the overlay, and now knows what the product is called.

### Stage 9 — Advocacy

**Who:** the parent, after a few months. The kid, at school, constantly.

**What they're feeling:** ownership. It's "our Goal." They want other people to have one, partly so they can play against them.

**What turns an owner into an advocate:**
- **Friend leaderboards.** Once two households both own a Goal, the app lets them form a group. The Daily becomes a competition between families. This is the strongest reason to want a friend to buy one.
- **Party mode with guests joining by QR.** At a party, the host puts the Goal into Tournament mode. The Goal shows a QR; guests scan it and get a web page (no install) where they type a name. The Goal now runs a bracket with everyone's names. Every guest leaves having been on the big board. Some of them will go home and search for it.
- **The owner referral is a game, not a discount code.** "Your friend's Goal is live — first Daily between you starts tomorrow." Any financial referral reward can be added later; the emotional one is built in.
- **Owners get the new keeper first.** Small, cheap, and it makes people feel like insiders.

**What we ask of advocates:** nothing explicitly. No "rate us," no "review," no "refer a friend and earn." The product shares itself through clips, guest play, and challenges. If review prompts are ever needed for store placement, they appear once, after a new best, and never again.

---

## 5. The app — structure

The app has **four screens** and no more. Anything that doesn't fit into these four doesn't ship.

### 5.1 Home — "Play"
- A grid of game tiles: icon, one-word name. Football games first, then arcade, then party. Tap one and it starts on the Goal.
- Above the grid: the player chips (avatars). Tap to toggle who's playing. Defaults to whoever played last.
- Below the grid: **Today's clips** strip (only appears if there are clips).
- That's the whole screen.

### 5.2 Playing — "Put me down"
- Appears automatically when a game is running. Large score, large current player name, nothing else. A single small **End** link at the bottom.
- Designed to be readable from two metres away on a garden table.

### 5.3 Players — "Us"
- One row per player: avatar, name, this week in one sentence.
- Tap a player: their bests, their keepers beaten, their shot heatmap (a goal outline with hit density — the one chart in the app), and their clips.
- Add a player is a plus button. Name, colour, done.

### 5.4 Goal — "Settings"
- Brightness, quiet hours (the Goal never lights up between these times), Wi-Fi, updates, which games are in the post-button rotation, camera and clips (with the privacy statement), party lighting.
- Party lighting lives here, not on Home, because it's a parent's feature not a kid's game. It's one tap to start a scene and one slider for brightness.

**Explicitly not in the app:** a news feed, a shop, achievements pages, a settings tree deeper than two levels, a tutorial, a "tips" section, a chat. Help is a single link to a page with the setup video and a contact address.

---

## 6. On-Goal interface rules

The Goal's face is used by every game. These rules keep it consistent and readable.

- **Three states only:** IDLE (dark or a single pulsing dot), PROMPT (what to do next: a target, a keeper, a word), RESULT (what just happened: impact point, number, word). Every game is a loop of PROMPT → kick → RESULT.
- **Words are one word, uppercase, max 6 characters in the standard font:** KICK, GOAL, SAVED, MISS, WIDE, NICE, WHO?, DAILY, NEXT, KEEPER, JAKE (player names are truncated to 6). Two exceptions use the narrow font: BULLSEYE and NEW BEST. Anything else scrolls, and scrolling is reserved for the Message feature and player names longer than 6.
- **Numbers are huge.** A speed or a score fills at least a third of the height.
- **Colour has fixed meanings across every game:** green = success, amber = near miss, red = fail/saved, white = neutral prompt, player colours = only used for identity.
- **Every RESULT lasts 1.5 seconds then returns to PROMPT.** No lingering. The next kick should never be blocked by the last result.
- **The impact cross is always shown**, even in games where position doesn't matter. People want to know where they hit.
- **Sound.** *Assumption: a small weatherproof speaker is included or can be.* If so: one short sound per result state (goal, save, hit, miss) and the keeper's occasional taunt. No music, no voice-over. If there's no speaker, everything above works silently.

---

## 7. The games — final list

Each game is defined by what's on the face, the rule in one line, the scoring, and any hardware caveat. Games marked **Core** ship in the first version and appear in the post-button rotation by default.

### 7.1 Football

**Keeper (Core)** — The goalie simulator. Section 8 covers it in full. Rule: score past the keeper. Scoring: goals from 5 kicks; sudden death if two players tie. The Goal keeps a record of which keepers each player has beaten.

**Shootout (Core)** — Two or more players alternate penalties against the keeper. Rule: standard shootout, 5 each then sudden death. On the face: the running score as two big numbers with the current player's colour. This is the multiplayer default and the game people play at a barbecue.

**Corners / Top Bins (Core)** — Only the four corners light up. Rule: hit a corner. Scoring: top corners 3, bottom corners 1, anywhere else 0, 10 kicks. Corner zones sized generously (section 2.2). Variant: after each hit the corner shrinks.

**Targets (Core)** — A shape appears somewhere on the face: ring, square, diamond, hoop. Rule: hit it before it disappears. Scoring: base points for a hit, bonus for speed and for smaller shapes, 60 seconds or 10 kicks. The shape's fade-out timer is the difficulty; the app has one slider for it: Easy / Normal / Hard.

**Reaction** — The face is dark. A target flashes. Rule: hit it within 2 seconds. Scoring: points scale with how fast the ball arrives after the flash. Five rounds. Needs the speed/kick-time detection working; otherwise it's measured from flash to impact, which still works.

**Moving Targets** — A ring slides left–right, or bounces, or orbits. Rule: hit it. Scoring: as Targets, with a multiplier for speed of the target. Three speeds.

**Power (Core)** — No targets. Rule: hit it as hard as you can, anywhere. Scoring: fastest of 3. On the face: the number, and if it's a new best, NEW BEST first. This is the game guests play. Depends on the speed estimate being reliable enough that people trust it; if it isn't, this ships as a power bar with a personal-best line rather than km/h.

**Free Kick** — The camera reads where the kicker is standing (distance and angle from centre) and the keeper positions himself accordingly: for a shot from the left, he shades to his right post. Rule: score from wherever you've put the ball. Scoring: goals from 5, with a bonus for wider angles and longer distances. The app shows a top-down diagram of where the last kick was taken from. Physical dummies on the pitch are the wall; the Goal doesn't draw one. *Depends on the camera reliably estimating the kicker's position — needs the calibration in Stage 5.*

**Passing (Core)** — A strip of low targets along the bottom of the face, at ground-ball height. Rule: pass the ball along the ground into the lit target. Scoring: accuracy plus a small bonus for pace. Ten passes. Doubles as the warm-up game and works for younger kids.

**Crossbar (Maybe)** — Only if impact sensors are added to the crossbar. Rule: hit the bar. Scoring: 5 for the bar, 1 for the top row of the face beneath it. Keep it in the backlog until the hardware decision is made; don't design around it.

### 7.2 Throwing and other sports

**Dodgeball (Core for parties)** — Silhouettes of "opponents" stand on the face. Rule: hit them with a soft ball to knock them out; new ones appear. Scoring: knockouts in 60 seconds. Works with a foam dodgeball and needs no technique detection.

**Rugby / NFL kicking** — The face shows posts; the target zone is the space between them, upper half of the face. Rule: put it through the posts. Scoring: successful kicks from 5, distance bonus via the camera's distance estimate. The face is too short to represent real posts, so the target zone is "above the bar and between the uprights" drawn as a shape.

**Baseball / softball pitching** — A strike-zone rectangle in the centre. Rule: throw strikes. Scoring: balls and strikes; three strikes per batter, three outs per inning. *Only with a soft, large ball; a real baseball is too small for the batten gaps.*

### 7.3 Arcade

**Invaders (Core)** — Rows of aliens descend slowly. Rule: hit an alien to destroy it. Scoring: points per alien, game over when they reach the bottom. Aliens are 3 columns × 4 rows, so about 8 across the full face; the descent speed is the difficulty.

**Whack-a-Mole (Core)** — Moles pop up in random spots for 1–2 seconds. Rule: hit them while they're up. Scoring: hits in 60 seconds. Ideal for young kids and guests.

**Breakout** — A wall of bricks across the top. Rule: each hit removes the bricks around the impact point. Scoring: bricks cleared in 15 kicks. Simple and oddly satisfying.

**Noughts and Crosses** — A 3 × 3 grid. Rule: two players alternate; kick a cell to claim it. Scoring: first line wins. Best of three.

**Darts** — A dartboard drawn to fit the face (ovals corrected for pixel pitch). Rule: standard darts rules. Scoring: 501, Around the Clock, Killer. Segment sizes are large; doubles and trebles are wide bands. The scoring UI on the Goal shows only the remaining score; the app shows the full board.

**Bingo** — A grid of numbers. Rule: hit numbers to mark them. Scoring: first line, then full house. Multiplayer, each player has their own card in the app, one shared grid on the Goal.

**Memory** — Cells flash in a sequence. Rule: hit them in the same order. Scoring: sequence length reached. One extra step per round.

**Colour Call** — The face shows four coloured blocks. Rule: the Goal shouts (or shows) a colour; hit it first. Scoring: two players race; first hit wins the round. Needs a speaker for the shout; without one the colour name is shown as a word.

### 7.4 Camera-only games (no ball)

**Mirror** — The camera's silhouette of whoever is standing in front is drawn live on the face. Not a game: it's the thing kids do for ten minutes when they discover it. Also used for the Stage 4 keeper walk-on. *Depends on background subtraction working on the camera feed; in a garden with moving foliage this needs testing.*

**Freeze** — The face shows GO, then FREEZE at random. Rule: anyone moving when it says FREEZE is out. The camera detects motion. Party filler.

**Hole in the Wall** — A shape appears; you have to make it with your body. Rule: match the silhouette. Scoring: percentage overlap. *Same camera dependency as Mirror.*

### 7.5 Party and garden

Not games; these live in Settings and are the parent's feature.

- **Scenes:** Fire, Ocean, Aurora, Stars, Rain. Slow, low-brightness animations for evenings.
- **Beat:** *Assumption: a microphone exists.* Colour pulses to sound. If no mic, this is a fixed-tempo pulse with a tempo slider.
- **Message:** scrolling text, up to 40 characters, set from the app. "HAPPY 40TH DAVE" scrolls across. Also used for birthday mode (Stage 7).
- **Scoreboard:** two big numbers with plus/minus on the app, for any garden game.
- **Timer:** a countdown for anything — barbecue, hide and seek, a match.
- **Torch:** every LED white at max brightness. Occasionally useful; costs nothing.

**Quiet hours** override all of the above. The parent sets them once (default 22:00–07:00) and the Goal never lights up in that window, except for the Torch if explicitly triggered.

---

## 8. The keeper

The keeper is the product's character. He's the reason people describe the Goal to friends, so he gets more design attention than any other feature.

### 8.1 How a penalty works, step by step

1. **Prompt.** The keeper walks in from one side, takes his position, bounces, spreads his arms. Above him: **BEAT ME** or the player's name.
2. **Anticipation.** As the kicker starts their run-up, the camera watches. The keeper shifts his weight subtly one way — a tell. Sometimes it's honest, sometimes it's a bluff, depending on his profile.
3. **Commit.** At the moment the camera detects the kick (or, as a fallback, the microphone hears it), the keeper **chooses a dive and starts moving. This decision is locked before the ball arrives.** He picks from: stay, left low, left high, right low, right high, based on his profile, the camera's read of the kicker's body shape, and a random element.
4. **Impact.** The sensors report where the ball hit and when. The Goal knows where the keeper's reach envelope was at that instant.
5. **Result.** If the impact point is inside the reach envelope: **SAVED**, the keeper catches it and holds the pose, a small celebration. If outside: **GOAL**, the ball position is shown as a cross, the keeper slumps or rolls. Then the speed.
6. **Replay on the face** (optional, 2 seconds): the dive re-plays quickly with the impact cross overlaid, so the kicker can see how close it was.

The important design decision is step 3. Because the keeper commits based on what happens *before* impact, a good kicker can genuinely disguise their shot, and the outcome is never computed backwards from where the ball landed. Players will test this. It has to hold up.

*Fallback if kick detection isn't reliable enough:* the keeper commits on a fixed timer after the run-up starts. Less satisfying, still fair. Never compute the dive after impact.

### 8.2 Keeper profiles

Each keeper is a small set of numbers plus a personality. The app shows none of the numbers; it shows a name, a silhouette, and a one-line description.

| Trait | What it changes |
|---|---|
| Reaction delay | How long after the kick before he starts moving (0.15–0.4 s) |
| Dive speed | How far his reach envelope travels per second |
| Reach | The size of his envelope at full stretch; taller keepers cover the top corners better. On a 2.7 m goal a full-stretch keeper covers a large share of the face, so even The Legend's envelope is capped at about 40% of the width — there is always a corner to hit |
| Read quality | How often his anticipation cue is honest, and how much he trusts the camera's read of the kicker |
| Weak zone | A region where his envelope is smaller (low left, top right, etc.) |
| Bluff rate | How often he shows a fake tell |
| Attitude | Idle animations, celebration style, taunt frequency |

**Launch keepers (five, invented, no licensing):**

- **The Rookie** — slow reaction, big weak zone low right, never bluffs. For under-10s and the first day.
- **The Wall** — huge reach, slow dive. Beat him with pace to the corners.
- **The Cat** — fast dive, small reach, guesses a lot. Beat him by waiting for his tell and going the other way.
- **The Reader** — high read quality, follows the kicker's hips. Beat him by disguising.
- **The Legend** — everything high, small weak zone that rotates each week. The end boss.

Real-name keepers are deliberately not in the product. Someone at home can rename any keeper whatever they like in the app (that's their business); the product itself never ships a real name.

### 8.3 Difficulty without a menu

There is no difficulty slider for the keeper. The keeper *is* the difficulty. The Goal starts everyone on The Rookie. When a player beats a keeper convincingly (say, 4 from 5 twice), the Goal offers the next one with **NEW KEEPER?** and a kick to accept. Each player's current keeper is remembered per profile, so a 7-year-old and a 40-year-old both walk up and get the right opponent without anyone touching a setting.

The weekly rotation (Stage 7) is separate: it's a guest keeper who's available to everyone for that week, in addition to their own progression.

---

## 9. The first 90 days, as the household lives it

**Day 1.** Unbox, build, plug in, ripple, KICK, keeper. Twenty minutes of the whole family taking penalties. The parent scans the QR, keeps the clips, names the kids. Sends one clip to a grandparent.

**Day 2.** The kid goes out before school. The Goal wakes, shows the household leaderboard, then the keeper. Five kicks, a NEW BEST. The parent gets the week's only notification that evening.

**Day 4.** The kid discovers the post button and finds Invaders. Plays for 40 minutes. Sibling joins, they play Noughts and Crosses, argue.

**Day 7.** NEW KEEPER on Monday. The Rookie is beaten by Friday.

**Day 10.** Barbecue. Shootout mode with five adults playing as GUEST. Someone hits 81 km/h. The host sends them the clip. The next morning that person searches for the product.

**Day 14.** The parent sets quiet hours after the Goal woke up when the fox walked past. (This is worth pre-empting: the camera wake should ignore anything below a set height, and quiet hours should default on.)

**Day 21.** Rain for three days. Nobody plays. No notifications nag anyone. On the fourth day the Goal wakes as normal. Nothing has been lost.

**Day 30.** The parent opens the app to share a clip and sees "This month: 300 kicks." Thinks: worth it.

**Day 45.** A school friend's family buys one. The two families form a group. The Daily becomes a rivalry.

**Day 60.** Halloween keeper. The kid asks if they can leave the Goal on the Fire scene during the party. Yes.

**Day 90.** The parent has not opened Settings since day 14. The kid has beaten The Reader. The Legend's weak zone moved last week and he hasn't found it yet.

---

## 10. What ships first

Everything in this document is designed to be coherent as a whole, but it doesn't all need to exist on day one. The minimum that delivers the experience above:

**Must ship (version 1):**
- Power-on ripple and self-test
- KICK → impact → speed → keeper walk-on sequence (Stage 4)
- Keeper with three profiles (Rookie, Wall, Cat), commit-before-impact
- Shootout, Corners, Targets, Power, Passing
- Invaders, Whack-a-Mole, Dodgeball
- Post button rotation, WHO? player pick, GUEST
- App: Home, Playing, Players, Settings (four screens only)
- QR pairing from the Goal, local profiles, no account required
- Clips kept locally, share from app
- Quiet hours, brightness, three party scenes, Message

**Second release:**
- Remaining keepers and weekly rotation
- The Daily and friend groups (needs accounts and cloud)
- Free Kick (needs camera positioning to be proven)
- Reaction, Moving Targets, Breakout, Darts, Memory
- Beat-my-score links
- Tournament mode with QR guest join

**Later / gated on hardware decisions:**
- Crossbar (crossbar sensors)
- Mirror, Freeze, Hole in the Wall (camera silhouette quality)
- Beat scene (microphone)
- Rugby, Baseball variants

---

## 11. Open questions and risks

These need answers before the design above can be finalised. Each one changes something specific in the experience.

| Question | What it affects |
|---|---|
| Measured impact-position tolerance of the sensors | Minimum target size in every game; whether Darts is viable |
| Can the kick moment be detected within ~30 ms (camera or mic)? | Whether speed is a km/h number or a power bar; whether the keeper can commit-before-impact |
| Camera performance at dusk / night | Whether the keeper and Free Kick work in the evening, which is when adults play |
| Camera background subtraction in a real garden | Whether Mirror and the silhouette games ship at all |
| Controller processing power | Whether clips render on the Goal or on the phone; how many LEDs it can animate at 30+ fps |
| Is there a speaker? A microphone? | Colour Call, Beat scene, keeper taunts, kick detection fallback |
| Weather rating of the sensors and camera | Whether "leave it out all year" is true |
| Real tiled width of a panel (13 × 71 = 923 mm vs the quoted 900 mm) | Frame width: 2.70 m or 2.77 m for three panels |
| Does a ball compressing into the batten gap ever contact an LED? | Channel depth; whether a protective cover is needed |
| Wake-on-approach false triggers (pets, foliage, passers-by) | Default height threshold; whether wake is on by default |

The biggest single risk to the experience is the keeper looking rigged. If people believe the dive is chosen after the ball has landed, the core game is dead. Commit-before-impact is non-negotiable and it should be visibly demonstrable: the replay on the face after each kick exists partly to prove it.

The second biggest risk is the sensor tolerance being worse than assumed. If it's over ~150 mm, most of the target games need to be redesigned around zones rather than shapes, and the impact cross (which people will compare against where they saw the ball hit) becomes a liability. Measure this first.
