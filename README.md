# OSS-reCamera-solutions

Official online repository for reCamera: the **线上安装 / Online Install**
solution catalog and the **Software Update** firmware channel — both consumed
by the Supervisor web UI on the device.

## Layout

```
catalog.json                       # solution catalog index (format 1)
packages/                          # riscv64 solution packages, grouped by
  ├── Factory/                     # web UI Solutions category (工厂制造)
  ├── Building/                    # (楼宇管理)
  ├── Medical/                     # (医疗养老)
  ├── Ecology/                     # (生态监测)
  └── Other/                       # (其他)
firmware/                          # firmware channel
  ├── latest.json                  # machine-readable "latest firmware" pointer
  └── README.md                    # firmware publishing rules (GitHub Releases)
```

The `packages/<Category>/` directory mirrors the web UI's Solutions
categories one-to-one. A package goes into the directory matching the
`category` field of its catalog entry (`factory|building|medical|ecology|
other` — the same key the web UI filters by).

## catalog.json format

The top-level object has `format: 1` and an `entries` array. Each entry:

| Field             | Type     | Notes                                                        |
| ----------------- | -------- | ------------------------------------------------------------ |
| `app_id`          | string   | lowercase `[a-z0-9-]`, max 64 — matches the app manifest id  |
| `name`, `name_zh` | string   | display name (EN, optional CN)                               |
| `scene`, `scene_zh` | string | optional category scene labels                               |
| `description`, `description_zh` | string | optional, max 512 chars                   |
| `package_file`    | string   | safe filename `[A-Za-z0-9._-]`, max 128 — basename under `packages/<Category>/` |
| `package_name`    | string   | optional opkg package name (used for installed-version lookup) |
| `package_version` | string   | `[A-Za-z0-9._+-]`, max 64                                    |
| `size`            | number   | exact byte size of the package                               |
| `sha256`          | string   | lowercase hex sha256 of the package                          |
| `urls`            | string[] | 1-8 download URLs, tried in order (mirror fallback)          |
| `category`        | string   | Solutions gallery category (see layout above)                |
| `demo_category`   | string   | optional Demos-page hint                                     |

The device verifies **every** field before caching the index and verifies the
**sha256 + size** of every package before installing.

## Why .deb

Solution packages are Debian-format `ar` archives (CPack DEB generator). The
device's native package manager is **opkg** (no dpkg on the image), which
unpacks exactly this format (`control.tar.gz` + `data.tar.gz`) and provides
install / version lookup / update / uninstall bookkeeping for free — the
Supervisor install pipeline (`opkg install --force-reinstall`, status reads
from `/var/lib/opkg/status`) is built on it. Downloads use the same transport
as the official firmware updater (`wget -T 10 -t 3 --no-check-certificate`),
with the catalog sha256 as the integrity guarantee.

## Publishing a new solution version

1. Build the riscv64 `.deb` package.
2. Copy it into `packages/<Category>/` (the entry's `category`).
3. Compute `sha256sum` and the exact byte size.
4. Update the matching entry (or add a new one) in `catalog.json`, keeping
   `package_file` as the bare file name and the `urls` pointing into the
   category directory.
5. Commit to `main` — devices re-sync on demand.

Each entry lists two URLs (GitHub raw + jsDelivr CDN). For regions where
GitHub is slow, add more mirrors (Gitee release, object-storage CDN, …) to
the `urls` array — no firmware change is needed.

## Firmware channel

See [firmware/README.md](firmware/README.md): images ship as GitHub Release
assets (tag = version), `firmware/latest.json` is the stable machine-readable
pointer, and the web UI updater wires to
`…/OSS-reCamera-solutions/releases/latest`.