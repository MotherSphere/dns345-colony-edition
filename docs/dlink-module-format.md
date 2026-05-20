# D-Link Add-Ons `.module` format (research notes)

Status: **incomplete**, still being reverse-engineered.

The DNS-3xx ShareCenter web UI has an **Application Management → Add Ons**
page that accepts a single `.module` file via a file picker and an Apply
button. After install, the module appears in a table with columns:
*Module Name*, *Version*, *Signature*, *Status*, *Start/Stop*, *Delete*.

This document is what we've figured out so far about the file format,
gathered by inspecting the CGI endpoints, browsing forum posts about
DSM-G600/DNS-32x add-ons, and looking at known third-party modules
(Transmission, ffp itself when distributed this way, etc.).

## File extension & MIME

The UI accepts `.module` as the extension. Internally it's a **gzipped tar**
(`.tar.gz`), just with a different extension. Sometimes it's a plain `.tgz`.

## Expected internal structure

Based on forum posts about DSM-G600 / DNS-32x add-ons, the canonical layout
inside the tarball is:

```
my-module/
├── name                    # plain text: human display name
├── version                 # plain text: version string
├── description             # plain text: short description shown in UI
├── checksum                # md5 or sha1 of the payload tarball below
├── payload.tar.gz          # the actual files to install
└── scripts/                # lifecycle hooks
    ├── pre-install.sh
    ├── post-install.sh
    ├── pre-uninstall.sh
    ├── post-uninstall.sh
    ├── start.sh
    └── stop.sh
```

The CGI installer (`mod_mgr.cgi` likely) extracts the outer tarball, reads
metadata, runs `pre-install.sh`, extracts `payload.tar.gz` to a target
location (probably `/usr/local/modules/<module-name>/`), runs
`post-install.sh`, and registers the module in some persistent state.

**Caveats:**

- Some firmware variants require **signed** modules. The `Signature`
  column suggests cryptographic signing, possibly via D-Link's CA.
  Whether DNS-345 1.05 enforces this or accepts unsigned modules is
  **unknown** — to be tested empirically.
- Files outside the tarball's top-level dir may be silently dropped.
- The lifecycle script interpreter is busybox `sh`, not bash. Stick to
  POSIX.

## Things to verify before we ship v0.1.0

- [ ] Does DNS-345 1.05 reject unsigned modules? If yes, options are:
      (a) get a community signing key (some hobbyists have published these),
      (b) find an `accept_unsigned=1` config toggle,
      (c) fall back to manual installation (just SMB-copy the unpacked
      tarball to the right path, since we already have telnet/SSH).
- [ ] Exact location where the firmware extracts payloads. Probably
      `/mnt/HD/HD_a2/Nas_Prog/<module-name>/` based on filesystem inspection,
      to be confirmed.
- [ ] How Start/Stop in the UI maps to which script (`start.sh`/`stop.sh`
      or the module-name binary?).
- [ ] Whether `post-install.sh` runs **as root** (we need root to
      mount --bind over /usr/local/modules/web/).

## Empirical research plan

1. Find a known-good module file (Transmission was popular). Extract it
   without installing, examine structure.
2. Build a smallest-possible test module that just creates `/tmp/colony-hello`
   on install. Try to install via UI. See what happens.
3. If signature check fails: probe the validation logic via filesystem
   inspection of the firmware's CGI scripts.

Once empirical info is in, this doc gets updated and the empty
checklist items above get resolved.

## References

- D-Link DSM-G600 forum threads (archived) describing add-on format
- `inreto.de/ffp` historical mentions of `.module` packaging
- nas-tweaks.net "Add-Ons" tutorials for the DNS-32x family
