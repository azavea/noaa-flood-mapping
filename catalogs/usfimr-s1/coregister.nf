#!/usr/bin/env nextflow

params.s1_catalog_zip = "$baseDir/data/catalog.zip"
params.hand_catalog_gz = "$baseDir/data/hand-catalog.tar.gz"

process generateItems {

    input:
    path s1_catalog_zip from params.s1_catalog_zip
    path hand_catalog_gz from params.hand_catalog_gz

    output:
    path "./chips.csv" into chips_csv

    """
    unzip ${s1_catalog_zip}
    mkdir ./hand-catalog && tar -xzvf ${hand_catalog_gz} -C ./hand-catalog
    PYTHONPATH="${baseDir}" python ${baseDir}/bin/nf_gen_csvs.py \
        --s1-catalog ./catalog/catalog.json \
        --hand-catalog ./hand-catalog/catalog/collection.json
    """
}

process coregister {
    input:
    stdin chips_csv.splitText()

    """
    PYTHONPATH="${baseDir}" python ${baseDir}/bin/nf_coregister.py
    """
}
