# Firmware channel

The web UI's **Update / Software Update** pulls system firmware from this
repository. Layout and rules:

## Publishing a firmware release

1. Build the release image (`sg2002_recamera_emmc_<version>.zip` or per release
   engineering).
2. Create a GitHub Release on this repository with tag `v<version>`
   (e.g. `v1.2.3`) and attach the image as a **release asset**. Release title
   should carry the firmware version.
3. Compute the asset's sha256 + byte size and fill in `firmware/latest.json`
   (stable URL:
   `https://raw.githubusercontent.com/RobotXTeam/OSS-reCamera-solutions/main/firmware/latest.json`).
4. Commit. `latest.json` is the machine-readable "what is the latest firmware"
   pointer; the release assets are the actual payloads.

## Why Releases + latest.json

The device updater (`upgrade.sh` in the supervisor scripts) is built around
GitHub Releases: it follows
`https://github.com/<org>/<repo>/releases/latest` redirects with
`curl -skLi … | grep -i '^location:'` and downloads with
`wget --no-check-certificate`, verifying integrity with a checksum file.
Pointing the device's `DEFAULT_UPGRADE_URL` at this repository
(`https://github.com/RobotXTeam/OSS-reCamera-solutions/releases/latest`) is
the intended wiring; the legacy "Self channel" layout (`url.txt` +
`md5sum.txt`) is only used for private/custom update servers and is not
mirrored here.

## latest.json fields

| Field           | Type   | Notes                                                        |
| --------------- | ------ | ------------------------------------------------------------ |
| `format`        | number | must be 1                                                    |
| `osName`        | string | OS/product name shown in the UI                              |
| `platform`      | string | board identifier (e.g. `sg2002_recamera_emmc`)               |
| `version`       | string | firmware version (e.g. `1.2.3`)                              |
| `filename`      | string | release asset file name                                      |
| `download_url`  | string | direct HTTPS URL of the release asset                        |
| `sha256`        | string | lowercase hex sha256 of the asset                            |
| `size`          | number | exact byte size                                              |
| `notes`         | string | short release notes line                                     |
| `published_at`  | string | ISO-8601 publish time                                        |