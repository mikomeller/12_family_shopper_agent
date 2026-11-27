<!--
Author:    mikomeller
Version:   0.1.1
Filename:  boris_docker.md
Pathname:  doc/runbooks/boris_docker.md
Purpose:   Runbook: run the Affinidi TrustBoris CLI (boris) in a Docker container instead of on the Mac
-->
# Runbook: boris CLI in Docker

## Source facts (verified)
Cask `affinidi-ai/tap` `Casks/boris.rb` (read via `gh api`): version 0.1.35, URL
`https://releases.trustboris.ai/boris/v0.1.35/boris-0.1.35-<aarch64|x86_64>-<apple-darwin|unknown-linux-musl>.tar.gz`,
sha256 per platform in the cask. The tap README states Linux arm64 and x86_64 (static musl binary) are supported.
The arm64 Linux tarball returned HTTP 200 (9.8 MB). The Dockerfile verifies the sha256 from the cask at build time.

## Steps
1. Build the image (from the repo root).
   `docker build -t family-shopper/boris docker/boris`
   Expected: build succeeds (sha256 check passes). **Verified.**
2. Check the version.
   `docker run --rm family-shopper/boris boris --version`
   Verified output: `boris 0.1.35 (aarch64-unknown-linux-musl, b291fbc9)`
3. Run the doctor.
   `docker run --rm family-shopper/boris boris doctor`
   **Verified**, exit code 9 with "1 problem, 5 warnings":
   - CLI ok (warning: not installed by an installer, background services refuse it)
   - Sign-in: not signed in (expected, step 5 fixes it)
   - systemd: no user manager (container, so `boris local` background service will not work)
   - Docker: "docker is not installed (registry agents run in Docker)"
   - git missing, clipboard missing (warnings)
4. Docker socket test.
   `docker run --rm -v /var/run/docker.sock:/var/run/docker.sock family-shopper/boris boris doctor`
   **Verified:** mounting the socket alone changes nothing; doctor still says docker is not installed, because boris looks for the
   `docker` CLI binary. Docker-in-Docker (installing `docker-ce-cli` plus the socket mount) is **unverified** and not in the image.
   Features that run registry agents or the runner image (`boris agent`, `boris images`) therefore need the CLI inside the image
   or boris on the Mac. Plain login, status, plan, apply, env, secret should not need Docker (unverified beyond login help).
5. Sign in (owner, by hand; not run by me).
   `docker run --rm -it -v boris-home:/home/boris family-shopper/boris boris login --url https://trustboris.ai --device`
   Reason: `boris login --help` lists `--device` ("sign in with a code on another device instead of this machine's browser") and
   `--no-browser` (prints the link). The container has no browser, so use one of these. The default browser flow's callback
   port is **not documented** in the help; I did not find which port it uses, so do not rely on it. A first sign-in needs an
   interactive terminal (`-it`) to confirm. The named volume `boris-home` keeps credentials (storage location **unverified**;
   also the keychain is absent in the container, so boris may use a file store, **unverified**).
6. Use it afterwards.
   `docker run --rm -it -v boris-home:/home/boris -v "$PWD":/work -w /work family-shopper/boris boris status`
   **Unverified** (needs login).

## Not verified
Actual login in a container, volume path for credentials, any command that needs Docker, `boris tunnel` (would need a published
port), amd64 image build (only arm64 built; amd64 hash is from the cask).

## Owner must do by hand
Step 5 (browser/code approval and the interactive yes), and decide whether Docker-in-Docker is needed for agent hosting.
Fallback: `brew install --cask affinidi-ai/tap/boris` on the Mac (the cask is the official route).
