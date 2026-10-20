FROM alpine:3.24 AS build

# renovate: datasource=github-tags depName=aqbanking/aqbanking
ARG AQBANKING_VERSION=6.9.2

# AqBanking uses Gwenhywfar for its shared runtime and plugin infrastructure.
# renovate: datasource=github-tags depName=aqbanking/gwenhywfar
ARG GWENHYWFAR_VERSION=5.14.1

RUN apk add \
        --no-cache \
        build-base \
        ca-certificates \
        coreutils \
        gettext \
        gettext-dev \
        gmp-dev \
        gnutls-dev \
        libgcrypt-dev \
        pkgconf \
        python3 \
        xmlsec-dev

COPY --chmod=755 scripts/resolve-redmine-source.py /usr/local/bin/resolve-redmine-source

WORKDIR /build/gwenhywfar

RUN resolve-redmine-source gwenhywfar \
                           "gwenhywfar-${GWENHYWFAR_VERSION}.tar.gz" \
                           gwenhywfar.tar.gz
RUN tar --extract --gzip --file gwenhywfar.tar.gz --directory . --strip-components=1
RUN ./configure --prefix=/usr/local \
                --disable-network-checks \
                --with-guis=none
RUN make --jobs="$(nproc)"
RUN make check
RUN make install

WORKDIR /build/aqbanking

RUN resolve-redmine-source aqbanking \
                           "aqbanking-${AQBANKING_VERSION}.tar.gz" \
                           aqbanking.tar.gz
RUN tar --extract --gzip --file aqbanking.tar.gz --directory . --strip-components=1
RUN PKG_CONFIG_PATH=/usr/local/lib/pkgconfig \
    ./configure --prefix=/usr/local \
                --disable-tutorials

# AqBanking 6.9.2 export copies accounts but drops the context's securities.
COPY patches/aqbanking-cli-export-securities.patch /tmp/aqbanking-cli-export-securities.patch
RUN patch --batch --forward --fuzz=0 --strip=1 --input=/tmp/aqbanking-cli-export-securities.patch
RUN make --jobs="$(nproc)"
RUN make install

COPY tests/export-regression/ /tmp/export-regression/
RUN python3 /tmp/export-regression/verify.py /tmp/export-regression/securities.context

FROM alpine:3.24

RUN apk add \
        --no-cache \
        ca-certificates \
        gettext-libs \
        gmp \
        gnutls \
        libgcrypt \
        xmlsec

COPY --from=build /usr/local/ /usr/local/
RUN aqbanking-cli versions

RUN adduser -D -u 1000 -h /aqbanking aqbanking

WORKDIR /aqbanking
VOLUME /aqbanking

USER 1000
