<p align="center">English | <a href="README.zh-CN.md">简体中文</a></p>

# Package Monitor (包裹监控)

A parcel / express-delivery tracking app in two editions sharing one API provider system:

- **Windows Desktop** (repo root, Python + PySide6): periodic auto-refresh, **system-tray notifications** on new tracking events;
- **Android** (`/flutter_app`, Flutter): on-the-go tracking with a Material You dark theme.

Both editions are ad-free and keep all data on your device.

---

# Android Edition (Flutter)

Track courier shipments on your phone: add a tracking number, query the logistics timeline on demand, auto-refresh on a schedule — latest status always on top. Details open as a fixed half-screen bottom sheet; foldables (Flip / Fold) adapt to the screen height.

| Welcome | Home | Half-screen details | Add shipment |
| --- | --- | --- | --- |
| ![welcome](flutter_app/screenshots/welcome.png) | ![home](flutter_app/screenshots/home.png) | ![detail](flutter_app/screenshots/detail.png) | ![add](flutter_app/screenshots/add.png) |

## Download APK

A prebuilt APK ships in the repo root: [`包裹监控.apk`](包裹监控.apk) (~21 MB, **contains no personal credentials** — enter your own API credentials on first launch).

## Features (Android)

- **Data providers (choose one on the welcome screen)**: Kuaidi100 API (recommended) / KDNiao API / Demo mode (offline);
- **Parcel cards**: courier badge, masked tracking number, status tag (In transit / Out for delivery / Delivered), latest event & time — **timeline always newest-first**;
- **Half-screen detail sheet**: slides up from the bottom with the full timeline (h = 1/2 screen height), newest node highlighted; foldables adapt automatically;
- **Add shipments**: the "＋" FAB opens a sheet with tracking-number input and courier chips (SF / YTO / ZTO / STO / YUNDA / JD / EMS / J&T / Other); optional phone-tail digits (required by some couriers, e.g. SF);
- **Auto refresh**: checks every 30 s and refreshes in the background once the configured interval (default 5 min) is reached; pull-to-refresh resets the timer; Do-not-disturb toggle in Settings;
- **Robustness**: falls back to IP + Host header when DNS fails (emulators); shows cached data on query failure instead of crashing; reuses results within 30 min per tracking number (avoids provider rate-locking).

## Build from source (Android)

Requires Flutter 3.24.x (Dart 3.5.x) and Android SDK 34:

```bash
cd flutter_app
flutter config --android-sdk <path-to-your-sdk>   # prevents local.properties from being overwritten
flutter pub get
flutter build apk --release
# Output: build/app/outputs/flutter-apk/app-release.apk
```

## Usage (Android)

1. Install the APK and pick a data provider on first launch;
2. For Kuaidi100, enter your auth key + customer (the repo and APK contain **no default credentials**); or try Demo mode first;
3. Tap "＋" to add a tracking number → pick the courier → add & query;
4. Shipments auto-refresh every 5 minutes (adjustable in Settings); pull down for an instant refresh.

## Project structure (Android)

```
flutter_app/lib/
├── main.dart               # Entry point, AppState, routing
├── models.dart             # Package / TraceNode (newest-first timeline)
├── constants.dart          # Courier table, demo data
├── theme.dart              # Material You dark theme
├── services/
│   ├── kuaidi100_api.dart  # Kuaidi100 realtime query (MD5 sign + IP fallback)
│   ├── kdniao_api.dart     # KDNiao instant query (DataSign + IP fallback)
│   └── config_store.dart   # SharedPreferences (per-provider credential slots)
└── screens/
    ├── welcome_screen.dart # Welcome screen (provider picker)
    ├── home_screen.dart    # Home cards + auto-refresh timer
    ├── detail_sheet.dart   # Half-screen detail timeline
    ├── add_sheet.dart      # Add-shipment sheet
    └── settings_screen.dart# Settings
```

---

# Windows Desktop Edition (Python + PySide6)

Query courier logistics by tracking number through **API providers**, refresh automatically on a schedule, and get **system-tray notifications** when something new happens. Ad-free; all data stays on your machine.

