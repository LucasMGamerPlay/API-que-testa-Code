FROM mcr.microsoft.com/dotnet/sdk:9.0

ENV DEBIAN_FRONTEND=noninteractive
ENV PATH="/opt/venv/bin:${PATH}"
ENV DOTNET_CLI_HOME=/tmp/dotnet
ENV NUGET_PACKAGES=/tmp/nuget
ENV GOCACHE=/tmp/go-build
ENV GOPATH=/tmp/go
ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-venv python3-pip nodejs npm rustc cargo golang g++ default-jdk \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN python3 -m venv /opt/venv \
    && pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY static ./static
COPY tests ./tests
COPY README.md .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]