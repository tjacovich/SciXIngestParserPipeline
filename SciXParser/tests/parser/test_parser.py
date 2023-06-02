import os
from unittest import TestCase

import base
import moto
from confluent_kafka.avro import AvroProducer
from mock import patch

from parser.parser import PARSER_APP
from tests.common.mockschemaregistryclient import MockSchemaRegistryClient


@moto.mock_s3
class test_parser(TestCase):
    def test_parser_task(self):
        mock_job_request = base.mock_job_request
        url = "https://test.bucket.domain"
        with patch.dict(os.environ, {"MOTO_S3_CUSTOM_ENDPOINTS": url}):
            with moto.mock_s3():
                mock_app = PARSER_APP(proj_home="SciXParser/tests/stubdata/")
                mock_app.schema_client = MockSchemaRegistryClient()
                mock_app._init_logger()
                producer = AvroProducer({}, schema_registry=mock_app.schema_client)
                mock_app.logger.info("Test")
                mock_app.parser_task(mock_job_request(), producer)
