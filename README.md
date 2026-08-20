# OSS-reCamera-solutions

Official online catalog and solution packages for reCamera — the source of the
Supervisor web UI's **线上安装 / Online Install** feature.

## Layout

```
catalog.json          # catalog index: format 1
packages/*.deb        # riscv64 solution packages (binaries; models ship separately)
```

## catalog.json format

The top-level object has `format: 1` and an `entries` array. Each entry:

| Field             | Type     | Notes                                                        |
| ----------------- | -------- | ------------------------------------------------------------ |
| `app_id`          | string   | lowercase `[a-z0-9-]`, max 64 — matches the app manifest id  |
| `name`, `name_zh` | string   | display name (EN, optional CN)                               |
| `scene`, `scene_zh` | string | optional category scene labels                               |
| `description`, `description_zh` | string | optional, max 512 chars                   |
| `package_file`    | string   | safe filename `[A-Za-z0-9._-]`, max 128 — name under `packages/` |
| `package_name`    | string   | optional opkg package name (used for installed-version lookup) |
| `package_version` | string   | `[A-Za-z0-9._+-]`, max 64                                    |
| `size`            | number   | exact byte size of the package                               |
| `sha256`          | string   | lowercase hex sha256 of the package                          |
| `urls`            | string[] | 1-8 download URLs, tried in order (mirror fallback)          |
| `category`, `demo_category` | string | optional gallery hints (`[a-z0-9_-]`, max 32)      |

The device verifies **every** field before caching the index and verifies the
**sha256 + size** of every package before installing.

## Publishing a new version

1. Build the riscv64 `.deb` package.
2. Copy it into `packages/` with the version in the file name
   (`<pkg>_<version>_riscv64.deb`).
3. Compute `sha256sum` and the exact byte size.
4. Update the matching entry (or add a new one) in `catalog.json`.
5. Commit to `main` — devices sync on demand.

Each entry lists two URLs (GitHub raw + jsDelivr CDN mirror); for regions where
GitHub is slow, add more mirrors (e.g. a Gitee release or an object-storage
CDN URL) to the `urls` array — no firmware change is needed.