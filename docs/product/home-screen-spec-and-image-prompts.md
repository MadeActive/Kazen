# Kazen — Home Screen Spec and Image-Generation Prompts

Sept 2026. Home is screen 3.1 in `screen-inventory-and-figma-prompt.md`. Design principles from the UX spec apply: one decision per screen, the Goal is the screen and the phone is the wallet, ask only when the answer matters, no news feed, no dashboard, no greeting.

---

## Part 1 — What is on Home

Home is a launcher. Its only job is to get a game onto the Goal in one tap, with the right players. Everything else is a glance, not a task.

### Layout, top to bottom

**1. Status bar (system).** Time, signal. Nothing custom.

**2. Header row.**
- Left: the KAZEN wordmark, small (24 px tall), black italic on whatever the background is.
- Right: one line of Goal status with a coloured dot. This is the only status indicator on the screen.

| Goal state | Dot | Copy | Tap does |
|---|---|---|---|
| Ready | green | `Goal ready` | nothing |
| Asleep | grey | `Goal asleep` | wakes it |
| Offline | red | `Can't reach your Goal` | opens offline help |
| Updating | amber | `Updating · 2 min` | opens Updates |
| Game running from the post button | pulsing green | `Jake's playing Keeper` | opens Playing |

No bell, no search, no avatar in the header. Notifications are two toggles in Settings; there is nothing to check.

**3. Players row.** Label above, small caps: `WHO'S PLAYING`.
- Horizontal row of chips. Each chip: a circle in the player's colour with their initial, name beneath in 12 px. Selected = filled circle with a tick. Not selected = outlined circle, name greyed.
- Default selection = whoever played last.
- Last chip: `+` outlined circle, label `Add`.
- If nobody is selected the row shows a small grey chip `Guest` selected automatically. Guest scores show but do not save.
- Long-press a chip opens that player's detail. No other gesture.

