FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install Python and tools
RUN apt-get update \
	&& apt-get install -y --no-install-recommends \
	   python3 \
	   python3-pip \
	   build-essential \
	   curl \
	&& rm -rf /var/lib/apt/lists/*

# Ensure pip is the python3 pip
RUN ln -s /usr/bin/pip3 /usr/local/bin/pip || true

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application
COPY . /app

# Expose the user-facing port
EXPOSE 5048

# Run Streamlit on 0.0.0.0 so the container is reachable and use port 5048
CMD ["streamlit", "run", "main.py", "--server.port", "5048", "--server.address", "0.0.0.0"]
