# syntax=docker/dockerfile:1

# Builder image. It builds the venv that will be copied to the final image
# 
ARG BASE_IMAGE_VERSION=latest
FROM ghcr.io/music-assistant/base:$BASE_IMAGE_VERSION AS builder

# Fastest way to install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# create venv which will be copied to the final image
ENV VIRTUAL_ENV=/app/venv
RUN uv venv $VIRTUAL_ENV

ADD dist dist
COPY requirements_all.txt .

# pre-install ALL requirements
# comes at a cost of a slightly larger image size but is faster to start
# because we do not have to install dependencies at runtime
RUN uv pip install \
    --find-links "https://wheels.home-assistant.io/musllinux/" \
    -r requirements_all.txt

# Install Music Assistant from prebuilt wheel
ARG MASS_VERSION
RUN uv pip install \
    --no-cache \
    --find-links "https://wheels.home-assistant.io/musllinux/" \
    "music-assistant@dist/music_assistant-${MASS_VERSION}-py3-none-any.whl"

# TODO: delete the unneeded architecture of librespot to decrease size!

# we need to set (very permissive) permissions to the workdir
# and /tmp to allow running the container as non-root
# NOTE that home assistant add-ons always run as root (and use apparmor)
# so we can't specify a user here
#
# IMPORTANT: chmod here, NOT on the final image, to avoid creating extra layers and increase size!
#
RUN chmod -R 777 /app

##################################################################################################

# FINAL docker image for music assistant server

FROM ghcr.io/music-assistant/base:$BASE_IMAGE_VERSION

ENV VIRTUAL_ENV=/app/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# copy the already build /app dir
COPY --from=builder /app /app

# the /app contents have correct permissinos but for some reason /app itself does not.
# so apply again, but ONLY to the dir (otherwise we increase the size)
RUN chmod 777 /app

# Set some labels
ARG MASS_VERSION
ARG TARGETPLATFORM
LABEL \
    org.opencontainers.image.title="Music Assistant Server" \
    org.opencontainers.image.description="Music Assistant Server/Core" \
    org.opencontainers.image.source="https://github.com/music-assistant/server" \
    org.opencontainers.image.authors="The Music Assistant Team" \
    org.opencontainers.image.documentation="https://github.com/orgs/music-assistant/discussions" \
    org.opencontainers.image.licenses="Apache License 2.0" \
    io.hass.version="${MASS_VERSION}" \
    io.hass.type="addon" \
    io.hass.name="Music Assistant Server" \
    io.hass.description="Music Assistant Server/Core" \
    io.hass.platform="${TARGETPLATFORM}" \
    io.hass.type="addon"

VOLUME [ "/data" ]
EXPOSE 8095

WORKDIR $VIRTUAL_ENV

ENTRYPOINT ["mass", "--config", "/data"]
