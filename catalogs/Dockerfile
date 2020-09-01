FROM continuumio/miniconda3

COPY ./requirements.txt /tmp/requirements.txt

RUN apt update \
  && apt install -y --no-install-recommends unzip \
  && rm -rf /var/lib/apt/lists/*

RUN conda create -n env python=3.7
RUN conda install -n env --yes --channel conda-forge \
  --file /tmp/requirements.txt

RUN echo "source activate env" > ~/.bashrc
ENV PATH /opt/conda/envs/env/bin:$PATH

WORKDIR /opt/catalogs

ENTRYPOINT [ "./main.sh" ]