## Features (Desktop)

- **Data providers (choose one on the login window)**
  1. **Cainiao account**: phone-number SMS authorization (legacy web API, may break at any time);
  2. **KDNiao API**: EBusinessID + AppKey, per-number instant query;
  3. **Kuaidi100 API** (recommended): customer (enterprise ID) + key (auth key) via the official realtime query endpoint (poll.kuaidi100.com); falls back to a free public query when no key is set;
  4. **Demo mode**: built-in sample parcels, fully offline.
- **Parcel card grid**: staggered brick layout that adapts to window width (3 cards per row on wide windows); each card shows the courier badge, masked tracking number, latest status and time.
- **Parcel details**: click a card for the full timeline (newest first).
- **Add shipments**: "＋" on the main window — paste a number, pick the courier; a saved phone tail is used automatically for queries that need it (e.g. SF).
- **Auto refresh**: background refresh every 5 minutes by default, tray notification on changes; **Do-not-disturb** mode available in Settings.
- **Settings (slide-in drawer)**: data-source notes / logs / API provider / refresh interval / DND / appearance / account.
- **Appearance**: dark / light / follow-system, 8 built-in color schemes driven by theme tokens (background, cards, top bar, accents).
- **Robustness**: single instance, keeps running in the tray on close, shows cached data on network errors instead of crashing.

## Provider comparison

| Source | Purpose | Notes |
|---|---|---|
| Cainiao account (legacy) | Account-level parcel list | Depends on legacy Taobao web API; may be unavailable; supplementary only |
| KDNiao API | Per-number query | api.kdniao.com instant query; pay-per-use |
| Kuaidi100 API | Per-number query | poll.kuaidi100.com realtime query; credentials from the console (customer = enterprise ID, key = auth key); official signing |
| Demo mode | Offline demo | Built-in sample parcels, no network |

> Kuaidi100 credentials: sign in at <https://api.kuaidi100.com/> → console shows the enterprise ID (customer) and auth key.
> Official realtime-query docs: <https://api.kuaidi100.com/document/5f0ffb5ebc8da837cbd8aefc.html>

## Repository layout (desktop part)

```
cainiao-monitor/
├── main.py                     # Program entry
├── requirements.txt            # Runtime dependencies
├── requirements-dev.txt        # Packaging dependencies
├── build_full.bat / build_lite.bat          # One-click packaging (full / lite)
├── build_full_onefile.bat / build_lite_onefile.bat  # Optional single-file packaging
├── cainiao_monitor_full_onedir.spec  # Full edition, onedir (default)
├── cainiao_monitor_lite_onedir.spec  # Lite edition, onedir (default)
├── cainiao_monitor_full.spec / cainiao_monitor_lite.spec  # Single-file specs (optional)
├── README.md                   # This file
├── 使用说明.md                  # Full user manual (Chinese)
├── create_project.py           # One-click source re-creation (self-extracting script)
├── tools/
│   └── gen_icon.py             # Generates the app icon (icon.ico)
├── resources/                  # Icons and other assets
├── app/
│   ├── config.py               # Config store (provider keys / settings / cache, JSON)
│   ├── constants.py            # Courier table, color schemes, API constants
│   ├── models.py               # Data models (parcel / timeline node)
│   ├── logger.py               # Logging
│   ├── api/
│   │   ├── http_client.py      # Shared session / timeout / retry / errors
│   │   ├── wuliu.py            # Taobao logistics helper: list & detail scraping
│   │   ├── kdniao.py           # KDNiao API query
│   │   └── kuaidi100.py        # Kuaidi100 query
│   ├── core/
│   │   ├── monitor.py          # Background monitor thread (polling + change detection)
│   │   ├── notifier.py         # System tray & notifications
│   │   └── workers.py          # Threading helpers
│   └── ui/
│       ├── theme.py            # Theme token system (dark/light + color schemes)
│       ├── icons.py            # Programmatic icons (tray / badges / status dots)
│       ├── login_window.py     # Login window (provider selection / credentials)
│       ├── main_window.py      # Main window (card grid + tray + settings drawer)
│       ├── package_card.py     # Parcel card widget
│       ├── detail_dialog.py    # Detail dialog (timeline)
│       ├── add_package_dialog.py # Add-shipment dialog
│       └── staggered_layout.py # Staggered brick layout
└── tests/
    ├── test_core.py            # Core logic tests (offline-capable)
    └── test_ui_smoke.py        # UI smoke tests (offscreen screenshots)
```

