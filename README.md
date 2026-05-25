# 🚨 Dynatrace Problem Buzzer

A lightweight, enterprise-ready background monitoring utility for detecting active problems in Dynatrace environments.

The tool continuously polls the Dynatrace Problems API and immediately notifies engineers through native Windows alerts and audible notifications whenever new incidents are detected — without requiring heavy UI frameworks or third-party notification systems.

---

# ✨ Features

## 🔔 Real-Time Native Notifications

Uses built-in Windows APIs:

- `MessageBoxW`
- `MessageBeep`

to instantly alert engineers when new problems are detected.

---

## 📜 Enterprise-Grade Logging

Integrated rotating log management using Python’s `RotatingFileHandler`.

### Benefits

- Prevents uncontrolled log growth
- Protects system disk space
- Maintains historical logs for troubleshooting

### Log Policy

| Setting | Value |
|---|---|
| Max Log File Size | 5 MB |
| Backup Files Retained | 3 |

---

## ⚙️ Dynamic Logging Levels

Supports configurable runtime verbosity:

- `DEBUG`
- `INFO`
- `WARNING`
- `ERROR`
- `CRITICAL`

Logging behavior can be modified directly from `config.json` without restarting the application.

---

## 🔐 SSL Verification Control

Designed for enterprise environments using:

- Internal proxies
- Custom CA certificates
- Restricted outbound networks

SSL validation can be enabled or disabled via configuration.

---

## 🔄 Hot-Reload Configuration

The application reloads configuration values during every polling cycle.

### Advantages

- No restart required
- Immediate configuration updates
- Faster operational tuning

---

## 💾 Persistent State Tracking

Maintains a local cache file:

```text
seen_problems.json
```

This prevents repeated notifications for already acknowledged incidents, even after:

- Application restarts
- Server reboots
- Unexpected crashes

---

# 🏗️ Architecture Overview

```text
+-------------------------------------------------------+
|                 Windows Environment                   |
|                                                       |
|  +------------------+         +--------------------+  |
|  |   config.json    | <-----+ | dynatracebuzzer2.1.py |
|  +------------------+         +---------+----------+  |
|                                         |             |
|                                         v             |
|  +------------------+         +---------+----------+  |
|  |seen_problems.json| <-----+ |  Monitoring Cycle  |  |
|  +------------------+         +---------+----------+  |
|                                         |             |
+-----------------------------------------|-------------+
                                          |
                                  HTTPS REST API
                                   SSL True/False
                                          |
                                          v
                              +-------------------+
                              | Dynatrace API v2  |
                              +-------------------+
```

---

# 📁 Required Runtime Files

The following files must exist in the same directory:

```text
dynatracebuzzer2.1.exe
config.json
seen_problems.json
```

---
## 🔑 Required API Token Scope

The Dynatrace API token must include the following permission:

```text
Read problems (problems.read)
```
# ⚙️ Configuration

The application requires a `config.json` file in the runtime directory.

## Example Configuration

```json
{
  "dynatrace": {
    "base_url": "https://your-tenant.live.dynatrace.com",
    "api_token": "dt0c01.xxxxxxxxxxxxxxxxx"
  },

  "filters": {
    "management_zones": [
      "DB",
      "DC"
    ],
    "text_filter": ""
  },

  "app_settings": {
    "log_level": "INFO",
    "ssl_verify": true,
    "interval_seconds": 60
  }
}
```

---

# 📘 Configuration Parameters

## Dynatrace Settings

| Parameter | Description |
|---|---|
| `base_url` | Dynatrace SaaS or Managed tenant URL |
| `api_token` | Dynatrace API token with Problems API access |

### Supported URL Formats

#### SaaS

```text
https://<tenant>.live.dynatrace.com
```

#### Managed

```text
https://<managed-domain>/e/<environment-id>
```

---

## Filter Settings

| Parameter | Description |
|---|---|
| `management_zones` | Restrict monitoring to specific Management Zones |
| `text_filter` | Optional text-based filtering |

---

## Application Settings

| Parameter | Description |
|---|---|
| `log_level` | Logging verbosity |
| `ssl_verify` | Enable/Disable SSL certificate validation |
| `interval_seconds` | Polling interval in seconds |

---

# 🔒 Security Recommendations

## Recommended Best Practices

- Store API tokens securely
- Restrict token permissions to minimum required scopes
- Avoid disabling SSL verification in production
- Exclude configuration files from public repositories

Example `.gitignore`:

```gitignore
config.json
seen_problems.json
*.log
```

---

# 🚀 Typical Use Cases

- NOC Monitoring
- Production Incident Detection
- 24x7 Operations Teams
- Infrastructure Monitoring
- Middleware Monitoring
- Application Support Teams
- Enterprise Command Centers

---

# 🛠️ Technology Stack

| Component | Technology |
|---|---|
| Language | Python |
| Notifications | Windows Native API |
| Logging | Python Logging Framework |
| API Integration | Dynatrace Problems API v2 |
| Packaging | PyInstaller |

---

# 📌 Operational Flow

```text
Start Application
        ↓
Load Configuration
        ↓
Load Seen Problems Cache
        ↓
Call Dynatrace Problems API
        ↓
Check for New Problems
        ↓
Trigger Alert + Sound
        ↓
Update Seen Cache
        ↓
Sleep for Configured Interval
        ↓
Repeat
```

---

# ▶️ Running the Application

## Python Mode

```bash
python dynatracebuzzer2.1.py
```

## Executable Mode

```bash
dynatracebuzzer2.1.exe
```

---

# 📄 License

Internal enterprise utility intended for operational monitoring and alerting purposes.

---

# 👨‍💻 Author

Developed for enterprise-grade monitoring operations using Dynatrace APIs and Windows native notification mechanisms.
