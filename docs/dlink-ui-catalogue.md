# D-Link DNS-345 web UI — extracted structure catalogue

Snapshot of `/usr/local/modules/web/` from a live DNS-345 running firmware
1.05. **1460 files, ~19 MB uncompressed.**

This catalogue is the empirical reference for which selectors / images /
paths we override. It's the answer to all the `/* TBD */` placeholders in
`theme/css/overrides.css`.

The raw extraction lives in `extracted/web/` (gitignored — pull it from
the NAS yourself if you need it).

## Top-level layout

```
/usr/local/modules/web/                  served by lighttpd as URL prefix /web/
├── pages/                               ← main management UI (the one we reskin)
│   ├── css/                             13 CSS files, ~1200 lines total
│   ├── images/
│   │   ├── logo.png    207×28 RGBA PNG  ← the "ShareCenter by D-Link" logo
│   │   ├── logo2.png    73×18 RGBA PNG  ← smaller variant
│   │   ├── logo_bg.jpg   6×94 JPG       ← vertical gradient strip
│   │   └── management/                  ← per-menu icons, banners
│   ├── function/                        177 JS modules (jQuery 1.6 + custom)
│   ├── jquery/                          jQuery UI 1.8.13 base
│   ├── help/                            inline help fragments
│   ├── *.html                           individual pages (management.html, home.html, ...)
│   └── (per-area dirs)                  account_mgr, app_mgr, backup_mgr, ...
├── MyMusic/                             SqueezeBox UI (separate app)
├── photo_center/                        Photo Center app (separate)
├── modules/                             lighttpd's compiled .so modules
├── config/                              lighttpd configuration
└── share/                               misc shared resources
```

**URL mapping**: lighttpd serves `/usr/local/modules/web/` at URL prefix `/web/`.
So `/web/pages/css/style.css` on the wire → `/usr/local/modules/web/pages/css/style.css`
on disk.

## CSS files that matter for the reskin

| File | Lines | Role |
|---|---|---|
| `pages/css/style.css` | 637 | Base typography, common element styling. Resets HTML/BODY/H1-H6, defines `.banner`, `.big_div_*`, `.div_*` |
| `pages/css/button_style.css` | 213 | All button variants: `.button`, `.button_min`, `.button_medium`, `.button_large`, `.button_max`, `.button_new`, `.button_login`, `.apply_button`, `.button_div`, etc. |
| `pages/css/main_menu.css` | 206 | Left navigation: `.main_menu`, `.main_menu_disable`, `.shareDiag`, `.diag_title`, `.icon`, `.hint_icon`, `.home_ul_list`, `.close`, `.desc` |
| `pages/css/dialog.css` | 102 | Modal/wizard dialogs (the popups we saw during RAID setup). `.dialog_overlay`, `.shareDiag` |
| `pages/css/style_mainFrame.css` | TBD | Iframe content styling (right-hand pane) |
| `pages/css/application.css` | TBD | Applications tab specific |
| `pages/css/help_style.css` | TBD | Right-side help iframe |
| `pages/css/accordion*.css` | TBD | Collapsible sections (Disk Management has them) |

The CSS is **circa 2011, in IE6/7-compatible uppercase form** (`FONT-SIZE: 11px`
not `font-size: 11px`). It's all manually authored, no preprocessor. Default
font: `Tahoma, Helvetica, Geneva, Arial, sans-serif` — we replace globally with
`JetBrainsMono Nerd Font`.

## Class name reference (from grep across all CSS)

Buttons:
- `.button`, `.button_min`, `.button_medium`, `.button_large`, `.button_max`,
  `.button_max_generic`, `.button_max_wizard`, `.button_new`, `.button_login`
- `.button_div`, `.button_div2`, `.button_display`, `.button_min_display`,
  `.button_medium_display`, `.button_large_display`, `.button_max_display`
- `.apply_button`, `.apply_off_button`

Layout:
- `.banner`, `.big_div_top`, `.big_div_body`
- `.div_top`, `.div_title`, `.div_body`, `.div_padding`
- `.accordion`, `.accordion_title`
- `.arrow_down`, `.arrow_right`

Menus:
- `.main_menu`, `.main_menu_disable`
- `.icon`, `.hint_icon`, `.home_ul_list`

Status / state:
- `.active`, `.enable`, `.disable`
- `.device_status`
- `.ui-state-active`, `.ui-state-custom` (jQuery UI base — used in tabs)

Dialogs:
- `.dialog_overlay` (the dim background behind a modal)
- `.shareDiag` (wizard popup container)
- `.diag_title` (wizard title bar)
- `.close`, `.desc`

Common:
- `.box`, `.clock`, `.banner`

