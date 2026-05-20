# DNS-345 Colony Edition

A beige + burgundy "Colony" reskin for the D-Link DNS-345 ShareCenter web UI,
packaged as a one-click `.module` add-on. **No NAND flash required.**

![status](https://img.shields.io/badge/status-WIP-yellow)
![target](https://img.shields.io/badge/target-DNS--345%20FW%201.05-blue)
![brick%20risk](https://img.shields.io/badge/brick%20risk-zero-success)

```
  ┌──────────────────────────────────┐       ┌──────────────────────────────────┐
  │ D-Link stock UI                  │       │ Colony Edition                   │
  │                                  │       │                                  │
  │  ████ gray metallic header       │  -->  │  ▒▒▒▒ parchment header           │
  │  blue buttons, dark text         │       │  burgundy buttons, ink text      │
  │  ShareCenter by D-Link logo      │       │  Colony NAS logo                 │
  └──────────────────────────────────┘       └──────────────────────────────────┘
```

## What this is (and isn't)

**Is** a runtime UI overlay. fun_plug runs at boot, bind-mounts Colony CSS
files over the squashfs ones, lighttpd happily serves them. The D-Link
firmware on NAND is untouched.

**Isn't** a real firmware replacement. The kernel, the CGI binaries, the
web server, the underlying business logic — all still D-Link's 2016 stock.
We just repaint the surface.

**Why the overlay approach?** Flashing custom firmware on a 6+ year old NAS
risks a brick that needs serial TTL + U-Boot fiddling to recover. The
overlay approach is reversible by deleting one `.module` file from the
Add-Ons UI.

## How it works

```
                          /dev/loop0 (squashfs RO)
                          ┌───────────────────────────┐
                          │ /usr/local/modules/web/   │
                          │   styles/main.css   (D-L) │  ← mount source
                          │   images/logo.png   (D-L) │
                          │   ...                     │
                          └───────────────┬───────────┘
                                          │
                          mount --bind    │   (Linux mount namespace)
                                          ▼
                          ┌───────────────────────────┐
                          │ /usr/local/modules/web/   │   ← what lighttpd
                          │   styles/main.css ← OVR   │     actually sees
                          │   images/logo.png ← OVR   │
                          │   ...                     │
                          └───────────────────────────┘
                                       ▲
                                       │ bind source
                          ┌────────────┴──────────────┐
                          │ /ffp/colony/overlay/      │   ← Colony assets
                          │   styles/main.css         │     from this module
                          │   images/logo.png         │
                          └───────────────────────────┘
```

At boot:

1. `fun_plug` runs `/ffp/etc/rc` which sources every `.sh` in `/ffp/start/`
2. `/ffp/start/colony.sh` walks `/ffp/colony/overlay/` and does a
   `mount --bind <ours>/<path> /usr/local/modules/web/<path>` for each file
3. lighttpd, which serves from `/usr/local/modules/web/`, transparently
   serves the bind-mounted Colony files

Uninstall = delete the `.module` from Add-Ons UI → next reboot, no bind
mounts, original D-Link UI returns intact.

## Repository layout

```
dns345-colony-edition/
├── README.md                 # this file
├── theme/                    # Colony brand source-of-truth
│   ├── css/
│   │   ├── colony-tokens.css # canonical palette + typography (ported from H&E)
│   │   └── overrides.css     # actual D-Link UI selectors → Colony tokens
│   ├── assets/               # logos, icons, backgrounds
│   └── fonts/                # JetBrainsMono Nerd Font family
├── module/                   # .module packaging
│   ├── manifest.json         # D-Link Add-Ons module metadata
│   ├── scripts/
│   │   ├── install.sh        # runs on .module install
│   │   ├── uninstall.sh      # runs on .module remove
│   │   └── colony.sh         # the boot hook that applies bind mounts
│   └── build.sh              # bundles theme/ into a .module artifact
├── docs/                     # how the D-Link UI is structured + reverse eng notes
└── extracted/                # gitignored: dumps of the D-Link squashfs for study
```

## Brand palette

Single source of truth: `theme/css/colony-tokens.css`.
Values match `HeavenAndEarth_Godot/client/scripts/ui_style.gd` and
`SAM-Colony-Edition/src/styles/theme.css` exactly.

| Token | Hex | Use |
|---|---|---|
| `--colony-ink` | `#2e1a14` | Main text, outlines |
| `--colony-ink-dim` | `#664233` | Secondary text |
| `--colony-red` | `#7d2333` | Primary action, highlights |
| `--colony-parchment` | `#fffcf2` | Base surface |
| `--colony-parchment-hover` | `#fcefdb` | Hover state |
| `--colony-parchment-pressed` | `#f2e1c7` | Pressed state |

See `theme/css/colony-tokens.css` for the full list (12 colors + typography
+ geometry tokens).

Font: **JetBrainsMono Nerd Font** across the board, weights 300-700.

## Project status

- [x] Palette extracted from H&E + SAM Colony Edition (single source of truth)
- [x] Repo scaffolded
- [x] D-Link squashfs extracted and catalogued (`docs/dlink-ui-catalogue.md`)
- [x] Selector map drafted from extracted CSS
- [x] `theme/css/overrides.css` (250 lines, real selectors)
- [x] `theme/scripts/build-assets.py` generates 48 Colony PNG sprites
- [x] Bind-mount script `module/scripts/colony.sh` (idempotent, with stop/status)
- [x] `build.sh` produces a working `dns345-colony-edition.module`
- [x] Tested end-to-end on a real DNS-345 (login, home, management all work)
- [ ] `.module` format empirically validated against D-Link's Add-Ons UI (currently installs cleanly via manual SSH)
- [ ] Polish: overlay `pages/images/setup_wizard.png` + the small icons for My Photos/Files/Music/Cloud
- [ ] Released as v0.1.0

## Screenshots (v0.1.0-dev, manual SSH install)

| Before (D-Link) | After (Colony) |
|---|---|
| dark header, grey gradient, Tahoma | parchment, JetBrainsMono, burgundy accents |

See `docs/screenshot-login.png`, `docs/screenshot-home.png`,
`docs/screenshot-management.png` for the current look.

## Compatibility

Built and tested for the **DNS-345** with stock firmware **1.05** (the final
D-Link release, dated November 2016).

The web UI codebase appears identical across the DNS-3xx ShareCenter family
(DNS-320, DNS-320L, DNS-325, DNS-345), so the same `.module` should work on
all of them — but only DNS-345 is in scope for v0.1.0. PRs from
DNS-32x owners welcome.

## Related repos

- [`MotherSphere/dotfiles/dns345/`](https://github.com/MotherSphere/dotfiles/tree/main/dns345)
  — original procedural setup for git-server-on-DNS-345, the work that led
  to this project
- [`MotherSphere/dns345-fun_plug`](https://github.com/MotherSphere/dns345-fun_plug)
  — vendored mirror of the fun_plug bootstrap source
- [`MotherSphere/dns345-funplug-recipes`](https://github.com/MotherSphere/dns345-funplug-recipes)
  — vendored fork of SirUli/funplug build recipes (where modernized packages
  will be built)

## License

Code in this repo: same as the parent MotherSphere org default (TBD).

Brand assets (Colony palette, logos) are MotherSphere's. Don't ship a
rebrand of Colony Edition as your own; fork the structure but ship under
your own branding.

D-Link assets (default UI we're overlaying) belong to D-Link. This project
doesn't redistribute D-Link's CSS or images; it only *overlays* its own
on a running system at runtime.
