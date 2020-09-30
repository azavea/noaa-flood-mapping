FROM continuumio/miniconda3

RUN apt update \
  && apt install -y --no-install-recommends unzip \
  && rm -rf /var/lib/apt/lists/*

RUN conda create -n env python=3.7
RUN conda config --set pip_interop_enabled True
COPY ./requirements-conda.txt /tmp/requirements-conda.txt
RUN conda install -n env --yes --channel conda-forge \
  --file /tmp/requirements-conda.txt

RUN echo "source activate env" > ~/.bashrc
ENV PATH /opt/conda/envs/env/bin:$PATH

# Only use pip to install any python deps that are not available on conda
# After setting env so we use conda pip
COPY ./requirements-pip.txt /tmp/requirements-pip.txt
RUN pip install -r /tmp/requirements-pip.txt

WORKDIR /opt/catalogs

COPY ./main.sh main.sh

ENTRYPOINT [ "./main.sh" ]
