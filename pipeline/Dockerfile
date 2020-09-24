FROM quay.io/azavea/raster-vision:pytorch-b72297b

RUN pip3 install --upgrade pystac==0.5.2

COPY sen1floods11_pipeline.py /workdir/
COPY usfimr_pipeline.py /workdir/
COPY default /root/.rastervision/

COPY multi-raster-source.diff /tmp/
COPY vsi-cache.diff /tmp/
RUN cd /opt/src && \
    patch -p1 < /tmp/multi-raster-source.diff && \
    patch -p1 < /tmp/vsi-cache.diff

CMD ["bash"]
