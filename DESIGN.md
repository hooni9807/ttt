---
name: TTT
description: 폰 한 대로 찍은 탁구 스윙을 브라우저 안에서 3D로 복원해 보여 주는 분석 앱
colors:
  floor: "#0B2340"
  table: "#17457A"
  table-deep: "#123A66"
  viewer-table: "#10325C"
  line: "#FFFFFF"
  ball: "#F28C28"
  ink: "#FFFFFF"
  ink-2: "#C9D8EC"
  ink-3: "#9DB4D3"
  ok: "#7FD8A6"
  warn: "#FF9A8A"
  trail-slow: "#9CC2EE"
typography:
  wordmark:
    fontFamily: "Pretendard Variable, Pretendard, system-ui, sans-serif"
    fontSize: "22px"
    fontWeight: 900
    letterSpacing: "0.18em"
  display:
    fontFamily: "Pretendard Variable, Pretendard, system-ui, sans-serif"
    fontSize: "clamp(28px, 7vw, 44px)"
    fontWeight: 800
    lineHeight: 1.2
    letterSpacing: "-0.02em"
  headline:
    fontFamily: "Pretendard Variable, Pretendard, system-ui, sans-serif"
    fontSize: "22px"
    fontWeight: 800
  title:
    fontFamily: "Pretendard Variable, Pretendard, system-ui, sans-serif"
    fontSize: "18px"
    fontWeight: 800
  feedback:
    fontFamily: "Pretendard Variable, Pretendard, system-ui, sans-serif"
    fontSize: "20px"
    fontWeight: 700
    lineHeight: 1.45
  body:
    fontFamily: "Pretendard Variable, Pretendard, system-ui, sans-serif"
    fontSize: "16px"
    fontWeight: 400
    lineHeight: 1.6
    fontFeature: "tnum"
  label:
    fontFamily: "Pretendard Variable, Pretendard, system-ui, sans-serif"
    fontSize: "14px"
    fontWeight: 600
  caption:
    fontFamily: "Pretendard Variable, Pretendard, system-ui, sans-serif"
    fontSize: "12px"
    fontWeight: 400
rounded:
  table: "6px"
  pill: "999px"
spacing:
  gutter: "16px"
  half-mobile: "32px 22px"
  half-desktop: "44px 48px"
  section-gap: "40px"
components:
  button-ball:
    backgroundColor: "{colors.ball}"
    textColor: "{colors.floor}"
    typography: "{typography.title}"
    rounded: "{rounded.pill}"
    padding: "0 28px"
    height: "56px"
  button-ghost:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    rounded: "{rounded.pill}"
    padding: "0 20px"
    height: "48px"
  button-icon:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    rounded: "{rounded.pill}"
    size: "44px"
  phase-chip:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    rounded: "{rounded.pill}"
    height: "44px"
  phase-chip-active:
    backgroundColor: "{colors.line}"
    textColor: "{colors.floor}"
    rounded: "{rounded.pill}"
    height: "44px"
  table-panel:
    backgroundColor: "{colors.table}"
    textColor: "{colors.ink}"
    rounded: "{rounded.table}"
    padding: "{spacing.half-mobile}"
---

# Design System: TTT

## Overview

**Creative North Star: "The Table Surface"**

The screen is a match table seen from above. A floor-navy ground holds one or more blue table tops, each framed by a white boundary line and split by a white net line; every working area sits inside one of those courts. The world rejects the default analysis-app layout of dark cards in a grid: panels are courts, dividers are painted lines, and the only warm thing on the page is the ball.

The system is dense but calm, built for one hand on a phone under bright hall lighting. Large touch targets (44px minimum, 56px for the primary action), high-contrast white-on-blue type, and tabular numerals so measurements line up. Motion is limited to the ball: it rolls along white lines on the progress rail and the scrubber, and the result view rises in once.

The 3D viewer belongs to the same world: its floor is the hall floor, its stage is a blue table top with white lines, the skeleton is drawn in white, and the impact point is the orange ball.

**Key Characteristics:**
- Floor navy ground, table blue panels, white 5px boundary and 3px net lines.
- Orange appears only on things you can press and on impact.
- Pills and circles for controls; near-square 6px corners for table tops.
- Single family (Pretendard), weight carries hierarchy, numbers are tabular.
- Status is mint (inside pro range) or coral (outside), never orange.

## Colors

A cool two-blue court palette with white lines, one warm ball accent, and two soft status hues.

### Primary
- **Ball Orange** (`ball`): the primary button fill, progress and scrubber thumbs, focus ring, text caret, selection, the impact line on the power-chain tracks, and the 3D impact marker. Nothing else.