## Run (dev mode, desktop)

Requires Python 3.10+:

```bat
pip install -r requirements.txt
python main.py --simulate   # demo mode, no account needed
python main.py              # pick a provider on the login window
```

## Build a standalone .exe (desktop)

The default is the "onedir" build (zero unpacking at runtime, avoids MSVCP140 extraction errors):

```bat
pip install -r requirements-dev.txt
python tools\gen_icon.py
pyinstaller --clean --noconfirm --distpath dist_lite --workpath build_lite cainiao_monitor_lite_onedir.spec
```

Output lands in `dist_lite\CainiaoMonitorLite\`: launch the exe or `启动菜鸟监控.cmd`.

- **Full edition** (embedded browser for Cainiao web login): `build_full.bat` / `cainiao_monitor_full_onedir.spec`
- **Lite edition** (no embedded browser, smaller): `build_lite.bat` — login via "system browser + paste Cookie"
- Antivirus tools occasionally flag PyInstaller binaries; add a trust rule if that happens.

## Usage (recommended: Kuaidi100, desktop)

1. Launch the app → pick **Kuaidi100 API** on the login window;
2. Enter customer (enterprise ID) and key (auth key), or tick the free public query;
3. On the main window → "＋" paste a tracking number, pick the courier → add;
4. The app auto-refreshes every 5 minutes and notifies via tray on changes.

> The Cainiao account (phone authorization) depends on a legacy web API and is supplementary only; KDNiao / Kuaidi100 per-number queries are the most reliable.

## Data & local privacy (desktop)

- All sign-in data (cookies, phone number, API keys) stays in `%APPDATA%\CainiaoMonitor\` on your machine — nothing is uploaded;
- **Before sharing, clear personal info**: app Settings → "Clear my info", or delete the `%APPDATA%\CainiaoMonitor` folder manually;
- Personal project, not affiliated with Alibaba / Cainiao / Kuaidi100 / KDNiao or any other company; APIs may change at any time; use at your own risk.

---

# API Application Guide (Kuaidi100 / KDNiao)

> Applies to both editions. Both services query by tracking number; the free tier is enough for personal use, paid tiers for heavy usage.
> Credentials are stored locally only — enter them in the provider settings of whichever edition you use (desktop login window / Android welcome screen).

## Kuaidi100 (recommended)

1. Sign up and log in at **<https://api.kuaidi100.com/>** (phone number is enough);
2. Complete **identity verification** (personal verification works, usually instant);
3. In the console, activate the "**Realtime Express Query**" service (free trial quota included);
4. Under "Console → Account info / Keys", grab the two credentials:
   - **customer** (enterprise ID / auth code)
   - **key** (auth key)
5. Pick "**Kuaidi100**" on the desktop login window / Android welcome screen and enter customer + key.

- Official realtime-query docs: <https://api.kuaidi100.com/document/5f0ffb5ebc8da837cbd8aefc.html>
- Desktop only: with no key set, the app falls back to a "free public query" (some couriers need the phone tail).

## KDNiao

1. Sign up and log in at **<https://www.kdniao.com/>**;
2. Complete identity verification under "User Center → Real-name Verification" (free);
3. Under "Service Center", activate the "**Logistics Tracking (instant query)**" API (free tier has a daily query cap);
4. Under "User Center → My Info / Key Management", grab the two credentials:
   - **EBusinessID** (user ID)
   - **AppKey** (secret)
5. Pick "**KDNiao**" on the desktop login window / Android welcome screen and enter EBusinessID + AppKey.

- Note: once the free quota is used up, queries report a quota error (resets daily, or upgrade to paid) — switch to Kuaidi100 in that case.
