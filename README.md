# NetClaw package for Arch Linux

Packaging candidate for the Arch User Repository (AUR). This package has not been published to the AUR. It is maintained separately from Omarchy.

The package installs a pinned NetClaw source snapshot, a `netclaw` command, and a terminal application entry. Installing or upgrading the package does not run NetClaw's setup, request credentials, start services, or modify any user's home directory. The package owns its dependencies; Omarchy needs only an optional Install menu entry once publication and desktop verification are complete.

## Build

On Arch Linux, install `base-devel` and the dependencies listed in `PKGBUILD`, then run as a regular user:

```bash
makepkg --syncdeps
makepkg --printsrcinfo > .SRCINFO
```

Review the recipe and source before installing the resulting package. `makepkg` runs the workspace regression tests and desktop entry validation in `check()`.

## Use

Run `netclaw` or select NetClaw in the application launcher. Run `netclaw install` to choose a runtime, integration profile and credentials. Full integration setup remains a separate, explicit choice. External services and optional components have their own requirements; package build validation does not certify those integrations.

The packaged source is read-only under `/usr/share/netclaw/source`. First launch copies it into `$XDG_DATA_HOME/netclaw`, defaulting to `~/.local/share/netclaw`. An existing unrecognized directory or symlink at that location is preserved and requires manual resolution. Existing source checkouts and OpenClaw/Hermes accounts are not adopted by the packaging launcher. Upstream setup controls any subsequent runtime configuration.

## Updates and removal

After updating the package, stop your NetClaw services and run:

```bash
netclaw --sync-source
netclaw install
```

Source synchronization preserves credentials, generated environments, and untracked files. It refuses to overwrite locally modified files or occupied new source paths. Resolve those conflicts manually before retrying. If a source update is interrupted, private `.netclaw-update-*` recovery directories next to the workspace retain the replaced files. The launcher does not manage running services; stop them before synchronizing, then review dependencies through upstream setup and restart them when appropriate.

Removing the package removes the packaged command, desktop entry and source snapshot. User workspaces, credentials and any services configured through upstream setup remain user-owned and must be managed separately.

## Publishing

Validation on 2026-10-14 used an Arch Linux x86_64 container under emulation on macOS. `makepkg` built `netclaw-1.10.0-1-any.pkg.tar.zst`; all 10 workspace regression tests, Bash syntax checks and desktop entry validation passed. Package installation, wrapper help, upstream help, installer help and component listing passed. The installed source matched its manifest, and package removal preserved the user's workspace. No credentials or real network integrations were used in these checks.

Complete runtime onboarding, live integrations and installation through the published AUR entry remain unverified. The Omarchy proposal stays a draft while those prerequisites are addressed.

The maintainer needs an AUR account and a registered SSH public key. AUR receives the recipe and supporting text files, not the built binary, downloaded source archive, test logs or screenshots. Once authenticated, publish `PKGBUILD`, `.SRCINFO`, `netclaw`, `netclaw.desktop`, `launcher.py`, `test_launcher.py`, and `LICENSE` to `ssh://aur@aur.archlinux.org/netclaw.git`.

Do not mark the Omarchy install entry ready until this package is published and the real install and desktop flow have been verified. There is no migration or default installation in the revised Omarchy proposal.
