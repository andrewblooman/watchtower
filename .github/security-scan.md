# SECURITY.md — Automated Security Scanning Guide

This document is designed to be read by an LLM agent. Follow the steps below in order:
1. Check whether each tool is installed; if not, install it using the instructions for the detected OS.
2. Run all four security scans against the current repository/project directory.
3. Report findings grouped by tool and severity.

---

## Supported Platforms

- **Ubuntu / Debian**
- **macOS**

> Windows is not supported. If a Windows environment is detected, inform the user and stop.

---

## Step 1 — Detect Operating System

Before installing or running any tool, detect the OS:

```bash
uname -s
```

- Output `Linux` → use **Ubuntu/Debian** instructions
- Output `Darwin` → use **macOS** instructions

---

## Step 2 — Check & Install Tools

For each tool below, first check if it is already installed. If the check command succeeds, skip the install. If it fails, run the install instructions for the detected OS.

---

### 2.1 Semgrep

**Check:**
```bash
semgrep --version
```

**Install — Ubuntu:**
```bash
# install through pip
python3 -m pip install semgrep

# If you receive "error: externally-managed-environment", use pipx instead:
# sudo apt install pipx
# pipx install semgrep

# Confirm installation
semgrep --version
```

**Install — macOS:**
```bash
# Option 1: Homebrew (recommended)
brew install semgrep

# Option 2: pip
python3 -m pip install semgrep

# Confirm installation
semgrep --version
```

> Note for Homebrew users: ensure Homebrew is added to your PATH.

---

### 2.2 Trivy

**Check:**
```bash
trivy --version
```

**Install — Ubuntu:**
```bash
sudo apt-get install wget gnupg
wget -qO - https://aquasecurity.github.io/trivy-repo/deb/public.key | gpg --dearmor | sudo tee /usr/share/keyrings/trivy.gpg > /dev/null
echo "deb [signed-by=/usr/share/keyrings/trivy.gpg] https://aquasecurity.github.io/trivy-repo/deb generic main" | sudo tee -a /etc/apt/sources.list.d/trivy.list
sudo apt-get update
sudo apt-get install trivy
```

**Install — macOS:**
```bash
brew install trivy
```

**Confirm installation:**
```bash
trivy --version
```

---

### 2.3 Gitleaks

**Check:**
```bash
gitleaks version
```

**Install — Ubuntu:**
```bash
GITLEAKS_VERSION=$(curl -s "https://api.github.com/repos/gitleaks/gitleaks/releases/latest" | grep -Po '"tag_name": "v\K[0-9.]+')
wget -qO gitleaks.tar.gz https://github.com/gitleaks/gitleaks/releases/latest/download/gitleaks_${GITLEAKS_VERSION}_linux_x64.tar.gz
sudo tar xf gitleaks.tar.gz -C /usr/local/bin gitleaks
rm -rf gitleaks.tar.gz

# Confirm installation
gitleaks version
```

**Install — macOS:**
```bash
brew install gitleaks

# Confirm installation
gitleaks version
```

---

## Step 3 — Run Security Scans

Once all tools are confirmed installed, run the following scans from the **root of the repository/project directory**.

> Set the target path variable before running:
> ```bash
> TARGET="."   # or replace with the path to the project directory
> ```

---

### 3.1 Semgrep — OWASP Top 10 & General Security

Semgrep is used to detect code-level vulnerabilities including those in the OWASP Top 10 (injection, broken auth, sensitive data exposure, XXE, broken access control, security misconfiguration, XSS, insecure deserialization, known vulnerable components, insufficient logging).

```bash
semgrep scan \
  --config "p/owasp-top-ten" \
  --config "p/security-audit" \
  --config "p/secrets" \
  --severity ERROR \
  --severity WARNING \
  --json \
  --output semgrep-results.json \
  $TARGET
```

**Human-readable output (optional):**
```bash
semgrep scan \
  --config "p/owasp-top-ten" \
  --config "p/security-audit" \
  --config "p/secrets" \
  --severity ERROR \
  --severity WARNING \
  $TARGET
```

**Key flags explained:**
- `p/owasp-top-ten` — rules mapped to OWASP Top 10 categories
- `p/security-audit` — broad security audit ruleset
- `p/secrets` — detects hardcoded secrets and credentials in source code
- `--severity ERROR --severity WARNING` — captures high and medium severity findings
- `--json --output semgrep-results.json` — saves findings for review

