FROM python:3.11-slim

WORKDIR /base-schemas

RUN apt-get update -y && apt-get install -yy --no-install-recommends \
    default-mysql-client \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

ARG user_name=user
ARG uid=1000
ARG gid=1000

RUN groupadd -g ${gid} ${user_name} \
    && useradd -m -u ${uid} -g ${gid} ${user_name}
USER ${user_name}
ENV PATH="/home/${user_name}/.local/bin:${PATH}"

COPY . /base-schemas
RUN pip install --no-cache-dir --user -e ".[dev]"

CMD ["bash"]
