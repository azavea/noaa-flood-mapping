FROM quay.io/azavea/raster-vision:pytorch-b72297b

RUN pip3 install --upgrade pystac==0.5.2

COPY rv_stac_config.py /workdir/rv_stac_config.py
COPY default /root/.rastervision/default

CMD ["bash"]