---

### 3.2 Trivy — Vulnerability Scanning (Dependencies, IaC, Container Images)

Trivy scans for known CVEs in dependencies, misconfigurations in infrastructure-as-code, and exposed secrets.

**Filesystem scan (dependencies + IaC + secrets):**
```bash
trivy fs \
  --scanners vuln,misconfig,secret \
  --severity CRITICAL,HIGH,MEDIUM \
  --format json \
  --output trivy-results.json \
  $TARGET
```

**Human-readable output (optional):**
```bash
trivy fs \
  --scanners vuln,misconfig,secret \
  --severity CRITICAL,HIGH,MEDIUM \
  $TARGET
```

**Key flags explained:**
- `--scanners vuln` — scans for known CVEs in package dependencies (npm, pip, go, etc.)
- `--scanners misconfig` — checks IaC files (Dockerfile, Kubernetes, Terraform, etc.) for security misconfigurations
- `--scanners secret` — detects hardcoded secrets and tokens
- `--severity CRITICAL,HIGH,MEDIUM` — filters to actionable findings; add `LOW` if comprehensive output is needed
- `--format json --output trivy-results.json` — saves findings for review

---

### 3.3 Gitleaks — Secrets & Credentials in Git History

Gitleaks scans the full Git history and working directory for hardcoded secrets, API keys, tokens, and credentials.

**Scan full Git history:**
```bash
gitleaks detect \
  --source $TARGET \
  --report-format json \
  --report-path gitleaks-results.json \
  --verbose
```

**Scan staged/uncommitted changes only:**
```bash
gitleaks protect \
  --source $TARGET \
  --report-format json \
  --report-path gitleaks-staged-results.json \
  --staged \
  --verbose
```

**Key flags explained:**
- `detect` — scans the full Git log and working tree
- `protect` — scans only staged changes (useful as a pre-commit check)
- `--report-format json` — structured output for review or CI integration
- `--verbose` — prints each finding as it is discovered

---

### 3.4 Docker Security Scan — Dockerfile Audit & Image Vulnerability Scan

This section covers two complementary Docker checks: a **Dockerfile best-practice audit** using Hadolint, and a **container image vulnerability scan** using Trivy. Both checks are run if any Dockerfiles are found in the project.

---

#### 3.4.1 Check for Dockerfiles

Before running Docker-specific scans, check whether any Dockerfiles exist in the project:

```bash
find $TARGET -name "Dockerfile*" -not -path "*/.git/*"
```

- If **no Dockerfiles are found**, skip this entire section and note: `Docker scan: No Dockerfiles detected.`
- If **one or more Dockerfiles are found**, proceed with both scans below for each file.

---

#### 3.4.2 Hadolint — Dockerfile Best Practice & Misconfiguration Audit

Hadolint is a Dockerfile linter that checks for security issues, outdated practices, and violations of Docker best practices. It maps findings to CIS Docker Benchmark rules.

**Check:**
```bash
hadolint --version
```

**Install — Ubuntu:**
```bash
HADOLINT_VERSION=$(curl -s "https://api.github.com/repos/hadolint/hadolint/releases/latest" | grep -Po '"tag_name": "v\K[0-9.]+')
wget -qO /usr/local/bin/hadolint https://github.com/hadolint/hadolint/releases/latest/download/hadolint-Linux-x86_64
chmod +x /usr/local/bin/hadolint

# Confirm installation
hadolint --version
```

**Install — macOS:**
```bash
brew install hadolint

# Confirm installation
hadolint --version
```

**Scan each Dockerfile found:**
```bash
hadolint \
  --format json \
  <path/to/Dockerfile> > hadolint-results.json
```

**Human-readable output (optional):**
```bash
hadolint <path/to/Dockerfile>
```

If multiple Dockerfiles exist, run Hadolint against each one and append results. Report the Dockerfile path alongside each finding.

**Key flags explained:**
- `--format json` — structured output for parsing and reporting

**What Hadolint checks for:**

