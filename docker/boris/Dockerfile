# Author:    mikomeller
# Version:   0.1.1
# Filename:  Dockerfile
# Pathname:  docker/boris/Dockerfile
# Purpose:   Run the Affinidi TrustBoris CLI (boris) in a container instead of on the Mac.
#            Source: Homebrew cask affinidi-ai/tap Casks/boris.rb (static musl Linux build).
FROM debian:bookworm-slim

ARG BORIS_VERSION=0.1.35
# sha256 values copied from the cask; TARGETARCH is set by buildx (arm64 or amd64).
ARG SHA_ARM64=c05085ce6aaa265ed75bf72e39d02eaf4125d110fe86edb8e3376efaf8c5bc58
ARG SHA_AMD64=354fd1194a487289139e6387d5294d802d987951909af393761f2801fd564635
ARG TARGETARCH

RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates curl \
 && rm -rf /var/lib/apt/lists/* \
 && case "$TARGETARCH" in \
      arm64) A=aarch64; SHA="$SHA_ARM64" ;; \
      amd64) A=x86_64;  SHA="$SHA_AMD64" ;; \
      *) echo "unsupported arch: $TARGETARCH" >&2; exit 1 ;; \
    esac \
 && curl -fsSL -o /tmp/boris.tar.gz \
      "https://releases.trustboris.ai/boris/v${BORIS_VERSION}/boris-${BORIS_VERSION}-${A}-unknown-linux-musl.tar.gz" \
 && echo "${SHA}  /tmp/boris.tar.gz" | sha256sum -c - \
 && tar -xzf /tmp/boris.tar.gz -C /usr/local/bin boris \
 && chmod 0755 /usr/local/bin/boris \
 && rm /tmp/boris.tar.gz

RUN useradd -m -u 10001 boris
USER boris
WORKDIR /home/boris
CMD ["boris", "--help"]
