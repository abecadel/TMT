FROM nvidia/cuda:11.8.0-cudnn8-devel-ubuntu22.04
WORKDIR /app

ENV DEBIAN_FRONTEND=noninteractive

ENV PATH="/root/miniconda3/bin:${PATH}"
ARG PATH="/root/miniconda3/bin:${PATH}"

RUN apt-get update
RUN apt-get install -y wget git libgl1 libglib2.0-0 ffmpeg build-essential curl libtbb-dev libopenexr-dev

RUN wget \
    https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh \
    && mkdir /root/.conda \
    && bash Miniconda3-latest-Linux-x86_64.sh -b \
    && rm -f Miniconda3-latest-Linux-x86_64.sh
RUN conda update -n base -c defaults conda -y
RUN conda init
RUN conda create --name digi python=3.10

SHELL ["conda", "run", "--no-capture-output", "-n", "digi", "/bin/bash", "-c"]
RUN conda conda install pytorch torchvision torchaudio pytorch-cuda=11.8 -c pytorch -c nvidia
RUN conda install -c kitsune.one python-blender

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY src src
COPY data data
