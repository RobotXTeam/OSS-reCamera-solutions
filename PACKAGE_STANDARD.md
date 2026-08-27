# reCamera Studio solution package standard

Every solution shown by the online catalog must work after installation in the
reCamera Studio WebUI. A successful build or a working UDP receiver is not
enough.

## Required runtime contract

- Package format: riscv64 `.deb` containing `control.tar.gz` and `data.tar.gz`.
  The device `opkg` cannot extract zstd members.
- Application manifest:
  `/usr/share/supervisor/apps/<app-id>.json`.
- Executable: `/usr/local/bin/<app-id>`.
- Init script: executable `/etc/init.d/K92<app-id>` supporting
  `start`, `stop`, `restart` and `status`.
- Card artwork: manifest path `/appimg/<file>`, packaged under
  `/userdata/local/apps/img/<file>`.
- Every manifest path in `required_files` must be present in the package.
- Studio preview is H.264 over WebSocket and is mandatory:

```json
"debug_ws": {
  "port": 8001,
  "video_path": "/",
  "results_path": "/results"
}
```

The application must actually start the repository `debug_stream` component on
port 8001 and publish H.264 frames. UDP, MQTT, RTSP and ONVIF are optional
additional outputs; none of them replaces the WebSocket preview contract.

## Required release gate

1. Build from a clean output directory. Never package a stale file from an
   `upload/` or previous build directory.
2. Build the `.deb` with gzip:

   ```sh
   dpkg-deb -Zgzip -z9 --root-owner-group -b <package-root> <output.deb>
   ```

3. Update `catalog.json` size and SHA256.
4. Run the complete static gate:

   ```sh
   ./tools/prepublish.sh
   ```

5. Install the exact generated package on a real reCamera, start it from
   Studio, then verify that a real H.264 frame reaches the WebUI endpoint:

   ```sh
   ./tools/prepublish.sh 192.168.2.102 <app-id>
   ```

6. Only publish after both commands pass. GitHub Actions repeats the static
   gate on every pull request and push.

Static inspection catches stale binaries, missing manifests, incompatible
compression, bad hashes and absent WebSocket support. The real-device smoke
test is still mandatory because only hardware can prove camera ownership,
model loading and live H.264 output.
