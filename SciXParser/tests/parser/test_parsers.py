import json
import os
from unittest import TestCase

import base
import boto3
import moto
import pytest
from confluent_kafka.avro import AvroProducer
from mock import patch
from SciXPipelineUtils import s3_methods, utils

from SciXParser.parser import db
from SciXParser.parser.parser import PARSER_APP
from tests.common.mockschemaregistryclient import MockSchemaRegistryClient


class TestParser(TestCase):
    def test_parser_task(self):
        mock_job_request = base.mock_job_request()
        url = "https://test.bucket.domain"
        with open("SciXParser/tests/stubdata/AVRO_schemas/ParserOutputSchema.avsc") as f:
            schema_str = f.read()
        with patch.dict(os.environ, {"MOTO_S3_CUSTOM_ENDPOINTS": url}):
            with moto.mock_s3() and base.base_utils.mock_multiple_targets(
                {
                    "get_schema": patch.object(
                        utils,
                        "get_schema",
                        return_value=schema_str,
                    )
                }
            ):
                mock_app = PARSER_APP(proj_home="SciXParser/tests/stubdata/")
                mock_app.schema_client = MockSchemaRegistryClient()
                mock_app._init_logger()
                producer = AvroProducer({}, schema_registry=mock_app.schema_client)
                mock_app.parser_task(mock_job_request, producer)
                self.assertEqual(
                    db.get_job_status_by_record_id(
                        mock_app, [mock_job_request.value()["record_id"]]
                    ).name,
                    "Success",
                )

    def test_parser_task_producer_failure(self):
        mock_job_request = base.mock_job_request()
        url = "https://test.bucket.domain"
        with open("SciXParser/tests/stubdata/AVRO_schemas/ParserOutputSchema.avsc") as f:
            schema_str = f.read()
        with patch.dict(os.environ, {"MOTO_S3_CUSTOM_ENDPOINTS": url}):
            with moto.mock_s3() and base.base_utils.mock_multiple_targets(
                {
                    "get_schema": patch.object(
                        utils,
                        "get_schema",
                        return_value=schema_str,
                    )
                }
            ):
                mock_app = PARSER_APP(proj_home="SciXParser/tests/stubdata/")
                mock_app.schema_client = MockSchemaRegistryClient()
                mock_app._init_logger()
                producer = (
                    base.bad_producer()
                )  # AvroProducer({}, schema_registry=mock_app.schema_client)
                with pytest.raises(ValueError):
                    mock_app.parser_task(mock_job_request, producer)
                self.assertEqual(
                    db.get_job_status_by_record_id(
                        mock_app, [mock_job_request.value()["record_id"]]
                    ).name,
                    "Error",
                )

    def test_parser_task_bad_source(self):
        mock_job_request = base.mock_job_request(source="trash")
        url = "https://test.bucket.domain"
        with open("SciXParser/tests/stubdata/AVRO_schemas/ParserOutputSchema.avsc") as f:
            schema_str = f.read()
        with patch.dict(os.environ, {"MOTO_S3_CUSTOM_ENDPOINTS": url}):
            with moto.mock_s3() and base.base_utils.mock_multiple_targets(
                {
                    "get_schema": patch.object(
                        utils,
                        "get_schema",
                        return_value=schema_str,
                    )
                }
            ):
                mock_app = PARSER_APP(proj_home="SciXParser/tests/stubdata/")
                mock_app.schema_client = MockSchemaRegistryClient()
                mock_app._init_logger()
                producer = AvroProducer({}, schema_registry=mock_app.schema_client)
                mock_app.parser_task(mock_job_request, producer)
                self.assertEqual(
                    db.get_job_status_by_record_id(
                        mock_app, [mock_job_request.value()["record_id"]]
                    ).name,
                    "Error",
                )

    @moto.mock_s3
    def test_reparse_task_alternate_s3(self):
        with open("SciXParser/tests/stubdata/arxiv_raw_xml_data.xml", "rb") as f:
            raw_record = f.read()
        mock_job_request = base.mock_reparse_job_request(force=False, resend=False)

        with open("SciXParser/tests/stubdata/AVRO_schemas/ParserOutputSchema.avsc") as f:
            schema_str = f.read()

        provider = "MINIO"
        url = "https://test.bucket.domain"
        mock_config = {
            "S3_PROVIDERS": [provider],
            str(provider) + "_BUCKET_NAME": "MINIOBUCKETNAME",
            str(provider) + "_S3_URL": url,
        }
        url = "https://test.bucket.domain"
        with patch.dict(os.environ, {"MOTO_S3_CUSTOM_ENDPOINTS": url}):
            with moto.mock_s3():
                conn = boto3.resource("s3")
                conn.create_bucket(Bucket="MINIOBUCKETNAME")
                buckets = s3_methods.load_s3_providers(mock_config)
                file_bytes = raw_record
                object_name = "/{}".format(mock_job_request.record_id)
                for producer in buckets:
                    buckets[producer].write_object_s3(
                        file_bytes=file_bytes, object_name=object_name
                    )
                with base.base_utils.mock_multiple_targets(
                    {
                        "get_schema": patch.object(
                            utils,
                            "get_schema",
                            return_value=schema_str,
                        )
                    }
                ):
                    return_value = base.mock_reparse_db_entry(
                        str(mock_job_request.record_id),
                        "/{}".format(mock_job_request.record_id),
                    )
                    mock_app = PARSER_APP(proj_home="SciXParser/tests/stubdata/")
                    mock_app.schema_client = MockSchemaRegistryClient()
                    mock_app._init_logger()
                    db.write_parser_record(
                        mock_app,
                        return_value.id,
                        return_value.date_created,
                        return_value.s3_key,
                        return_value.parsed_data,
                        return_value.source,
                    )
                    db.write_job_status(mock_app, mock_job_request.value())
                    producer = AvroProducer({}, schema_registry=mock_app.schema_client)
                    mock_app.parser_task(mock_job_request, producer)
                    self.assertEqual(
                        db.get_job_status_by_record_id(
                            mock_app, [mock_job_request.value()["record_id"]]
                        ).name,
                        "Success",
                    )

    @moto.mock_s3
    def test_reparse_task_alternate_s3_no_object(self):
        mock_job_request = base.mock_reparse_job_request(force=False, resend=False)

        with open("SciXParser/tests/stubdata/AVRO_schemas/ParserOutputSchema.avsc") as f:
            schema_str = f.read()

        url = "https://test.bucket.domain"
        with patch.dict(os.environ, {"MOTO_S3_CUSTOM_ENDPOINTS": url}):
            with moto.mock_s3():
                with base.base_utils.mock_multiple_targets(
                    {
                        "get_schema": patch.object(
                            utils,
                            "get_schema",
                            return_value=schema_str,
                        ),
                    }
                ):
                    mock_app = PARSER_APP(proj_home="SciXParser/tests/stubdata/")
                    mock_app.schema_client = MockSchemaRegistryClient()
                    mock_app._init_logger()
                    producer = AvroProducer({}, schema_registry=mock_app.schema_client)
                    return_value = base.mock_reparse_db_entry(
                        str(mock_job_request.record_id),
                        "/{}".format(mock_job_request.record_id),
                    )
                    db.write_parser_record(
                        mock_app,
                        return_value.id,
                        return_value.date_created,
                        return_value.s3_key,
                        return_value.parsed_data,
                        return_value.source,
                    )
                    db.write_job_status(mock_app, mock_job_request.value())
                    with pytest.raises(ValueError):
                        mock_app.parser_task(mock_job_request, producer)
                    self.assertEqual(
                        db.get_job_status_by_record_id(
                            mock_app, [mock_job_request.value()["record_id"]]
                        ).name,
                        "Error",
                    )

    @moto.mock_s3
    def test_reparse_task(self):
        mock_job_request = base.mock_reparse_job_request(force=False, resend=False)

        with open("SciXParser/tests/stubdata/arxiv_raw_xml_data.xml", "rb") as f:
            raw_record = f.read()

        with open("SciXParser/tests/stubdata/AVRO_schemas/ParserOutputSchema.avsc") as f:
            schema_str = f.read()

        mock_config = {"S3_PROVIDERS": ["AWS"], "AWS_BUCKET_NAME": "BUCKETNAME"}
        moto_fake = moto.mock_s3()
        moto_fake.start()
        conn = boto3.resource("s3")
        conn.create_bucket(Bucket="BUCKETNAME")
        buckets = s3_methods.load_s3_providers(mock_config)
        file_bytes = raw_record
        object_name = "/{}".format(mock_job_request.record_id)
        for producer in buckets:
            buckets[producer].write_object_s3(file_bytes=file_bytes, object_name=object_name)

        with base.base_utils.mock_multiple_targets(
            {
                "get_schema": patch.object(
                    utils,
                    "get_schema",
                    return_value=schema_str,
                ),
            }
        ):
            return_value = base.mock_reparse_db_entry(
                str(mock_job_request.record_id),
                "/{}".format(mock_job_request.record_id),
            )
            mock_app = PARSER_APP(proj_home="SciXParser/tests/stubdata/")
            mock_app.schema_client = MockSchemaRegistryClient()
            mock_app._init_logger()
            producer = AvroProducer({}, schema_registry=mock_app.schema_client)
            db.write_parser_record(
                mock_app,
                return_value.id,
                return_value.date_created,
                return_value.s3_key,
                return_value.parsed_data,
                return_value.source,
            )
            db.write_job_status(mock_app, mock_job_request.value())
            mock_app.parser_task(mock_job_request, producer)
            self.assertEqual(
                db.get_job_status_by_record_id(
                    mock_app, [mock_job_request.value()["record_id"]]
                ).name,
                "Success",
            )

        moto_fake.stop()

    @moto.mock_s3
    def test_reparse_task_no_change_in_parsed_record(self):
        mock_job_request = base.mock_reparse_job_request(force=False, resend=False)
        with open("SciXParser/tests/stubdata/arxiv_raw_xml_data.xml", "rb") as f:
            raw_record = f.read()

        with open("SciXParser/tests/stubdata/AVRO_schemas/ParserOutputSchema.avsc") as f:
            schema_str = f.read()

        with open("SciXParser/tests/stubdata/arxiv_parsed_data.json", "r") as f:
            parsed_record = json.load(f)

        mock_config = {"S3_PROVIDERS": ["AWS"], "AWS_BUCKET_NAME": "BUCKETNAME"}
        moto_fake = moto.mock_s3()
        moto_fake.start()
        conn = boto3.resource("s3")
        conn.create_bucket(Bucket="BUCKETNAME")
        buckets = s3_methods.load_s3_providers(mock_config)
        file_bytes = raw_record
        object_name = "/{}".format(mock_job_request.record_id)
        for producer in buckets:
            buckets[producer].write_object_s3(file_bytes=file_bytes, object_name=object_name)

        with base.base_utils.mock_multiple_targets(
            {
                "get_schema": patch.object(
                    utils,
                    "get_schema",
                    return_value=schema_str,
                ),
            }
        ):
            return_value = base.mock_reparse_db_entry(
                str(mock_job_request.record_id),
                "/{}".format(mock_job_request.record_id),
                parsed_record,
            )
            mock_app = PARSER_APP(proj_home="SciXParser/tests/stubdata/")
            mock_app.schema_client = MockSchemaRegistryClient()
            mock_app._init_logger()
            producer = AvroProducer({}, schema_registry=mock_app.schema_client)
            db.write_parser_record(
                mock_app,
                return_value.id,
                return_value.date_created,
                return_value.s3_key,
                return_value.parsed_data,
                return_value.source,
            )
            db.write_job_status(mock_app, mock_job_request.value())
            mock_app.parser_task(mock_job_request, producer)
            self.assertEqual(
                db.get_job_status_by_record_id(
                    mock_app, [mock_job_request.value()["record_id"]]
                ).name,
                "Unchanged",
            )
        moto_fake.stop()

    @moto.mock_s3
    def test_reparse_task_force(self):
        mock_job_request = base.mock_reparse_job_request(force=True, resend=False)
        mock_config = {"S3_PROVIDERS": ["AWS"], "AWS_BUCKET_NAME": "BUCKETNAME"}
        with open("SciXParser/tests/stubdata/arxiv_raw_xml_data.xml", "rb") as f:
            raw_record = f.read()

        moto_fake = moto.mock_s3()
        moto_fake.start()

        conn = boto3.resource("s3")
        conn.create_bucket(Bucket="BUCKETNAME")

        buckets = s3_methods.load_s3_providers(mock_config)
        file_bytes = raw_record
        object_name = "/{}".format(mock_job_request.record_id)

        for producer in buckets:
            buckets[producer].write_object_s3(file_bytes=file_bytes, object_name=object_name)

        with open("SciXParser/tests/stubdata/AVRO_schemas/ParserOutputSchema.avsc") as f:
            schema_str = f.read()
        with open("SciXParser/tests/stubdata/arxiv_parsed_data.json", "r") as f:
            parsed_record = json.load(f)

        with base.base_utils.mock_multiple_targets(
            {
                "get_schema": patch.object(
                    utils,
                    "get_schema",
                    return_value=schema_str,
                ),
            }
        ):
            return_value = base.mock_reparse_db_entry(
                str(mock_job_request.record_id),
                "/{}".format(mock_job_request.record_id),
                parsed_record,
            )
            mock_app = PARSER_APP(proj_home="SciXParser/tests/stubdata/")
            mock_app.schema_client = MockSchemaRegistryClient()
            mock_app._init_logger()
            producer = AvroProducer({}, schema_registry=mock_app.schema_client)
            db.write_parser_record(
                mock_app,
                return_value.id,
                return_value.date_created,
                return_value.s3_key,
                return_value.parsed_data,
                return_value.source,
            )

            db.write_job_status(mock_app, mock_job_request.value())
            mock_app.parser_task(mock_job_request, producer)
            self.assertEqual(
                db.get_job_status_by_record_id(
                    mock_app, [mock_job_request.value()["record_id"]]
                ).name,
                "Success",
            )

        moto_fake.stop()

    def test_reparse_task_resend(self):
        mock_job_request = base.mock_reparse_job_request(force=False, resend=True)
        with open("SciXParser/tests/stubdata/AVRO_schemas/ParserOutputSchema.avsc") as f:
            schema_str = f.read()
        with open("SciXParser/tests/stubdata/arxiv_parsed_data.json", "r") as f:
            parsed_record = json.load(f)

        with base.base_utils.mock_multiple_targets(
            {
                "get_schema": patch.object(
                    utils,
                    "get_schema",
                    return_value=schema_str,
                )
            }
        ):
            return_value = base.mock_reparse_db_entry(
                str(mock_job_request.record_id),
                "/{}".format(mock_job_request.record_id),
                parsed_record,
            )
            mock_app = PARSER_APP(proj_home="SciXParser/tests/stubdata/")
            mock_app.schema_client = MockSchemaRegistryClient()
            mock_app._init_logger()
            producer = AvroProducer({}, schema_registry=mock_app.schema_client)
            db.write_parser_record(
                mock_app,
                return_value.id,
                return_value.date_created,
                return_value.s3_key,
                return_value.parsed_data,
                return_value.source,
            )
            db.write_job_status(mock_app, mock_job_request.value())
            mock_app.parser_task(mock_job_request, producer)
            self.assertEqual(
                db.get_job_status_by_record_id(
                    mock_app, [mock_job_request.value()["record_id"]]
                ).name,
                "Success",
            )

    def test_reparse_task_resend_no_parsed_record(self):
        mock_job_request = base.mock_reparse_job_request(force=False, resend=True)
        with open("SciXParser/tests/stubdata/AVRO_schemas/ParserOutputSchema.avsc") as f:
            schema_str = f.read()

        with base.base_utils.mock_multiple_targets(
            {
                "get_schema": patch.object(
                    utils,
                    "get_schema",
                    return_value=schema_str,
                )
            }
        ):
            return_value = base.mock_reparse_db_entry(
                str(mock_job_request.record_id),
                "/{}".format(mock_job_request.record_id),
            )
            mock_app = PARSER_APP(proj_home="SciXParser/tests/stubdata/")
            mock_app.schema_client = MockSchemaRegistryClient()
            mock_app._init_logger()
            producer = AvroProducer({}, schema_registry=mock_app.schema_client)
            db.write_parser_record(
                mock_app,
                return_value.id,
                return_value.date_created,
                return_value.s3_key,
                return_value.parsed_data,
                return_value.source,
            )
            db.write_job_status(mock_app, mock_job_request.value())
            mock_app.parser_task(mock_job_request, producer)
            self.assertEqual(
                db.get_job_status_by_record_id(
                    mock_app, [mock_job_request.value()["record_id"]]
                ).name,
                "Error",
            )

    def test_reparse_task_resend_no_record_in_db(self):
        mock_job_request = base.mock_reparse_job_request(force=False, resend=True)
        with open("SciXParser/tests/stubdata/AVRO_schemas/ParserOutputSchema.avsc") as f:
            schema_str = f.read()

        with base.base_utils.mock_multiple_targets(
            {
                "get_schema": patch.object(
                    utils,
                    "get_schema",
                    return_value=schema_str,
                )
            }
        ):
            mock_app = PARSER_APP(proj_home="SciXParser/tests/stubdata/")
            mock_app.schema_client = MockSchemaRegistryClient()
            mock_app._init_logger()
            producer = AvroProducer({}, schema_registry=mock_app.schema_client)

            db.write_job_status(mock_app, mock_job_request.value())
            with pytest.raises(AttributeError):
                mock_app.parser_task(mock_job_request, producer)
            self.assertEqual(
                db.get_job_status_by_record_id(
                    mock_app, [mock_job_request.value()["record_id"]]
                ).name,
                "Error",
            )
