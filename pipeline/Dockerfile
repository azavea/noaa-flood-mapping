FROM quay.io/azavea/raster-vision:pytorch-b8e8c65

RUN pip3 install --upgrade pystac==0.5.2 && apt-get install -y nano

# Pipelines
COPY sen1floods11_pipeline.py /workdir/
COPY usfimr_pipeline.py /workdir/
COPY default /root/.rastervision/

# Patches
COPY patches/shm.diff /tmp/
COPY patches/nan.diff /tmp/
COPY patches/ignore_index.diff /tmp/
COPY patches/filter.diff /tmp/
RUN cd /opt/src && \
    patch -p1 < /tmp/shm.diff && \
    patch -p1 < /tmp/nan.diff && \
    patch -p1 < /tmp/ignore_index.diff && \
    patch -p1 < /tmp/filter.diff

CMD ["bash"]