| Check | Rule | Severity |
|---|---|---|
| Unpinned or EOL base image tag (e.g. `node:13`) | DL3006 | WARNING |
| Missing image digest pin (`FROM image@sha256:...`) | DL3007 | INFO |
| `apt-get` without pinned versions | DL3008 | WARNING |
| `sudo` used inside container | DL3004 | ERROR |
| `ADD` used instead of `COPY` | DL3020 | ERROR |
| `npm install` without `--omit=dev` or `NODE_ENV=production` | DL3016 | WARNING |
| `apt-get upgrade` used (non-deterministic) | DL3005 | ERROR |
| `curl` piped directly to shell | DL4006 | WARNING |
| Multiple `RUN` commands that should be chained | DL3059 | INFO |

---

#### 3.4.3 LLM Dockerfile Review — Extended Checks

After running Hadolint, perform the following **additional checks by reading the Dockerfile directly**. These cover issues that static linters do not catch.

For each Dockerfile found, read its contents and check for every item in this list:

**1. Hardcoded secrets in ENV or ARG**

Flag any `ENV` or `ARG` instruction that contains passwords, tokens, keys, or connection strings. Example of a violation:
```dockerfile
ENV MONGO_DB_USERNAME=admin \
    MONGO_DB_PWD=password        # ❌ hardcoded credential
```
Recommended fix: Use Docker secrets or build-time args sourced from a secrets manager. Never hardcode credentials.

**2. Running as root**

Flag if there is no `USER` instruction, or if the image explicitly sets `USER root`. Containers should run as a non-root user.
```dockerfile
# ❌ No USER instruction — defaults to root
CMD ["node", "server.js"]

# ✅ Correct
RUN addgroup -S appgroup && adduser -S appuser -G appgroup
USER appuser
CMD ["node", "server.js"]
```

**3. Missing HEALTHCHECK**

Flag if there is no `HEALTHCHECK` instruction. Production containers should define a health check so orchestrators (Docker Compose, Kubernetes) can detect unhealthy containers.
```dockerfile
# ✅ Example
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD wget -qO- http://localhost:3000/health || exit 1
```

**4. Missing image labels**

Flag if there are no `LABEL` instructions. Images should include metadata labels for maintainability and compliance.
```dockerfile
# ✅ Recommended labels
LABEL maintainer="your-team@example.com" \
      version="1.0.0" \
      description="Node.js application server" \
      org.opencontainers.image.source="https://github.com/your-org/your-repo"
```

**5. Outdated or EOL base image**

Check the `FROM` instruction for known EOL or outdated image tags. Flag any of the following patterns:
- A specific version number that is known to be EOL (e.g. `node:13`, `node:14`, `python:3.7`, `ubuntu:18.04`)
- A floating tag with no version pin (e.g. `node:alpine`, `ubuntu:latest`)
- No SHA digest pin

```dockerfile
# ❌ Violations
FROM node:13-alpine          # EOL version
FROM node:alpine             # unpinned — resolves to different image over time
FROM node:lts-alpine         # unpinned floating tag

# ✅ Correct
FROM node:20-alpine3.19@sha256:<digest>   # pinned version + digest
```