## ID references (from grep across all CSS)

Hardcoded color values appearing as IDs (weird but: D-Link team named some IDs after their hex):
- `#A0DC00`, `#A9A9A9`, `#B9B9B9`, `#C0C0C0`, `#c4c4c4`, `#c5dbec`, `#c60`,
  `#cc0`, `#cccccc`, `#CCCCCC`, `#d9d9d9`, `#DAA520`, `#dfeffc`, `#e3e2e2`,
  `#e9e7e7`, `#E1EFFB`, `#F1F1F1`, `#f7f7f7`

(Many of these are colors used somewhere; we don't override these directly,
we just override the rules that use them.)

Real DOM IDs (observed via Playwright in our live setup):
- `#header`, `#sub_menu`, `#sub_menu2`, `#menu_container`
- `#icon_status`, `#icon_disk`, `#icon_account`, `#icon_network`, `#icon_app`, `#icon_sys`
- `#login_user`, `#my_home`, `#my_app`, `#my_management`
- `#title_banner`, `#title_div`
- `#formatdsk_Diag`, `#formatdsk_Diag_title` (RAID wizard)
- `#popup_button`, `#popup_ok2`, `#popup_cancel2`, `#popup_message`
- `#alert_overlay`

## HTML loading pattern

Pages are dynamically loaded with `document.write` of `<link>` and `<script>` tags.
That means we **can't** inject our CSS via a static `<link>` in the HTML head
without modifying every HTML file. We have two options:

1. **Bind-mount our CSS over an existing CSS file** (preferred — what we do).
   E.g. overlay our combined Colony CSS over `pages/css/style.css`. lighttpd
   serves the bind-mounted file; browser receives our content under the
   original URL.
2. **Append our `<script>` to a universally-loaded JS file** that uses
   `document.write` to inject `<link rel="stylesheet" href="/web/colony.css">`.
   More fragile but allows adding new files.

For v0.1.0, option (1) is the path.

## Image targets for replacement

Top priority (visible everywhere):
- `pages/images/logo.png` (207×28) — the "ShareCenter by D-Link" logo
- `pages/images/logo2.png` (73×18) — smaller variant
- `pages/images/logo_bg.jpg` (6×94) — header gradient strip

Menu icons (each as on/off pair, 6 menus):
- `pages/images/management/account_on.png`, `account_off.png`
- `pages/images/management/disk_on.png`, `disk_off.png`
- `pages/images/management/app_on.png`, `app_off.png`
- `pages/images/management/sys_on.png`, `sys_off.png`
- `pages/images/management/status_on.png`, `status_off.png`
- `pages/images/management/network_on.png`, `network_off.png`

Banner ornaments (header bar pieces):
- `pages/images/management/banner_left.png` (587 B)
- `pages/images/management/banner_left2.png` (1.0k)
- `pages/images/management/banner_center2.png` (273 B)
- `pages/images/management/banner_right.png` (583 B)
- `pages/images/management/banner_right2.png` (976 B)

Misc:
- `pages/images/management/account_off.png` etc — Amazon S3, app icons, etc.

We must match the **exact pixel dimensions** of the original — D-Link's CSS
has hardcoded width/height. Easy fix: just paint a Colony version at the
same size.

## JS files we should NOT touch

These contain real business logic. Overlaying them breaks the UI:
- `pages/function/management.js`, `init.js`, `function.js`
- `pages/function/wizard.js`, `volume_info.js`, `account.js`, `group.js`
- `pages/function/network_accessDiag.js`, `batch_user.js`
- Anything in `pages/jquery/` (it's vendored jQuery + plugins)

We will however introduce **one** new JS file:
- `pages/function/colony-injector.js` (loaded via bind-mount over an empty
  spot, or appended to `define.js` if needed) — its job is to fix up
  hardcoded text strings ("ShareCenter by D-Link" → "Colony NAS"), set the
  page title, and any DOM tweaks CSS can't do.

## Open questions for v0.1.0

- [ ] Does the firmware load `style.css` early enough that overriding it via
      bind-mount applies to the initial paint? Or is there a flash of
      unstyled D-Link before our CSS kicks in?
- [ ] Are some images inline (base64) in CSS `background-image: url(data:...)`?
      If yes those need CSS-level overrides, not file-level.
- [ ] What's the role of `style_mainFrame.css` vs `style.css`? Probably
      iframe content (right pane). Needs same treatment.
- [ ] `application.css` and `application_user.html` suggest a different
      stylesheet for the **Applications** top tab (where we found Remote
      Backups). Needs overlay too.

These get resolved when we draft `overrides.css` from real classes (vs the
guesses currently in there).
