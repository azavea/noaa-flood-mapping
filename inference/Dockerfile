FROM quay.io/azavea/raster-vision:pytorch-45815af

RUN pip3 install --upgrade pystac==0.4.0

COPY rv_stac_config.py /workdir/rv_stac_config.py
COPY default /root/.rastervision/default

CMD ["bash"]
