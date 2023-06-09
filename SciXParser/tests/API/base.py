import contextlib
from datetime import datetime
from unittest import TestCase


class mock_gRPC_avro_msg:
    def value(self):
        return {
            "record_id": "206f479f-bb1e-49ff-96df-491d66769abc",
            "task": "REPARSE",
            "status": None,
            "persistence": None,
            "force": None,
            "resend": None,
        }

    def bitstream(self):
        return b"\x00H206f479f-bb1e-49ff-96df-491d66769abc\x00\x00\x00\x00\x00"


class mock_reparse_db_entry(object):
    def __init__(self, record_id, s3_key, record=None):
        self.id = record_id
        self.s3_key = s3_key
        self.date_created = datetime(2023, 6, 1)
        self.date_modifed = None
        self.parsed_data = record
        self.source = "ARXIV"


class base_utils(TestCase):
    @staticmethod
    @contextlib.contextmanager
    def mock_multiple_targets(mock_patches):
        """
        `mock_patches` is a list (or iterable) of mock.patch objects
        This is required when too many patches need to be applied in a nested
        `with` statement, since python has a hardcoded limit (~20).
        Based on: https://gist.github.com/msabramo/dffa53e4f29ec2e3682e
        """
        mocks = {}

        for mock_name, mock_patch in mock_patches.items():
            _mock = mock_patch.start()
            mocks[mock_name] = _mock

        yield mocks

        for mock_name, mock_patch in mock_patches.items():
            mock_patch.stop()