### Neutral
- **Hall Floor Navy** (`floor`): page background, 3D ground plane, and the ink on any white or orange fill.
- **Table Blue** (`table`): every table-top panel and the small pose plates.
- **Deep Table Blue** (`table-deep`): field surfaces on the table (the select).
- **Viewer Table Blue** (`viewer-table`): the 3D canvas clear colour, a step darker than the table so the 3D table top reads against it.
- **Court Line White** (`line`): boundary, net, scrubber track, active segment and phase fills, the 3D skeleton.
- **Ink** (`ink`), **Ink 2** (`ink-2`), **Ink 3** (`ink-3`): primary text, secondary text (ledes, labels, units), tertiary text (hints, footnotes, axis ticks). Translucent white (0.18–0.35 alpha) draws hairline row dividers inside a court.
- **Slow Trail Blue** (`trail-slow`): the wrist trail's low-speed end in 3D; it lerps to Ball Orange at peak speed.

### Status
- **Range Mint** (`ok`): inside the pro reference range; good verdicts.
- **Range Coral** (`warn`): outside the range, the "fix next" headings, errors.

### Named Rules
**The Ball Rule.** Orange is the ball: it marks what can be pressed and the moment of impact. It is never a status colour, a heading colour, or decoration.

**The Painted Line Rule.** Structure is drawn with white court lines (5px boundary, 3px net, 1px translucent hairlines), not with shadows, tinted cards, or extra background shades.

## Typography

**Display Font:** Pretendard Variable (with Pretendard, system-ui, sans-serif)
**Body Font:** Pretendard Variable
**Label/Mono Font:** none; numbers use `tabular-nums` site-wide.

**Character:** One Korean grotesque doing everything; hierarchy comes from weight (400 to 900) and size, not from a second face. Korean text uses `word-break: keep-all`.

### Hierarchy
- **Wordmark** (900, 22px, 0.18em tracking): the TTT mark only.
- **Display** (800, clamp(28px, 7vw, 44px), 1.2, -0.02em): the start-screen headline, balanced.
- **Headline** (800, 22px): the current analysis step and the "fix next" callout heading.
- **Title** (800, 18px): section headings; also the primary button label size.
- **Feedback** (700, 20px, 1.45, max 36em): the one correction sentence, larger than the numbers around it.
- **Figures** (800, 20–28px): readout values and impact speed, with 600 13px units in Ink 2.
- **Body** (400, 16px, 1.6, max 34em): ledes and tips.
- **Label** (600–700, 13–15px): segment labels, table headers, phase buttons.
- **Caption** (400, 12–13px, Ink 3): hints, axis ticks, footnotes.

### Named Rules
**The Advice-First Rule.** The correction sentence is set larger and heavier than any measured number near it; the next thing to fix outranks the data.

## Layout

A single centred column, max 1180px, 16px side gutter. Each screen is one table (start, result stage) or a sequence of sections on the floor below it.

- **Mobile (default):** a table is split into two halves stacked top and bottom by a 3px horizontal net; halves pad 32px × 22px. Short 22px centre-line stubs mark the table's top and bottom edge midpoints. On the result stage the 3D viewer fills the table (min(62vh, 560px), min 340px) and the source video sits as a corner picture-in-picture (32% wide, max 220px) with a white 2px border.
- **≥900px:** the start table turns sideways: two courts left and right of a vertical 3px net, halves pad 44px × 48px. The single result screen grows to min(70vh, 640px). Sections below go two-up with 56px column gap; wide sections span both.
- **Rhythm:** 8/10/12px gaps inside controls, 14–18px between heading and content, 40px between sections, 56px bottom clearance plus the safe-area inset.

## Elevation & Depth

Flat. Depth is the table-on-floor contrast plus painted white lines, not shadow. The one exception is the ball: orange elements cast a short navy shadow as if lifted off the table.

### Shadow Vocabulary
- **Ball lift** (`box-shadow: 0 6px 18px rgba(3,12,26,.35)`, hover `0 10px 24px rgba(3,12,26,.4)`): primary button.
- **Ball contact** (`box-shadow: 0 3px 8px rgba(3,12,26,.45)`): progress ball and scrubber thumb.

### Named Rules
**The Only-The-Ball-Floats Rule.** Shadows belong to orange ball elements alone. Tables, plates, and ghost controls stay flat.

## Shapes

Two families. Table tops, pose plates, video frames, and the focus ring use a near-square 6px corner, like a real table edge. Everything pressable is a pill (999px) or a circle: the primary and ghost buttons, the handedness segment, phase buttons, icon buttons, and the ball itself. Borders are white and thick: 5px on a table, 3px on a plate and nets, 2px on controls. Icons are 20px stroked line icons at 2px, round caps.

## Components

