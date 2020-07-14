from abc import ABC, abstractmethod
from os import listdir
from os.path import exists, isfile, join
from shutil import copyfile

import boto3
from google.cloud import storage


class Storage(ABC):
    @abstractmethod
    def ls(self, path):
        """ Yield generator with a list of absolute or relative string paths """
        pass

    @abstractmethod
    def download(self, path, target_filename):
        """ Place file at path at target_filename if target_filename does not exist"""
        blob = self.bucket.blob(path)
        blob.download_to_filename(target_filename)


class FileStorage(Storage):
    def ls(self, path):
        for f in listdir(path):
            if isfile(join(path, f)):
                yield f

    def download(self, path, target_filename):
        if not exists(target_filename):
            copyfile(path, target_filename)


class GoogleCloudStorage(Storage):
    def __init__(self, bucket_name):
        self.client = storage.Client()
        self.bucket = self.client.bucket(bucket_name)

    def ls(self, path):
        for blob in self.client.list_blobs(self.bucket, prefix=path):
            yield "https://storage.googleapis.com/{}/{}".format(
                self.bucket.name, blob.name
            )

    def download(self, path, target_filename):
        if not exists(target_filename):
            blob = self.bucket.blob(path)
            blob.download_to_filename(target_filename)


class S3Storage(Storage):
    def __init__(self, bucket_name):
        self.bucket_name = bucket_name

    def ls(self, prefix):
        client = boto3.client("s3")
        extra_args = {}
        while True:
            response = client.list_objects_v2(
                Bucket=self.bucket_name, Prefix=prefix, **extra_args
            )
            for obj in response["Contents"]:
                yield "s3://{}/{}".format(self.bucket_name, obj["Key"])
            if not response["IsTruncated"]:
                break
            extra_args["ContinuationToken"] = response["NextContinuationToken"]

    def download(self, path, target_filename):
        if not exists(target_filename):
            with open(target_filename, "wb") as f:
                bucket = boto3.resource("s3").Bucket(self.bucket_name)
                bucket.download_fileobj(path, f)
