import datetime
import logging as logger

import parser.models as models

logger.basicConfig(level=logger.DEBUG)


def write_status_redis(redis_instance, status):
    logger.debug("Publishing status: {}".format(status))
    redis_instance.publish("PARSER_statuses", status)


def get_job_status_by_record_id(cls, record_ids, only_status=None):
    """
    Return all updates with record_id
    """
    with cls.session_scope() as session:
        status = None
        logger.info("Opening Session")
        for record_id in record_ids:
            if only_status:
                record_db = (
                    session.query(models.gRPC_status)
                    .filter(models.gRPC_status.record_id == record_id)
                    .filter_by(status=only_status)
                    .first()
                )
            else:
                record_db = (
                    session.query(models.gRPC_status)
                    .filter(models.gRPC_status.record_id == record_id)
                    .first()
                )
            if record_db:
                status = record_db.status
                logger.info("{} has status: {}".format(record_db.record_id, status))

    return status


def _get_job_by_record_id(session, record_id, only_status=None):
    """
    Return all updates with record_id internal function
    """
    logger.info("Opening Session")

    if only_status:
        record_db = (
            session.query(models.gRPC_status)
            .filter(models.gRPC_status.record_id == record_id)
            .filter_by(status=only_status)
            .first()
        )
    else:
        record_db = (
            session.query(models.gRPC_status)
            .filter(models.gRPC_status.record_id == record_id)
            .first()
        )
    if record_db:
        logger.info("Found record: {}".format(record_db.record_id))
    return record_db


def write_job_status(cls, job_request, only_status=None):
    """
    Write new status for job to db
    """
    with cls.session_scope() as session:
        job_status = models.gRPC_status()
        job_status.record_id = job_request.get("record_id")
        job_status.job_request = job_request.get("task")
        job_status.status = job_request.get("status")
        job_status.date_added = datetime.datetime.now()
        job_status.date_of_last_attempt = job_status.date_added
        session.add(job_status)
        session.commit()
    return True


def update_job_status(cls, record_id, status=None):
    """
    Update status for job previously written to db
    """
    updated = False
    with cls.session_scope() as session:
        job_status = _get_job_by_record_id(session, record_id)
        if job_status:
            job_status.status = status
            job_status.date_of_last_attempt = datetime.datetime.now()
            if status == "Success":
                job_status.date_of_last_success = job_status.date_of_last_attempt
            session.add(job_status)
            session.commit()
            updated = True
    return updated


def write_parser_record(cls, record_id, date, s3_key, parsed_metadata, source):
    """
    Write harvested record to db.
    """
    success = False
    with cls.session_scope() as session:
        try:
            PARSER_record = models.PARSER_record()
            PARSER_record.id = record_id
            PARSER_record.s3_key = s3_key
            PARSER_record.parsed_data = parsed_metadata
            PARSER_record.date_created = date
            PARSER_record.date_modified = date
            PARSER_record.source = source
            session.add(PARSER_record)
            session.commit()
            success = True

        except Exception as e:
            cls.logger.exception("Failed to write record {}.".format(record_id))
            raise e
    return success


def update_parser_record_metadata(cls, record_id, date, parsed_metadata):
    """
    Write harvested record to db.
    """
    updated = False
    with cls.session_scope() as session:
        try:
            record_db = get_parser_record(session, record_id)
            if record_db:
                PARSER_record = models.PARSER_record()
                PARSER_record.id = record_db.record_id
                PARSER_record.s3_key = record_db.s3_key
                PARSER_record.parsed_data = parsed_metadata
                PARSER_record.date_created = record_db.date_created
                PARSER_record.date_modified = date
                PARSER_record.source = record_db.source
                session.add(PARSER_record)
                session.commit()
                updated = True
        except Exception as e:
            cls.logger.exception("Failed to write record {}.".format(record_id))
            raise e

    return updated


def get_parser_record(session, record_id):
    """
    Return record with UUID: record_id
    """
    record_db = (
        session.query(models.PARSER_record).filter(models.PARSER_record.id == record_id).first()
    )
    return record_db
