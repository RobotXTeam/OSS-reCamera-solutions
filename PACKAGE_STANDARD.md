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
port 8001 and publish H.264 frames. UDP is an optional additional output and
never replaces the WebSocket preview contract.

### Full Studio integration contract (mandatory)

Every published solution must reuse **all** of Studio, not just the preview.
The release gate (`tools/validate_catalog.py`) rejects a package missing any of
these; the real-device gate (`tools/device_stream_test.py`) verifies them live:

1. **RTSP external output** — the manifest declares `rtsp_url` with a `{host}`
   placeholder, and the binary actually serves the encoded stream on
   `rtsp://<ip>:8554/live` (plus `live1` when a sub stream exists).
2. **RGN result overlay** — the manifest sets `"result_overlay": true` and the
   binary links the `result_overlay` component, which burns the boxes into the
   encoded RTSP stream through a VPSS overlay region. The Studio console toggle
   (`/userdata/local/result_overlay.conf`) gates it live without a restart.
3. **MQTT result output + Home Assistant** — the manifest declares `mqtt_topic`
   and the binary links the `ha_mqtt`/`studio_mqtt` publisher. Results JSON is
   published to the topic; when `/userdata/local/ha.conf` enables Home
   Assistant, the same client runs MQTT discovery so results surface as HA
   sensors automatically.
4. **Inference/connection settings** — the manifest declares `config_schema`
   (see below) and `run.sh` consumes `/userdata/local/apps/<app-id>.config.json`
   so every declared control actually changes runtime behavior.

These are verified in two layers:

- Static (CI + pre-publish): `tools/validate_catalog.py` checks the manifest
  fields and that the binary contains `debug_stream`, `result_overlay`, and
  `ha_mqtt`/`studio_mqtt` symbols.
- Live (pre-release, on hardware): `tools/device_stream_test.py` checks the
  main H.264 route, the `/results` JSON envelope (timestamp/frame_id/resolution/
  boxes), the `/sub` H.264 route, and that the RTSP listener answers. It runs
  for every transition target inside `tools/device_transition_matrix.py`.

Legacy outputs remain available but are no longer the point: UDP may still be
offered, and ONVIF may be added on top, but a solution is only releasable when
the four contract items above all pass.

## Camera ownership and handoff contract

Camera ownership belongs to Supervisor, not to an individual solution. Every
transition (solution to solution, solution to live preview, and live preview to
solution) is one serialized transaction: stop the current owner, verify that
`/dev/cvi-vpss` is free, start the target, verify one owner plus a ready H.264
listener on port 8001, and roll back to the previous owner if startup fails.

A solution must therefore follow these lifecycle rules:

- Its init script controls only its own exact process and never starts, stops or
  kills another solution.
- `start` returns success only after the process has been launched reliably.
- `stop` first sends `TERM` to the PID it owns, waits for bounded graceful
  cleanup, and removes stale PID/readiness files. Do not use `killall` or broad
  `pkill` cleanup.
- The process must release all camera/VPSS resources when it receives `TERM`.
- `status` must distinguish a live owned process from a stale PID file.

Supervisor remains the final recovery authority and may terminate the actual
process holding `/dev/cvi-vpss` if a broken solution exceeds the release
deadline. This recovery is a safety net, not a substitute for correct cleanup.

The device transition test automatically discovers every executable
`/etc/init.d/K92*` application. Adding a new package therefore adds it to the
full ordered-pair test without maintaining a hard-coded application list.

## Developer-defined configuration

Configuration is optional and belongs to the solution author. Declare it in
the manifest as `config_schema`; Studio automatically renders the same controls
on the solution **Configuration** page and the live debugging page. No
solution-specific frontend code is required.

```json
"config_schema": {
  "groups": [{
    "key": "detection",
    "scope": "application",
    "title": "Detection",
    "title_zh": "检测",
    "items": [{
      "key": "confidence",
      "type": "number",
      "title": "Confidence threshold",
      "title_zh": "置信度阈值",
      "description": "Ignore detections below this value.",
      "description_zh": "忽略低于此数值的检测结果。",
      "min": 0,
      "max": 100,
      "step": 1,
      "unit": "%",
      "default": 50
    }]
  }]
}
```

Each group or individual item may declare `scope`:

- `"application"` — inference and application behavior such as confidence,
  thresholds, regions and model parameters.
- `"connection"` — transport and destination settings such as MQTT, RTSP,
  broker host/port, topic, URL or endpoint.

An item-level scope overrides its group. When omitted, Studio automatically
classifies common connection keys (`mqtt_*`, `rtsp_*`, `*_host`, `*_port`,
`*_topic`, `*_url`, and similar); all remaining items are application
parameters. Empty sections are not displayed.

Supported item types are `number`, `boolean`, `enum`, `string`, `zone` and
`line`. A 0–100 `number` is rendered as a percentage slider with a synchronized
numeric input. One declared item produces one control; no items produce no
configuration panel.

Studio reads and writes configuration through:

- `GET /api/appMgr/getConfig?app_id=<app-id>`
- `POST /api/appMgr/setConfig` with
  `{"app_id":"<app-id>","values":{"confidence":75}}`

The Supervisor validates the schema, writes the flat values object to
`/userdata/local/apps/<app-id>.config.json`, and restarts an active solution.
The solution must read that file and prove on the real device that every value
actually changes its runtime behavior. A control that only saves in the UI but
is ignored by the application fails the release gate.

## Required release gate

1. Build from a clean output directory. Never package a stale file from an
   `upload/` or previous build directory.
2. Build the `.deb` with gzip:

   ```sh
   dpkg-deb -Zgzip -z9 --root-owner-group -b <package-root> <output.deb>
   ```

   `--root-owner-group` is mandatory. Studio rejects non-root-owned init
   scripts, so a package whose payload records the developer's local UID/GID
   will appear as “runtime files incomplete” even when every path exists.

3. Update `catalog.json` size and SHA256.
4. Run the complete static gate:

   ```sh
   ./tools/prepublish.sh
   ```

5. Install the exact generated package on a real reCamera. The device gate
   refuses to run if `<app-id>` is not installed, then tests every ordered
   switch between every installed solution and live preview. Every target must
   expose a stable H.264 stream. With `N` camera owners it executes
   `N × (N - 1)` transitions and restores the original owner:

   ```sh
   ./tools/prepublish.sh 192.168.2.102 <app-id>
   ```

6. Only publish when the report ends with `failed=0`. A new application is not
   eligible for upload if any existing-to-new, new-to-existing, or live-preview
   transition fails. GitHub Actions repeats the static gate on every pull
   request and push; the hardware matrix remains a mandatory pre-release gate.

7. For every declared configuration item, save a non-default value and verify
   it reaches the process or changes observable output. Stop the solution and
   start the next one without rebooting to prove camera resources are released.

Static inspection catches stale binaries, malformed configuration schemas,
missing manifests, incompatible compression, bad hashes and absent WebSocket
support. The real-device test is still mandatory because only hardware can
prove camera ownership, model loading, configuration consumption, cleanup and
stable live H.264 output.
