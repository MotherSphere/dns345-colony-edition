# Overlay mechanism: how Colony Edition repaints the D-Link UI without flashing

## The challenge

The DNS-345 web UI is served by `lighttpd` (running from `/usr/local/modules/`)
out of a **squashfs read-only mount** on `/dev/loop0`. We can't simply
overwrite `/usr/local/modules/web/styles/main.css` — the underlying
storage is read-only, and even if we could write, it'd revert after a
reboot from NAND.

## The trick: bind mounts

Linux's `mount --bind` lets you make any file appear at any path in the
filesystem namespace, regardless of what's actually stored underneath.
The bind mount lives only in the kernel's mount table; it's free, fast,
and doesn't touch storage.

```sh
mount --bind /ffp/colony/overlay/styles/main.css \
             /usr/local/modules/web/styles/main.css
```

After this command, any process that opens
`/usr/local/modules/web/styles/main.css` (including `lighttpd` serving
the file to a browser request for `/styles/main.css`) sees the Colony
version. The squashfs file underneath is untouched and unreachable until
we `umount` the bind.

This is the same mechanism Docker, Flatpak, Nix sandboxing, and chroot
escapes use. It's been in Linux since the 2.4 kernel, and the DNS-345's
2.6.31 kernel supports it natively.

## What we override

The D-Link web UI is conventional 2011-era frontend code: HTML, CSS,
small JS modules. The bits we care about:

```
/usr/local/modules/web/
├── styles/main.css          ← main color tokens, will be replaced
├── styles/menu.css          ← left nav appearance
├── styles/wizards.css       ← popup dialog styling
├── images/
│   ├── logo.png             ← D-Link "ShareCenter" logo → Colony logo
│   ├── header_bg.png        ← gray metallic header → parchment header
│   ├── btn_*.png            ← button backgrounds in blue → burgundy versions
│   └── icon_*.png           ← left nav icons
├── function/define.js       ← bootstrap JS, we'll inject the Colony stylesheet
└── (HTML files left untouched)
```

We don't need to modify HTML at all — injecting a stylesheet via
`function/define.js` (which every page sources) lets us add CSS that
overrides the D-Link styles by specificity / source order.

## What we **don't** touch

- The CGI binaries (`/cgi-bin/*.cgi`) — they're proprietary D-Link, we
  don't reimplement business logic
- Any JS that handles actual NAS operations (RAID config, share creation,
  etc.) — overlaying these would be fragile and bring zero brand value
- Anything outside `/usr/local/modules/web/`

The principle: **only repaint pixels, never re-implement features**.

## Lifecycle

```
boot
  → kernel mounts /dev/loop0 onto /usr/local/modules (squashfs RO)
  → fun_plug bootstrap finds /mnt/HD/HD_a2/fun_plug.tgz
  → /ffp/etc/rc sources all /ffp/start/*.sh
  → /ffp/start/colony.sh runs `start`
    → walks /ffp/colony/overlay/ tree
    → for each file: mount --bind it over /usr/local/modules/web/<same-path>
    → records each mount in /ffp/var/run/colony-mounts.list
  → lighttpd starts (or restarts)
  → browser hits :80, gets Colony-painted UI
```

To uninstall:
1. **Application Management → Add Ons → Delete** the `dns345-colony-edition`
   row in the UI
2. Reboot the NAS
3. fun_plug runs but `/ffp/start/colony.sh` is gone, no binds happen
4. lighttpd serves the original D-Link squashfs files

To temporarily disable without uninstalling:
- Use the Start/Stop column in the Add-Ons UI, which invokes
  `/ffp/start/colony.sh stop`
- That iterates `colony-mounts.list` in reverse and umounts each bind
- Refresh browser, original UI is back

## Edge cases we've thought about

**Bind mount over a file that doesn't exist**
- `mount --bind` requires the target to exist. We check
  `[ -e "$dst" ]` before attempting; missing targets are logged and skipped.
- This means we can ship overlay files for paths that don't exist on
  every firmware variant — they just no-op on firmwares that lack them.

**Firmware update from D-Link**
- D-Link could theoretically push firmware 1.06 that changes file paths.
  In that case our binds reference now-nonexistent paths and silently
  no-op. The user sees the new D-Link UI. Not a brick, just degraded.
- D-Link hasn't pushed firmware since 2016 so this is hypothetical.

**Module fails to extract**
- `/ffp/start/colony.sh` defensively logs to `/ffp/var/log/colony.log`
  and exits clean. The rest of fun_plug continues. SSH/telnet/etc still
  work, so we're never locked out.

**File-level bind vs directory-level bind**
- We use **per-file** binds, not a directory-level bind over `/usr/local/modules/web/`.
  Directory binds would hide files we don't override (e.g. JS we don't
  care about), breaking the UI entirely. Per-file binds are surgical:
  only the files we provide are replaced, everything else stays D-Link's.

## Limits we accept

- We can only override files that *exist* in the D-Link UI. We can't
  inject brand-new pages without adding routing config to lighttpd,
  which is a more invasive change for a later phase.
- We can't change anything that the CGI scripts emit dynamically (e.g.
  inline `<style>` blocks inside CGI HTML output). We can only mask
  this with stronger CSS specificity from our overlay.
- We can't change the OLED display message — that's controlled by a
  separate binary on the device. Out of scope for v0.1.0.
