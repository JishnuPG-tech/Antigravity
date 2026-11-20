<div align="center">

  <p>
    <b>English</b> &nbsp;&bull;&nbsp; <a href="README.ru.md">Русский</a>
  </p>

  <br/>

  <img src="docs/assets/logo.png" alt="Antigravity" width="88" height="88" style="border-radius: 20px;" />

  # Antigravity for Android

  **Autonomous AI development environment running natively on Android & ARM64.**

  [![Android](https://img.shields.io/badge/Android-7.0%2B-3DDC84?style=flat-square&logo=android&logoColor=white)](https://android.com)
  [![Arch](https://img.shields.io/badge/ARM64-v8.0--A%2B-blue?style=flat-square)](https://arm.com)
  [![Release](https://img.shields.io/badge/Version-2.4.1-blueviolet?style=flat-square)](https://github.com/werdio325-png/antigravity-android/releases)
  [![License](https://img.shields.io/badge/License-Apache_2.0-orange?style=flat-square)](LICENSE)

  <br/>

  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/assets/hero_dark.png">
    <source media="(prefers-color-scheme: light)" srcset="docs/assets/hero_light.png">
    <img alt="Antigravity Interface" src="docs/assets/hero_dark.png" width="100%" style="border-radius: 12px; border: 1px solid rgba(128,128,128,0.2);" />
  </picture>

</div>

---

### Overview

**Antigravity for Android** brings autonomous agentic coding directly to mobile hardware.

No PRoot, chroot, or virtualization overhead. Antigravity runs **bare-metal inside native Android userspace (Bionic)**, unleashing the full read/write speed of UFS storage and physical CPU cores. Driven by Gemini models, the agent inspects repositories, authors code across multiple files, compiles binaries, and runs tests completely on-device.

---


---

## Hybrid Cloud & Edge Architecture (Upgrades in this Fork)

> **Base Project Attribution:** This project is built upon the foundational native Android runtime created by [werdio325-png/antigravity-android](https://github.com/werdio325-png/antigravity-android).
>
> Rather than rebuilding an IDE from scratch, the primary focus of this fork is **feature enhancement and hardware limitation removal**: overcoming the physical ceilings of mobile devices (thermal throttling, high RAM consumption during builds, battery drain, and storage saturation) by turning the mobile app into a hybrid edge-to-cloud development powerhouse.

### Key Upgrades & Features Added

#### 1. Heuristic Cloud Auto-Delegation (ExecHandler.java & runner.py)
Heavy compilation, packaging, and testing commands are automatically intercepted and offloaded from the phone to a 16-vCPU cloud container (agy_cloud.py):
- **Auto-Routed Commands:** cargo, rustc, go build, npm, npx, pnpm, pip, pytest, cmake, make, gcc, docker.
- **Zero Thermal Throttling:** The phone remains cool and battery-efficient while high-core cloud servers handle the heavy lifting.
- **Automatic Fallback:** If disconnected from the cloud, tasks safely fall back to local device execution.

#### 2. WebView Virtual Path Mapping (web/patch_main.py)
Injected a bidirectional virtual path abstraction layer directly into the core editor bundle:
- Clean Aliasing: Maps verbose internal storage paths into clean virtual mount aliases:
  - file:///GoogleDrive/ <-> /data/user/0/com.agy/files/GoogleDrive
  - file:///local/downloads/ <-> /storage/emulated/0/Download
  - file:///local/documents/ <-> /storage/emulated/0/Documents
- Real-Time Directory Sync: New folders and files created in the editor trigger real-time directory synchronization with cloud Google Drive.

#### 3. Shizuku Elevated Hardware Bridge (rish)
Preserves native on-device hardware capabilities through Shizuku IPC (uid=2000):
- Direct APK installation and uninstallation (pm install -r)
- Real-time logcat stream capture and crash diagnostics
- Hardware property queries and battery status monitoring without requiring root.

#### 4. Persistent Cloud Storage & Google Drive Integration
- Cloud workspace (/data/antigravity) automatically syncs bidirectionally with Google Drive.
- Heavy build caches (node_modules, target, .venv) remain exclusively in the cloud container to preserve phone storage.

---

## Cloud Runner Configuration & Setup

The cloud runner is hosted on a high-performance 16-vCPU container running FastAPI and Nginx.

### Environment Variables
Configure the following in your environment:

```env
AGY_CLOUD_URL=https://jishnupg-hermes.hf.space/antigravity
AGY_CLOUD_TOKEN=your_secure_auth_token
AGY_CLOUD_AUTO=1
```

### Manual Cloud CLI Usage
```bash
# Execute any command directly on the 16-vCPU cloud runner:
agy-cloud exec "cargo build --release"
agy-cloud exec "npm install"

# Check cloud status and health:
agy-cloud status
```

---

### Highlights in v2.4

* **Modular Core:** Clean separation into 6 standalone subsystems (`modules/*`) with independent test suites.
* **Native Splash:** Canvas-based dot animation saving ~40 MB RAM with instant startup.
* **Desktop Mode:** Instant toggle in Appearance settings for tablets, external keyboards, and Samsung DeX.
* **Universal ARMv8.0-A Support:** Built-in transparent atomic & SIMD emulation (`liblse_compat.so`) for older CPUs.
* **Background Micro-Daemon:** Ultra-lightweight `agy-daemon` (<10 MB RAM) with cron scheduler, file watcher, and AI task queue.

---

### Key Features

* **Autonomous Agent:** Plans tasks, edits code across project trees, executes shell tools, and fixes build errors.
* **Elevated Control (Shizuku):** Direct ADB-level operations (`uid=2000`) without root for package installs and system diagnostics.
* **Built-in `pkg` Manager:** Fast package manager installing development runtimes (`git`, `python`, `node`, `clang`) from Termux repos.
* **Adaptive Viewports:** Seamless touch-first mobile UI with optional desktop layout.
* **In-Place Upgrades:** Consistent keystore guarantees updating APKs without losing sessions or workspace data.

---

### Quick Start

1. **Download APK** from [Releases](https://github.com/werdio325-png/antigravity-android/releases):
   * `antigravity.apk` — standard release (original Google account checks).
   * `antigravity-region-bypass.apk` — release with account eligibility check bypass.
2. **Grant Storage Permission** (`All Files Access`). *(Optional: enable Shizuku for ADB access)*.
3. **Install Runtimes** via terminal or agent:
   ```bash
   pkg update && pkg install git python nodejs
   ```

---

### Building & Testing

```bash
# Build standard release APK (dist/antigravity.apk):
bash build.sh

# Build release APK with region bypass (dist/antigravity-region-bypass.apk):
bash build.sh --region-bypass

# Run all test suites:
bash test_all_modules.sh
```

---

### Repository Structure

```text
antigravity/
├── config/             # App constants, environment paths, and AI rules
├── modules/            # Decoupled core modules (v2.4+)
│   ├── core/           # Binary unpacking, glibc loader, shims, SHA-256 manifest
│   ├── patches/        # Binary patch engine (syscall emulation, resolv, SIGILL)
│   ├── io/             # High-performance I/O Bus: event broker, FIFO pipes, sockets
│   ├── env/            # Path resolver, diagnostics, Flight Recorder logs, CLI
│   ├── builder/        # Gradle-free APK builder (javac, D8, aapt, zipalign, apksigner)
│   └── runner/         # Standalone runtime preparation, port probe, E2E tests
├── app/                # Android host app (native splash, WebView, system bridges)
├── web/                # Local web frontend, desktop mode toggle, themes
├── env/                # Bionic userspace, Termux overlay, pkg manager, liblse_compat
├── docs/assets/        # Screenshots, banners, and diagrams
├── build.sh            # Root APK build script
└── test_all_modules.sh # Test suite for all 6 modules
```

> [!TIP]
> Each module in `modules/`, `app/`, `web/`, and `env/` includes its own dedicated `README.md` with in-depth technical documentation.

---

<div align="center">
  <sub>Licensed under the <a href="LICENSE">Apache 2.0 License</a></sub>
</div>
