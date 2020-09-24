FROM quay.io/azavea/raster-vision:pytorch-b72297b

RUN pip3 install --upgrade pystac==0.5.2

COPY sen1floods11_pipeline.py /workdir/
COPY usfimr_pipeline.py /workdir/
COPY default /root/.rastervision/
COPY multi-raster-source.diff /tmp/

RUN cd /opt/src && patch -p1 < /tmp/multi-raster-source.diff

CMD ["bash"]
