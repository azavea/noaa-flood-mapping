FROM quay.io/azavea/raster-vision:pytorch-e361661

RUN pip3 install --upgrade pystac==0.5.2 && apt-get install -y nano

# Pipelines
COPY sen1floods11_pipeline.py /workdir/
COPY usfimr_vector_pipeline.py /workdir/
COPY usfimr_raster_pipeline.py /workdir/
COPY default /root/.rastervision/

CMD ["bash"]
