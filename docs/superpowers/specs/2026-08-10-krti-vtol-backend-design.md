# KRTI VTOL Backend Bridge Design

**Status:** Disetujui pengguna pada 2026-08-10
**Target:** Backend bridge nyata di laptop ground station
**Frontend consumer:** TanStack Start dashboard VTOL
**Hardware link:** Pixhawk melalui MAVLink serial
**Video link:** RTSP/UDP dari perangkat UAV/receiver

## 1. Tujuan

Backend menyediakan bridge lokal yang:

1. membaca telemetry Pixhawk melalui serial MAVLink;
2. menerima stream kamera RTSP/UDP dan menjalankan inference lokal;
3. menyatukan telemetry, vision, mission, payload, safety, link, dan camera menjadi event VTOL;
4. mengirim event realtime ke dashboard melalui WebSocket;
5. menerima command terbatas dari dashboard melalui HTTP;
6. meneruskan command ke Pixhawk hanya setelah safety gate lulus;
7. reconnect otomatis ketika serial atau stream video terputus.

Backend berjalan di laptop ground station. Backend menjadi satu-satunya modul aplikasi yang boleh menulis command MAVLink. RC dan Emergency Stop fisik tetap menjadi jalur keselamatan utama.

## 2. Non-goals

Tahap pertama tidak mencakup:

- database, akun, cloud storage, atau multi-tenant;
- joystick virtual atau kontrol attitude kontinu;
- editor waypoint atau pengganti Mission Planner;
- ELS buatan browser;
- autonomous avoidance berdasarkan person detection;
- penyimpanan frame/video permanen;
- hardcoded nama, site, atau koordinat lokasi kompetisi;
- service inference terpisah atau orkestrasi multi-container.

## 3. Arsitektur

Satu proses FastAPI modular menjalankan adapter dan worker berikut:

```text
Pixhawk receiver -- MAVLink serial --> mavlink_reader ----┐
                                                          v
RTSP/UDP stream --------------------> video_inference -> state_store
                                                          |
                                   +----------------------+----------------+
                                   v                                       v
                            WS /ws/flight                         command safety gate
                                                                            |
                                                                            v
                                                               mavlink_writer -> Pixhawk
```

### Modul

- `mavlink_reader`: membuka serial, membaca pesan, memvalidasi nilai numerik, dan mengubahnya menjadi state/event internal.
- `mavlink_writer`: pemilik tunggal handle serial untuk command. Tidak boleh ada modul lain yang menulis MAVLink.
- `video_ingest`: membuka RTSP/UDP dan menyediakan frame terbaru dengan bounded buffer.
- `inference_worker`: menjalankan model lokal dan menerbitkan geometry detection dalam koordinat ternormalisasi `0..1`.
- `state_store`: menyimpan snapshot terbaru dan sequence counter secara in-memory.
- `event_broadcaster`: mengirim event baru ke semua client WebSocket.
- `command_service`: menerima intent HTTP, memanggil safety gate, menunggu acknowledgment atau timeout, lalu mengembalikan hasil.
- `reconnect_manager`: mengatur lifecycle serial dan video secara terpisah sehingga putusnya video tidak menghentikan telemetry.
- `health_service`: menyajikan status readiness, freshness, dan error terakhir tanpa membuka data sensitif tambahan.

Worker inference tidak boleh memblokir pembacaan MAVLink. Buffer frame dibatasi ke frame terbaru; frame lama dibuang ketika inference tertinggal.

## 4. Kontrak HTTP

### `GET /api/health`

Mengembalikan status operasional:

```json
{
  "status": "ready",
  "serial": { "state": "ready", "port": "COM7", "lastEventAt": 0 },
  "video": { "state": "ready", "lastFrameAt": 0 },
  "inference": { "state": "ready", "model": "model/best.pt" }
}
```

`status` bernilai `ready` hanya jika serial sehat. Video dan inference boleh `degraded` tanpa memutus telemetry.

### `GET /api/snapshot`

Mengembalikan snapshot state yang kompatibel dengan `FlightState` frontend. Nilai yang belum tersedia tetap `null`, bukan nol sintetis.

### `POST /api/commands`

Request:

```json
{ "commandId": "uuid", "type": "arm" }
```

`type` hanya boleh salah satu dari:

- `arm`;
- `enable_autonomy`;
- `pause_mission`;
- `retry`;
- `emergency_land`.

Response:

```json
{ "commandId": "uuid", "status": "accepted" }
```

atau:

```json
{ "commandId": "uuid", "status": "rejected", "reason": "Serial link is not ready" }
```

Timeout menghasilkan `unknown`, bukan `accepted`. Request dengan `commandId` yang sudah pernah diproses tidak boleh mengeksekusi command kedua.

## 5. Kontrak WebSocket

Endpoint: `WS /ws/flight`.

Saat client tersambung, backend mengirim snapshot event yang diperlukan untuk menghidrasi UI, lalu mengirim event incremental. Event tidak dibungkus format kedua agar langsung cocok dengan `FlightEvent` frontend.

Semua event memiliki:

```ts
{ type: string; seq: number; timestampMs: number }
```

Event yang digunakan:

- `telemetry` — mode, armed, battery, GPS, local position, altitude, rangefinder, speed, heading, attitude, clearance;
- `vision` — kamera, class, confidence, box/path normalized, frame id;
- `mission` — phase, waypoint, status, score, timer, retry checkpoint, autonomy readiness;
- `payload` — secured, armed, released, atau unknown;
- `safety` — link-loss seconds, ELS state, person warning, obstacle warning;
- `map` — availability base map bila diketahui;
- `camera` — camera id, connection, FPS, latency;
- `link` — connected, stale, atau disconnected;
- `trim_vision` — instruksi membatasi target vision terbaru.

