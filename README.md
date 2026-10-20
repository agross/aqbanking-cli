# AqBanking CLI container

A standalone Alpine-based image containing AqBanking CLI and Gwenhywfar, built
from upstream release archives.

## Container registry

The GitHub Actions workflow publishes to `ghcr.io/agross/aqbanking-cli` on push,
using the repository's `GITHUB_TOKEN` with `packages: write` permission. It builds
`linux/amd64` and `linux/arm64` images and uses the GitHub Actions build cache.
Tags follow the branch name; the default branch also receives the AqBanking version
from `AQBANKING_VERSION` in the Dockerfile (for example, `6.9.2`) and `latest`.
Same-repository pull request builds also push their images to GHCR, tagged
`pr-<number>`, so
both architectures can be downloaded and tested before merging:

```sh
docker pull ghcr.io/agross/aqbanking-cli:pr-123
docker run --rm ghcr.io/agross/aqbanking-cli:pr-123 aqbanking-cli versions
```

Fork pull requests build both architectures and run the same build-time checks,
but skip registry login and publishing.

After the workflow has published an image:

```sh
docker run --rm ghcr.io/agross/aqbanking-cli:latest aqbanking-cli versions
```

## Build and run

```sh
docker build --tag aqbanking-cli:local .
docker run --rm aqbanking-cli:local aqbanking-cli versions
docker run --rm aqbanking-cli:local aqbanking-cli --help
```

The container runs as UID 1000, with `/aqbanking` as its home directory, working
directory, and volume. Mount a writable directory owned by UID 1000 to retain
AqBanking configuration between runs:

```sh
docker run --rm --interactive --tty \
  --volume "$PWD/data:/aqbanking" \
  aqbanking-cli:local aqbanking-cli --help
```

The image inherits Alpine's default command (`/bin/sh`). Pass any installed
tool and its arguments after the image name, for example:

```sh
docker run --rm aqbanking-cli:local aqhbci-tool4 --help
```

For a local build of either supported architecture:

```sh
docker buildx build --platform linux/amd64 --load --tag aqbanking-cli:amd64 .
docker buildx build --platform linux/arm64 --load --tag aqbanking-cli:arm64 .
```

Cross-platform builds require an emulator or a builder with native workers for
the requested architecture.

## Build contents and verification

- Alpine 3.24 is used for both compilation and the runtime image.
- Gwenhywfar 5.14.1 is built without GUI support. Its upstream `make check`
  suite must pass before installation; network-dependent tests are disabled.
- `scripts/resolve-redmine-source.py` resolves release archives through the
  upstream Redmine Files API and verifies their published SHA-256 digests.
- `patches/aqbanking-cli-export-securities.patch` preserves context-level
  securities during normal CLI export. It applies with zero fuzz; incompatible
  upstream changes fail the build for review.
- The build runs `tests/export-regression/verify.py` against a synthetic native
  context, checking account and securities preservation, quantities, prices,
  and UTC timestamps.
- The final image copies `/usr/local` from the builder, installs runtime
  dependencies. Compiler tools and the Python test runner remain in the builder.
