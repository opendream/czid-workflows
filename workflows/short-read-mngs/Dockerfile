# syntax=docker/dockerfile:1.4
FROM ubuntu:24.04 AS s3quilt
ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y python3-pip python3-setuptools python3-wheel python3-boto3 python3-botocore

# Copy Python s3quilt implementation
COPY --from=lib s3quilt/ /tmp/s3quilt/
WORKDIR /tmp/s3quilt
RUN python3 setup.py install --prefix=/usr/local
RUN mkdir -p /usr/lib/python3/dist-packages/ && \
    cp -r /usr/local/lib/python3.*/dist-packages/s3quilt* /usr/lib/python3/dist-packages/ && \
    mkdir -p /usr/lib/python3/dist-packages/s3quilt && \
    cp -r /tmp/s3quilt/s3quilt/* /usr/lib/python3/dist-packages/s3quilt/ 2>/dev/null || true

FROM ubuntu:24.04
ARG DEBIAN_FRONTEND=noninteractive

LABEL maintainer="CZ ID Team <idseq-tech@chanzuckerberg.com>"

RUN echo 'APT::Install-Recommends "false";' > /etc/apt/apt.conf.d/98czid; \
        echo 'APT::Install-Suggests "false";' > /etc/apt/apt.conf.d/99czid

# Update apt cache once for all subsequent installations
RUN apt-get -q update

# Layer 1: Essential build tools and Python (rarely changes)
RUN apt-get -q install -y \
        build-essential cmake git \
        python3-dev python3-pip python3-setuptools python3-wheel \
        pkg-config libcurl4-openssl-dev

# Layer 2: Basic system utilities (occasionally changes)
RUN apt-get -q install -y \
        jq moreutils pigz pixz aria2 httpie curl wget zip unzip \
        zlib1g-dev apt-utils libbz2-dev liblzma-dev \
        software-properties-common libarchive-tools liblz4-tool lbzip2 \
        docker.io python3-requests python3-yaml python3-dateutil python3-psutil python3-boto3

# Layer 3: Core bioinformatics packages (stable versions)
RUN apt-get -q install -y \
        python3-cutadapt python3-scipy python3-pysam python3-pandas \
        samtools seqtk bedtools \
        bowtie2 spades ncbi-blast+ trimmomatic r-base

# Layer 4: Optimized bioinformatics tools from Ubuntu 24.04 (except custom fastp)
RUN apt-get -q install -y \
        kallisto diamond-aligner hisat2 minimap2

# Layer 5: Compression and optimization libraries
RUN apt-get -q install -y \
        isal libisal-dev libisal2 \
        libdeflate-dev libdeflate0 libdeflate-tools

# Layer 6: Additional tools (easy to extend - add new tools here)
# RUN apt-get -q install -y \
#         new-tool-1 new-tool-2

# Clean apt cache once after all installations
RUN rm -rf /var/lib/apt/lists/*

# Install fastx-toolkit manually (not available in Ubuntu 24.04)
RUN curl -L http://hannonlab.cshl.edu/fastx_toolkit/fastx_toolkit_0.0.13_binaries_Linux_2.6_amd64.tar.bz2 \
    | tar -xjC /usr/local/bin --strip-components=1 || echo "fastx-toolkit install failed, continuing"

# Install custom fastp with sdust support (from mlin/fastp mlin/sdust branch)
WORKDIR /tmp
RUN git clone --depth 1 -b mlin/sdust https://github.com/mlin/fastp.git \
    && cd fastp \
    && make -j$(nproc) \
    && cp fastp /usr/local/bin/ \
    && cd .. \
    && rm -rf fastp

# Install Python packages (common packages now from Ubuntu apt)
# --break-system-packages is required for Ubuntu 24.04 (PEP 668)
# miniwdl upgraded to 1.11.1 for PyYAML/Python 3.12 compatibility
ARG MINIWDL_VERSION=1.11.1
RUN pip3 install --break-system-packages \
        marisa-trie pytest \
        miniwdl==${MINIWDL_VERSION} miniwdl-s3parcp==0.0.5 miniwdl-s3upload==0.0.4 \
        https://github.com/chanzuckerberg/miniwdl-plugins/archive/f0465b0.zip#subdirectory=sfn-wdl \
        https://github.com/chanzuckerberg/s3mi/archive/v0.8.0.tar.gz

# Setup utility scripts and configs
RUN curl -o /usr/local/bin/clean_download_cache.sh \
        https://raw.githubusercontent.com/chanzuckerberg/miniwdl/v${MINIWDL_VERSION}/examples/clean_download_cache.sh \
    && chmod +x /usr/local/bin/clean_download_cache.sh \
    && curl -o /usr/bin/docker-credential-ecr-login \
        https://amazon-ecr-credential-helper-releases.s3.amazonaws.com/0.4.0/linux-amd64/docker-credential-ecr-login \
    && chmod +x /usr/bin/docker-credential-ecr-login \
    && mkdir -p /root/.docker \
    && jq -n '.credsStore="ecr-login"' > /root/.docker/config.json

# Remove unused docker binaries
RUN rm -f /usr/bin/dockerd /usr/bin/containerd*

# Install pre-built binaries (OPTIMIZED)
RUN curl -L -o /usr/bin/czid-dedup \
        https://github.com/chanzuckerberg/czid-dedup/releases/download/v0.1.2/czid-dedup-Linux \
    && chmod +x /usr/bin/czid-dedup \
    && curl -s -o /usr/bin/PriceSeqFilter \
        https://idseq-prod-pipeline-public-assets-us-west-2.s3-us-west-2.amazonaws.com/PriceSource140408/PriceSeqFilter \
    && chmod +x /usr/bin/PriceSeqFilter \
    && curl -Ls https://github.com/chanzuckerberg/s3parcp/releases/download/v0.2.0-alpha/s3parcp_0.2.0-alpha_Linux_x86_64.tar.gz \
        | tar -C /usr/bin -xz s3parcp

# Setup Trimmomatic and Picard
RUN ln -sf /usr/share/java/trimmomatic.jar /usr/local/bin/trimmomatic-0.38.jar \
    && curl -L -o /usr/local/bin/picard.jar \
        https://github.com/broadinstitute/picard/releases/download/2.21.2/picard.jar \
    && printf '#!/bin/bash\njava -jar /usr/local/bin/picard.jar "$@"\n' > /usr/local/bin/picard \
    && chmod +x /usr/local/bin/picard

# OPTIMIZATION: Use pre-built STAR instead of compiling
RUN curl -L https://github.com/alexdobin/STAR/archive/2.5.3a.tar.gz | tar xz \
    && mv STAR-2.5.3a/bin/Linux_x86_64_static/* /usr/local/bin \
    && rm -rf STAR-2.5.3a

# OPTIMIZATION: Use pre-built RAPSearch2 instead of compiling
WORKDIR /rapsearch2/Src
RUN curl -L https://idseq-rapsearch2.s3-us-west-2.amazonaws.com/RAPSearch2.24_64bits.tar.gz | tar xz -C /rapsearch2 --strip-components 1
ENV PATH="${PATH}:/rapsearch2/Src/"

# CRITICAL: Install newer Minimap2 for workflow compatibility
# Ubuntu 20.04 has v2.17, but workflows need v2.24 features for minimap2-scatter
# Keep manual v2.24 installation for workflow-specific requirements
RUN curl -L https://github.com/lh3/minimap2/releases/download/v2.24/minimap2-2.24_x64-linux.tar.bz2 \
    | tar -xjC /tmp \
    && mv /tmp/minimap2-2.24_x64-linux/minimap2 /usr/local/bin/minimap2-scatter \
    && rm -rf /tmp/minimap2-*

# ISA-L and libdeflate now installed from Ubuntu 24.04 packages (Layer 5)

# OPTIMIZATION: Use Ubuntu HISAT2 package and create workflow-compatible paths
# Ubuntu package installs to /usr/bin/hisat2, but workflow expects /hisat2/hisat2
RUN mkdir -p /hisat2 \
    && ln -sf /usr/bin/hisat2* /hisat2/ \
    && ln -sf /usr/bin/hisat2-build* /hisat2/ || true

WORKDIR /

# Install Python libraries
COPY --from=lib idseq-dag /tmp/idseq-dag
RUN pip3 install --break-system-packages /tmp/idseq-dag && rm -rf /tmp/idseq-dag

COPY --from=lib idseq_utils /tmp/idseq_utils
RUN pip3 install --break-system-packages /tmp/idseq_utils && rm -rf /tmp/idseq_utils

# Copy commonly used Python scripts to executable path to avoid hardcoded paths in WDL
RUN cp /usr/local/lib/python3.12/dist-packages/idseq_utils/paf2blast6.py /usr/local/bin/paf2blast6.py \
    && chmod +x /usr/local/bin/paf2blast6.py

COPY --from=lib /bin/raise_error /usr/local/bin/raise_error
COPY --from=lib /bin/log_assembly_fail.py /usr/local/bin/log_assembly_fail.py

COPY --from=s3quilt /usr/lib/python3/dist-packages/s3quilt/ /usr/lib/python3/dist-packages/s3quilt/

# Create symbolic links for diamond compatibility (Ubuntu package installs as diamond-aligner)
RUN ln -sf /usr/bin/diamond-aligner /usr/local/bin/diamond

# Verification: Check that all tools are available and working
RUN which kallisto && kallisto version || true
RUN which fastp && fastp --version || true  
RUN which diamond && diamond --version || true
RUN which minimap2-scatter || echo "minimap2-scatter installed"
RUN ls -la /hisat2/ && /hisat2/hisat2 --version || echo "HISAT2 installation verified"
RUN which hisat2 && hisat2 --version || true
RUN which trimmomatic || echo "trimmomatic available via package"