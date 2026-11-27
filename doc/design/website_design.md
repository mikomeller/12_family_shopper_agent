<!--
Author:    rhaveen-sa (with Claude Code)
Version:   0.1.0
Filename:  website_design.md
Pathname:  doc/design/website_design.md
Purpose:   Design brief for the Family Shopper Agent website, "Rings" design. For the colleague who updates the website.
           Mockup: doc/design/website_mockup.html. Same system as the pitch deck pitch/pitch.html.
-->
# Website design: "Rings"

Open [`website_mockup.html`](website_mockup.html) in a browser. It is a complete one-page mockup. Copy its tokens and components.

## Idea
Each family member is a ring that fills as they spend: teen blue (outer), child green (middle), family orange (inner).
The rings are the logo, the hero image and the progress shown on every key section. Everything else stays quiet:
light grey page, white cards, big black type, lots of space. One idea, used everywhere, is what makes it feel clean and its own.

## Tokens
| Token | Value | Use |
|---|---|---|
| `--bg` | `#f5f5f7` | page background |
| `--card` | `#ffffff` | cards, alternate sections |
| `--ink` | `#1d1d1f` | headlines, body text |
| `--mute` | `#6e6e73` | lead text, descriptions |
| `--soft` | `#86868b` | eyebrows, captions |
| `--teen` / `--teen2` | `#0a7cff` / `#5ac8fa` | teen ring, primary buttons, links |
| `--child` / `--child2` | `#28c76f` / `#a8e063` | child ring, Boris bullets |
| `--fam` / `--fam2` | `#ff8a00` / `#ffc24b` | family ring |
| `--no` | `#ff3b30` | refusals only |
| Radius | 28 px cards, 20 px small cards, 99 px buttons and chips | |
| Max width | 1120 px, 24 px side padding | |

Type: the system font stack (`-apple-system, BlinkMacSystemFont, "SF Pro Display", "Helvetica Neue", Arial`).
No web fonts are needed. Headline weight 700 with tight letter spacing (-0.035em to -0.045em). Body 15 to 22 px, line height 1.45.
The only gradient is the word highlight (blue to green to orange), used once per screen at most.

## Page sections (top to bottom)
1. **Nav.** Sticky, frosted glass. Small ring logo, three links, one blue "Get it on GitHub" button.
2. **Hero.** "Pocket money with guardrails." with the gradient on "guardrails". Lead line, two buttons, three chips
   (Live idealo MCP, Your own model and key, Limits in the wallet). Large animated rings on the right with "378.02 € family money left this month".
3. **One family, three rings.** Three white cards: 50 € teen, 20 € child, 400 € family. Each card has its own single ring.
4. **How it works.** White band. Three steps with coloured numbers: Connect idealo, Bring your own model, Set the limits.
5. **Every "no" explains itself.** A phone-like chat card showing a refusal with the amount left. Use a real screenshot of the app here when one exists.
6. **Trust.** The only black section. Two dark panels: what the wallet does, what Affinidi TrustBoris does. Keep the honest status chip on the Boris panel.
7. **Tested.** Four big numbers: 152 tests, 72/72, 13 × 3 scenarios, 0 limits exceeded.
8. **Closing.** Rings, "Hand your kids an agent, not your credit card.", the Docker command, GitHub button.
9. **Footer.** One line.

## Ring component
- SVG, `viewBox 0 0 240 240`. Radii 104, 78, 52. Stroke width 18. Round caps.
- Track: same colour at 13 % opacity. Arc: linear gradient from the light to the dark shade of the colour.
- End cap: a dot in the dark shade with a soft shadow, so the end of the arc reads even on small values.
- Small values get a minimum visible arc of 3 %.
- Animation: arcs fill over 1.6 s with an ease-out curve when the section scrolls into view.
  Respect `prefers-reduced-motion` (no animation).
- The script in the mockup (`ringSVG` and `fill`) can be copied as it is.

## Rules
- Use the numbers from the product (limits, test counts). Do not invent users, quotes or logos.
- Red only for a refusal. Blue for actions.
- One headline per section, at most two lines. One lead line under it.
- Mobile: below 860 px every grid becomes one column. The nav links hide.
- Do not use Apple's own product names, icons or the Activity rings artwork. Our rings use our own colours, three members and a money label.
