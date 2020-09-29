FROM quay.io/azavea/raster-vision:pytorch-b8e8c65

RUN pip3 install --upgrade pystac==0.5.2

COPY sen1floods11_pipeline.py /workdir/
COPY usfimr_pipeline.py /workdir/
COPY default /root/.rastervision/

COPY patches/shm.diff /tmp/
COPY patches/nan.diff /tmp/
RUN cd /opt/src && patch -p1 < /tmp/shm.diff && patch -p1 < /tmp/nan.diff

CMD ["bash"]
