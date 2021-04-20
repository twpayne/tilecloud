import logging
from typing import Any, Optional

import boto3
import botocore.config
import botocore.exceptions

from tilecloud import Tile, TileStore
from tilecloud.layout.template import TemplateTileLayout

logger = logging.getLogger(__name__)
CLIENT_TIMEOUT = 60


class S3TileStore(TileStore):
    """Tiles stored in Amazon S3"""

    def __init__(
        self,
        bucket: str,
        tilelayout: TemplateTileLayout,
        dry_run: bool = False,
        s3_host: Optional[Any] = None,
        cache_control: Optional[Any] = None,
        **kwargs: Any,
    ) -> None:
        self._s3_host = s3_host
        self._client = None
        self.bucket = bucket
        self.tilelayout = tilelayout
        self.dry_run = dry_run
        self.cache_control = cache_control
        TileStore.__init__(self, **kwargs)

    def __contains__(self, tile):
        if not tile:
            return False
        key_name = self.tilelayout.filename(tile.tilecoord, tile.metadata)
        try:
            self.client.head_object(Bucket=self.bucket, Key=key_name)
            return True
        except botocore.exceptions.ClientError as exc:
            if _get_status(exc) == 404:
                return False
            else:
                raise

    def delete_one(self, tile):
        try:
            key_name = self.tilelayout.filename(tile.tilecoord, tile.metadata)
            if not self.dry_run:
                self.client.delete_object(Bucket=self.bucket, Key=key_name)
        except botocore.exceptions.ClientError as exc:
            tile.error = exc
        return tile

    def get_one(self, tile):
        key_name = self.tilelayout.filename(tile.tilecoord, tile.metadata)
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=key_name)
            tile.data = response["Body"].read()
            tile.content_encoding = response.get("ContentEncoding")
            tile.content_type = response.get("ContentType")
        except botocore.exceptions.ClientError as exc:
            if _get_status(exc) == 404:
                return None
            else:
                tile.error = exc
        return tile

    def list(self):
        prefix = getattr(self.tilelayout, "prefix", "")
        for s3_key in self.client.list_objects(Bucket=self.bucket, Prefix=prefix):
            try:
                tilecoord = self.tilelayout.tilecoord(s3_key["Key"])
            except ValueError:
                continue
            yield Tile(tilecoord)

    def put_one(self, tile):
        assert tile.data is not None
        key_name = self.tilelayout.filename(tile.tilecoord, tile.metadata)
        args = {}
        if tile.content_encoding is not None:
            args["ContentEncoding"] = tile.content_encoding
        if tile.content_type is not None:
            args["ContentType"] = tile.content_type
        if self.cache_control is not None:
            args["CacheControl"] = self.cache_control
        if not self.dry_run:
            try:
                self.client.put_object(
                    ACL="public-read", Body=tile.data, Key=key_name, Bucket=self.bucket, **args
                )
            except botocore.exceptions.ClientError as exc:
                tile.error = exc
        return tile

    @property
    def client(self):
        if self._client is None:
            self._client = get_client(self._s3_host)
        return self._client


def _get_status(s3_client_exception):
    return s3_client_exception.response["ResponseMetadata"]["HTTPStatusCode"]


def get_client(s3_host):
    config = botocore.config.Config(connect_timeout=CLIENT_TIMEOUT, read_timeout=CLIENT_TIMEOUT)
    return boto3.client(
        "s3", endpoint_url=("https://%s/" % s3_host) if s3_host is not None else None, config=config
    )