### Buttons
- **Ball (primary):** an orange pill, 56px tall, 0 28px padding, navy 800 18px label with icon; full width up to 420px on the start screen. Hover lifts 1px with a deeper shadow; active presses 1px down.
- **Ghost:** transparent pill, 48px tall, 2px white border, 700 label; hover fills 10% white.
- **Icon:** 44px white-bordered circle (play/pause); hover fills 10% white.
- **Text:** Ink 2, 14px, underlined at 40% white with 4px offset; hover to full Ink.
- **Focus (all):** 3px Ball Orange outline, 3px offset.

### Chips
- **Handedness segment:** a 2px white pill containing two 44px-tall labels; the checked one fills white with navy text.
- **Phase buttons:** three equal 44px pills with a white 2px border; `aria-pressed` fills white with navy text.

### Cards / Containers
- **Table panel:** Table Blue, 5px white border, 6px corners, centre-line stubs, halves split by a 3px net. No shadow.
- **Pose plate:** a miniature table (3px white border, 6px corners) holding a stick-figure SVG and a bold 13px caption.
- **Readout strip:** four columns under a 3px net line, divided by 1px translucent hairlines; 12px label over 20px 800 figure.

### Inputs / Fields
- **Select:** 44px tall, 8px corners, 2px 50%-white border on Deep Table Blue.
- **Scrubber:** a 3px white track (the net) with a 22px orange ball thumb.

### Navigation
- **Top bar:** wordmark left, handedness segment right, 14px vertical padding, on the floor (not on a table).

### Ball on the Net (signature)
The progress rail and the scrubber are the same device: a 3px line with a filled white portion and an orange ball riding it. While waiting for an unknown duration the ball rolls back and forth (1.4s, `cubic-bezier(.16,1,.3,1)`, alternate). In the power-chain chart each joint lane is a thin white track with white peak dots and a short orange tick at the impact end.

### 3D Viewer
Clear colour Viewer Table Blue over a floor-navy ground with one translucent white ring under the feet; no table is drawn, because a single camera cannot tell where the table is. The body is a lit mannequin: white cylinder bones and sphere joints (bone radius ~3cm, joints ~4cm, head 10cm), with the hitting arm in a warm tint (#FFB877). The wrist trail covers only backswing→finish as a 16mm tube coloured from Slow Trail Blue to Ball Orange by speed: the whole path sits at 25% opacity and the part already played draws solid. An orange sphere marks impact. The view opens from the video camera's position; pill buttons (영상 시점 / 옆 / 위) ease the camera to presets over 450ms, and dragging clears the selection.

### Swing Score
Top of the feedback court: the total in 56px/800 white with a 20px "/ 10", a 14px "종합 점수 · 항목 평균 · 참고용" label, then one row per scored part, each out of 10 (name, Ball-on-the-Net bar filled to its share, "g/10"), and a note naming which parts had criteria. A 3px white net line separates it from the fixes below. At ≥900px the number and the bars sit side by side.

### Off-range wording
When a measured value falls outside a pro range, the screen states the gap in words next to the range: 팔꿈치 "N° 더 접힘 / 더 펴짐", 무릎 "더 굽힘 / 더 펴짐", 몸통 꼬임 "덜 꼬임 / 더 꼬임", 스윙 면 기울기 "더 눕힘 / 더 세움". Swing plane is one value per swing, shown under the wrist speed in the comparison section.

### Video Overlay
The result stage is one screen. With 3D off it shows the original video with the 2D skeleton drawn on a canvas over the video's contain-fit rectangle; with 3D on it shows the 3D scene, and the video (if still on) shrinks to a bordered inset at the top-right. Same colour rules as 3D: white bones and joints with a dark 3px outline so they read on any footage, the hitting arm in #FFB877, a head circle between the ears, the wrist path backswing→finish faint white with the played part solid orange, and an orange dot at impact. Four independent pill toggles (영상 / 스켈레톤 / 궤적 / 3D) sit bottom-left and combine freely: 스켈레톤 and 궤적 apply to both the 2D overlay and the 3D scene; the 3D camera presets appear above them only while 3D is on. With the video off, the dark letterbox ground stays. A JSON opened without video forces 3D on and disables 영상.

## Do's and Don'ts

### Do:
- **Do** put every working area inside a Table Blue panel with a 5px white boundary, and split it with a 3px white net.
- **Do** reserve Ball Orange for pressable controls, focus, progress/scrub thumbs, and impact.
- **Do** use mint for inside-range and coral for outside-range, each paired with an icon and words.
- **Do** keep touch targets at 44px or larger; the primary action is 56px.
- **Do** set every number with tabular figures and its unit in smaller Ink 2.
- **Do** keep the 3D view the largest element on the result screen at every width.
- **Do** disable all animation and transition under `prefers-reduced-motion`.

### Don't:
- **Don't** build dark cards in a grid; panels are courts on a floor.
- **Don't** use orange for status, headings, or decoration.
- **Don't** add shadows to tables, plates, or ghost controls.
- **Don't** introduce a second typeface; vary weight instead.