### Pemetaan MAVLink minimum

- `HEARTBEAT`: mode, armed, heartbeat freshness, link state;
- `GLOBAL_POSITION_INT` dan `GPS_RAW_INT`: latitude, longitude, altitude, GPS fix, satellites, HDOP bila tersedia;
- `ATTITUDE`: roll, pitch, yaw;
- `SYS_STATUS`: battery percent dan voltage;
- `DISTANCE_SENSOR`: rangefinder;
- `VFR_HUD`: ground speed dan heading.

Pesan yang tidak tersedia tidak diisi dengan nilai default yang menyesatkan. Backend mengirim `null` dan frontend menampilkan `NO DATA`.

## 6. Video dan inference

Default artifact is `model/best.pt`; format lain tidak diperlukan untuk desain tahap pertama.

Setiap hasil inference minimal memiliki:

- `frameId`;
- `camera`;
- `className`;
- `confidence`;
- `box` atau `path`;
- timestamp sumber.

Box/path dinormalisasi ke `0..1` sebelum dipublish. Metadata dari frame yang sudah terlambat dibuang dan tidak boleh ditempelkan ke frame terbaru. Person detection hanya menghasilkan warning pasif; tidak boleh memicu command penerbangan otomatis.

## 7. State dan reconnect

Serial dan video memiliki state machine terpisah:

```text
DISCONNECTED -> CONNECTING -> READY -> STALE
       ^             |          |        |
       +-------------+----------+--------+
                    reconnect
```

Aturan reconnect:

- backoff: 1, 2, 4, 8 detik, lalu maksimum 30 detik;
- reconnect serial tidak menghentikan worker video;
- reconnect video tidak mengubah telemetry serial menjadi disconnected;
- frame terakhir boleh ditampilkan sebagai frame beku, tetapi tidak ditandai live;
- command hanya boleh diteruskan saat serial `READY` dan heartbeat masih fresh;
- state terakhir dan error terakhir tersedia di `/api/health`.

Tidak ada persistence database. Log structured dikirim ke stdout dan state debug dibatasi ring buffer in-memory.

## 8. Safety gate dan command

Safety gate memeriksa:

1. command termasuk allowlist;
2. `commandId` belum pernah diproses;
3. serial state `READY`;
4. heartbeat tidak stale;
5. state misi memenuhi precondition command;
6. command tidak sedang berjalan bersamaan dengan command penerbangan lain;
7. link dan safety state tidak melarang command.

ARM tetap membutuhkan hold-to-confirm 1,5 detik di frontend, kemudian backend melakukan pre-arm validation sendiri. Enable autonomy hanya diterima jika backend menyatakan transisi WP1 siap. Retry selalu menyertakan checkpoint dari state backend. Emergency land memiliki prioritas tampilan tertinggi, tetapi tidak diklaim berhasil ketika serial terputus.

Backend tidak melakukan auto-retry command penerbangan. Jika acknowledgment tidak tiba sebelum timeout, status menjadi `unknown` dan operator diarahkan memeriksa RC/Pixhawk.

ELS dan payload release berasal dari Pixhawk atau safety logic backend yang berwenang. Browser hanya menampilkan event dan tidak memicu keduanya secara otomatis.

## 9. Konfigurasi

Konfigurasi melalui environment:

- `PIXHAWK_SERIAL` — COM port atau device path;
- `PIXHAWK_BAUD` — baud rate serial;
- `VIDEO_URL` — URL RTSP/UDP;
- `MODEL_PATH` — path artifact model, default `model/best.pt`;
- `INFERENCE_CONF` — threshold confidence;
- `MAX_FPS` — batas inference;
- `SERIAL_RECONNECT_MAX_SECONDS` — batas backoff;
- `COMMAND_TIMEOUT_SECONDS` — batas acknowledgment;
- `CORS_ORIGINS` — origin dashboard yang diizinkan.

Default hanya boleh cocok untuk laptop lokal. Origin wildcard dan bind publik tidak digunakan sebagai default.

## 10. Testing dan acceptance

### Unit

- parsing MAVLink ke telemetry dengan nilai valid dan `null`;
- heartbeat freshness dan transisi link;
- safety gate untuk setiap command dan precondition;
- duplicate command idempotency;
- timeout menghasilkan `unknown`;
- normalisasi box/path inference;
- reconnect backoff tanpa busy loop.

### Integration

- FastAPI `GET /api/health` dan `GET /api/snapshot`;
- WebSocket menerima initial events dan incremental events;
- `POST /api/commands` mengirim ke fake serial hanya setelah gate lulus;
- fake serial disconnect/reconnect;
- fake RTSP frame dan inference result;
- telemetry tetap berjalan ketika video worker gagal.

### Smoke hardware

Dengan COM port Pixhawk dan URL RTSP nyata:

1. health berubah menjadi ready;
2. dashboard menerima telemetry aktual;
3. disconnect serial menghasilkan stale/disconnected dan reconnect;
4. disconnect video tidak memutus telemetry;
5. command valid mendapat acknowledgment atau `unknown` secara jujur;
6. command ditolak ketika link belum ready.

Sukses backend berarti seluruh unit/integration test pass, dashboard dapat menghidrasi dari snapshot dan WebSocket, dan smoke hardware tidak mengirim command saat link tidak sehat.
