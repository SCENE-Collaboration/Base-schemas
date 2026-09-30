FROM python:3.11-slim

RUN apt-get update -y && apt-get install -yy --no-install-recommends \
    default-mysql-client \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

ARG user_name=user
ARG uid=1000
ARG gid=1000

# -o: the host's uid/gid may already exist in the base image.
RUN groupadd -o -g ${gid} ${user_name} \
    && useradd -o -m -u ${uid} -g ${gid} ${user_name}
USER ${user_name}
ENV PATH="/home/${user_name}/.local/bin:${PATH}"

# COPY creates /base-schemas owned by the user, so pip -e can write egg-info.
COPY --chown=${uid}:${gid} . /base-schemas
WORKDIR /base-schemas
RUN pip install --no-cache-dir --user -e ".[dev]"

CMD ["bash"]