**4. Football games.** Section label, small caps: `FOOTBALL`.
- A 2-column grid of six tiles. Each tile: a bold pixel-style glyph (the same shape the Goal draws for that game), the game name in uppercase, one line of sentence-case subtitle. Tiles are tall enough to be a comfortable thumb target from a garden table (minimum 120 px).
- The tile for the last-played game carries a small tag in the corner: `LAST PLAYED`. That tile sits first in the grid so "tap the first tile" always equals "kick to play the last game" on the Goal.
- One tile may carry one line of personal context for the first selected player. Only these two:
  - Keeper tile: `vs The Wall` (the player's current keeper)
  - Power tile: `Best 74 km/h` (or `Best ▮▮▮▮▮▯▯` if speed is in power-bar mode)

| Tile | Glyph | Name | Subtitle |
|---|---|---|---|
| 1 | keeper silhouette, arms out | `KEEPER` | `Beat the keeper` |
| 2 | two big digits `3 – 2` | `SHOOTOUT` | `Penalties, 2+ players` |
| 3 | four lit corners | `CORNERS` | `Top bins` |
| 4 | a ring | `TARGETS` | `Hit it before it fades` |
| 5 | a large number `74` | `POWER` | `How hard can you kick?` |
| 6 | a low strip of blocks | `PASSING` | `Along the ground` |

**5. Arcade and party.** Section label: `ARCADE & PARTY`.
- Same tile component, but a single row of three, shorter (about 96 px) and visually quieter (thinner outline or lower contrast). This is the "secondary" signal without hiding them.

| Tile | Glyph | Name | Subtitle |
|---|---|---|---|
| 7 | rows of aliens | `INVADERS` | `Stop them landing` |
| 8 | a mole in a hole | `WHACK-A-MOLE` | `60 seconds` |
| 9 | three silhouettes | `DODGEBALL` | `Soft ball only` |

- A tenth tile, greyed with a dashed outline: `MORE GAMES` with subtitle `Coming soon`. Not tappable. Shows that the grid grows without promising dates.

**6. Today's clips.** Section label: `TODAY'S CLIPS`. The whole section is hidden when there are no clips today.
- Horizontal strip of 16:9 thumbnails, newest first, scrolls sideways. Each thumbnail: the frame at impact, and in the corner the overlay in miniature: result word and speed, e.g. `GOAL · 68`.
- One line of small grey text beneath the strip: `Clips stay on your Goal until you share them.`

**7. Tab bar.** Three tabs, icons with labels: `Play` (selected), `Us`, `Goal`. Playing is not a tab; it appears on its own when a game is running.

### Tile states
- **Default.** As above.
- **Needs players.** Shootout with one player selected: tile stays tappable, the options sheet asks for a second player. No greyed state here; the fix is one tap away.
- **Needs full Goal.** On the single-panel prototype, tiles that need 39 columns show the subtitle replaced by `Needs full Goal` and are not tappable.
- **Pressed.** Fills with the player's colour for the duration of the press. Small touch of identity, costs nothing.
- **Goal offline.** Tiles stay visible and tappable; tapping shows the toast `Can't reach your Goal`. The grid never disappears, so the app still looks like itself when the Goal is off.

### What is deliberately not on Home
Greeting or headline, weekly summary, charts, streak flame, notifications, search, filters, settings shortcuts other than the tab, promotional cards, the keeper roster, a "start" button separate from the tiles. The parent's "This week: 42 kicks" sentence lives on the Us tab.

### Copy rules on this screen
- Game names uppercase, matching the words the Goal itself shows.
- Subtitles sentence case, under five words, no full stops, no exclamation marks.
- Status copy is a statement, never an instruction ("Goal asleep", not "Tap to wake your Goal").
- Numbers rounded, no decimals, unit after a space: `74 km/h`.

---

## Part 2 — Prompts for ChatGPT image generation

### The brand system, as read from `Design/Brand/Style/`
The 40 references point one way. Written down so the prompts and any designer start from the same place:

- **Palette of three.** Acid green (about #C6FF00), green-black (about #0B0F0A, a black with a hint of green), ice white (about #EDEFEA). Nothing else except the players' identity colours and the fixed result colours (green success, amber near miss, red fail).
- **Type.** A heavy, condensed, italic display face for the wordmark and any word that shouts (the KAZEN wordmark, game names, result words). Tight uppercase, letters almost touching. A neutral grotesque (Helvetica Neue / Inter class) for everything else, regular weight, sentence case.
- **Voice.** Short declaratives in caps: "BUILT FOR THOSE WHO NEVER SKIP TRAINING". For Kazen the equivalent are the Goal's own words: KICK, GOAL, SAVED, NEW BEST, BEAT ME.
- **App UI convention in the references.** Black screens, one accent used sparingly for the primary action and the selected state, white text, dark-grey cards with soft corners, one enormous number per screen, photography only as full-bleed hero when it earns its place.
- **Photography.** Real people, real light, sweat and grain, the green appearing on kit and glasses rather than as a filter. For Kazen: kids and adults in a normal garden at dusk, the Goal glowing.
- **Motif.** The Goal's own LED grid. Every icon on the phone should be drawable on a 39 × 36 dot grid.

Image models render text unreliably. The prompts below list every word that should appear so the model has less to invent. Ask for one phone per image; ask for a 2 × 2 grid only when comparing layouts and expect the text to blur.

### Master prompt (paste as-is, then append one variant block)

> A high-fidelity UI mockup of a single iPhone screen, portrait, straight-on, no hand, the phone centred on a plain green-black backdrop. The app is called KAZEN, a companion app for an outdoor LED football goal. This is the Home screen. It is a game launcher, not a dashboard: no charts, no greeting, no feed, no promotional cards.
>
> Brand: exactly three colours. Acid green #C6FF00 as the single accent, green-black #0B0F0A background, ice white #EDEFEA text. Display type is a heavy condensed italic sans in tight uppercase, like a sports brand wordmark. Body type is a plain neutral grotesque. The look is a premium sports-training app: black, sparse, confident, one big accent, nothing decorative.
>
> Layout from top to bottom:
> 1. Header row: the wordmark "KAZEN" small on the left in heavy condensed italic caps, ice white. On the right a small acid-green dot and the text "Goal ready" in body type.
> 2. A tiny uppercase label "WHO'S PLAYING" above a horizontal row of four circular avatar chips: a solid acid-green circle with a black letter J and the name "Jake" beneath, a solid orange circle with M and "Mia", an outlined grey circle with D and "Dad", and an outlined circle with a plus sign labelled "Add". The two solid circles carry a small black tick.
> 3. A tiny uppercase label "FOOTBALL" above a two-column grid of six large square tiles. Tiles are dark grey #161A16 with soft 16 px corners and no border. Each tile has a bold pixel-art icon drawn in acid green dots at the top left, the game name in heavy condensed italic caps in ice white, and a one-line grey subtitle in body type. Tiles in order: "KEEPER" with a goalkeeper silhouette arms outstretched, subtitle "Beat the keeper", a small acid-green pill in the top-right corner reading "LAST PLAYED" in black, and a line "vs The Wall"; "SHOOTOUT" with big pixel digits "3–2", subtitle "Penalties, 2+ players"; "CORNERS" with four lit corner blocks, subtitle "Top bins"; "TARGETS" with a pixel ring, subtitle "Hit it before it fades"; "POWER" with the number "74" drawn huge in acid green, subtitle "How hard can you kick?" and a line "Best 74 km/h"; "PASSING" with a low row of pixel blocks, subtitle "Along the ground".
> 4. A tiny uppercase label "ARCADE & PARTY" above a single row of three shorter, quieter tiles with icons in grey rather than green: "INVADERS" with pixel aliens, "WHACK-A-MOLE" with a mole, "DODGEBALL" with three silhouettes.
> 5. A tiny uppercase label "TODAY'S CLIPS" above a horizontal strip of three 16:9 video thumbnails, real photographs of a kid kicking a football at a glowing green LED goal in a garden at dusk, grainy and natural. Each has a tiny corner overlay in acid green reading "GOAL · 68", "SAVED · 61", "BULLSEYE · 72". Beneath the strip one line of small grey text: "Clips stay on your Goal until you share them."
> 6. A bottom tab bar on green-black with three items: "Play" (acid green, selected), "Us", "Goal" in grey.
>
> All pixel-art icons look like they were lit on a coarse LED dot grid, echoing the product. Generous spacing, large tap targets, readable at arm's length. Render all text exactly as written, no extra words, no extra icons.

### Variant blocks (append one at a time)

**V1. Dark, cards (the default, closest to Strongr and Nike Run+ in the references).**
> Variant: as described. Tiles are dark-grey cards on the green-black background. The only acid green on the screen is the status dot, the selected avatar, the LAST PLAYED pill, the icons on the six football tiles, the POWER number, the clip overlays and the selected tab.

**V2. Dark, outlined (closer to the REPZ poster system).**
> Variant: no filled cards. Tiles are transparent with a 1 px acid-green outline and square corners, icons in acid green, names in ice white. The header wordmark is larger, about 40 px tall. Feels like the REPZ billboard translated to a phone: black, green line-work, condensed caps.

**V3. Ice white mode (daytime in the garden).**
> Variant: ice white #EDEFEA background, green-black text and icons, tiles are white cards with a hairline grey border, acid green used only for the status dot, the selected avatar, the LAST PLAYED pill and the selected tab. Same layout, same copy. This tests whether the brand survives sunlight readability, since the phone is used outdoors.

**V4. Hero clip (the one time photography leads).**
> Variant: the top third of the screen is a full-bleed photograph of a kid mid-kick at the glowing goal at dusk, with the wordmark "KAZEN" overlaid bottom-left in heavy condensed italic caps in acid green and the text "Goal ready" bottom-right. The WHO'S PLAYING row sits directly beneath the photo. The rest of the layout is unchanged. Use this to judge whether a hero image adds anything or just pushes the games down.

**V5. Big-number launcher (Mojo / sports-graphic energy).**
> Variant: the KEEPER tile is twice the height of the others and spans both columns at the top of the grid, showing a large acid-green goalkeeper silhouette and the words "BEAT ME" in heavy condensed italic caps, with "vs The Wall" and the LAST PLAYED pill. The remaining five football tiles sit beneath it in the two-column grid. Everything else unchanged. Tests a "one hero game" hierarchy against the flat grid.

### Companion screen (ask for once V1 is chosen)
> Same brand and phone. The "Playing" screen shown while a game runs on the Goal. Green-black background. Top: small grey text "SHOOTOUT · KICK 3 OF 5". Centre: the name "JAKE" in heavy condensed italic caps, ice white, then the score "3 – 2" enormous in acid green filling a third of the screen height, then a small goal outline drawn in grey dots with a single acid-green cross in the top-left corner, then the result line "GOAL · 68 km/h" in ice white. Bottom: a single small grey text link "End". Nothing else on the screen. Designed to be read from two metres away on a garden table.

### Variations worth asking for after the first pass
- Same screen with `Goal asleep` and a grey dot instead of `Goal ready`.
- Same screen with the Today's clips section removed (a day with no clips).
- Same screen with `Jake's playing Keeper` in the header, to see how the join-a-running-game state reads.
- A two-phone image: Home on the left, Playing on the right, to check the pair feel like one product.

### Prompt hygiene for image models
- One variant per image; combining two produces mush.
- If text comes out wrong, re-run with "render text exactly, no additional words or icons" at the end, or ask for placeholder bars instead of text and judge layout only.
- Ask for a 1024 × 1536 portrait canvas or a 9:19.5 aspect.
- Save the keepers into `Design/Research/Kazen-home-explorations/` with the variant number in the filename so the choice is traceable.