After flagging the version, check the [Docker Hub](https://hub.docker.com) page for the image or use known EOL data to confirm whether the version is still receiving security updates. Recommend upgrading to the current LTS or stable release.

**6. Unnecessary packages or dev dependencies in production image**

Flag if a package manager install step does not exclude development dependencies. Examples:
```dockerfile
# ❌ Installs dev dependencies in production image
RUN npm install

# ✅ Correct
RUN npm install --omit=dev
# or
ENV NODE_ENV=production
RUN npm install

# ❌ pip without --no-cache-dir increases image size unnecessarily
RUN pip install -r requirements.txt

# ✅ Correct
RUN pip install --no-cache-dir -r requirements.txt
```

**7. Missing .dockerignore**

Check whether a `.dockerignore` file exists in the same directory as the Dockerfile:
```bash
find $TARGET -name ".dockerignore" -not -path "*/.git/*"
```
If no `.dockerignore` is found, flag it. Without it, sensitive files (`.env`, `node_modules`, `.git`, credentials) may be unintentionally copied into the image via `COPY . .` instructions.

Recommended `.dockerignore` entries:
```
.git
.env
*.env
node_modules
npm-debug.log
.DS_Store
*.md
tests/
.github/
```

**8. COPY . . without .dockerignore**

If the Dockerfile contains `COPY . .` or `COPY . /app` (wildcard copy of entire context) and no `.dockerignore` exists, escalate this to HIGH severity as sensitive files are very likely being included in the image.

---

#### 3.4.4 Trivy — Container Image Vulnerability Scan

If the project has a Dockerfile and the image can be built, Trivy can scan the resulting image for CVEs in OS packages and language dependencies baked into the image.

**Build the image first (if not already built):**
```bash
docker build -t security-scan-target:latest <path/to/directory/containing/Dockerfile>
```

**Scan the built image:**
```bash
trivy image \
  --scanners vuln,secret \
  --severity CRITICAL,HIGH,MEDIUM \
  --format json \
  --output trivy-image-results.json \
  security-scan-target:latest
```

**Human-readable output (optional):**
```bash
trivy image \
  --scanners vuln,secret \
  --severity CRITICAL,HIGH,MEDIUM \
  security-scan-target:latest
```

> If Docker is not installed or the image cannot be built, skip this step and note: `Trivy image scan: skipped — Docker not available or image could not be built.`

**Key flags explained:**
- `trivy image` — scans a built container image (not just the Dockerfile)
- `--scanners vuln` — detects CVEs in OS packages (Alpine, Debian, Ubuntu) and language runtimes (Node, Python, Go, etc.) installed inside the image
- `--scanners secret` — detects secrets baked into image layers
- `--severity CRITICAL,HIGH,MEDIUM` — filters to actionable findings

---

## Step 4 — Review & Report Findings

After all scans complete, summarise findings as follows:

1. **Semgrep** (`semgrep-results.json`) — list findings by OWASP category, file, line number, and severity.
2. **Trivy filesystem** (`trivy-results.json`) — list CVEs by package, version, fixed version (if available), and severity; list any misconfigurations and secrets found.
3. **Gitleaks** (`gitleaks-results.json`) — list any detected secrets by file, line, rule ID, and commit hash.
4. **Docker — Hadolint** (`hadolint-results.json`) — list Dockerfile rule violations by rule ID, line number, and severity.
5. **Docker — LLM review** — list all findings from the extended Dockerfile checks (hardcoded secrets, missing USER, missing HEALTHCHECK, missing labels, EOL base image, missing .dockerignore, dev dependencies).
6. **Docker — Trivy image** (`trivy-image-results.json`) — list CVEs found inside the built container image by package, installed version, fixed version, and severity.

For each finding provide:
- Tool name
- Severity (CRITICAL / HIGH / MEDIUM / LOW)
- File path and line number
- Description of the issue
- Recommended remediation

If no issues are found by a tool, explicitly state: `[TOOL NAME]: No issues detected.`

---

## Output Files

| File | Tool | Contents |
|---|---|---|
| `semgrep-results.json` | Semgrep | OWASP Top 10 & security audit findings |
| `trivy-results.json` | Trivy | CVEs, misconfigurations, secrets in filesystem |
| `trivy-image-results.json` | Trivy | CVEs and secrets inside built container image |
| `gitleaks-results.json` | Gitleaks | Secrets in full Git history |
| `gitleaks-staged-results.json` | Gitleaks | Secrets in staged changes |
| `hadolint-results.json` | Hadolint | Dockerfile best-practice and misconfiguration findings |

---

## Notes

- Always run scans from the root of the repository unless a specific subdirectory is intended.
- Gitleaks requires the target directory to be a Git repository (i.e. `.git` folder must be present). If it is not, skip the Gitleaks scan and inform the user.
- Trivy will automatically download and update its vulnerability database on first run; an internet connection is required.
- Semgrep rules are fetched from the Semgrep registry; an internet connection is required.
- Docker section (3.4) is skipped automatically if no Dockerfiles are found in the project.
- The Trivy image scan (3.4.4) requires Docker to be installed and the image to be buildable. If Docker is unavailable, skip that sub-step only — Hadolint and the LLM Dockerfile review still run.
- The LLM Dockerfile review in 3.4.3 must be performed by reading the Dockerfile contents directly and reasoning about each check — it is not automated by a tool.
- These scans are non-destructive and read-only; they will not modify any project files.