# LOGGING_LEVEL = 'WARN'
# LOGGING_LEVEL = 'DEBUG'
LOGGING_LEVEL = "INFO"
LOG_STDOUT = True
# SQLALCHEMY Configuration
SQLALCHEMY_URL = "postgresql://template:TEMPLATE@localhost:5432/template"
SQLALCHEMY_ECHO = False
# REDIS Configuration
REDIS_HOST = "localhost"
REDIS_PORT = 6379
# Kafka Configuration
KAFKA_BROKER = "kafka:9092"
SCHEMA_REGISTRY_URL = "http://schema-registry:8081"
# TEMPLATE AVRO Schema Parameters
TEMPLATE_INPUT_SCHEMA = "TEMPLATEInputSchema"
TEMPLATE_INPUT_TOPIC = "TEMPLATEInput"
TEMPLATE_OUTPUT_SCHEMA = "TEMPLATEOutputSchema"
TEMPLATE_OUTPUT_TOPIC = "TEMPLATEOutput"
# S3 Configuration
S3_PROVIDERS = ["AWS", "MINIO"]
# AWS Configuration
AWS_ACCESS_KEY_ID = "CHANGEME"
AWS_SECRET_ACCESS_KEY = "SECRETS"
AWS_DEFAULT_REGION = "us-east-1"
PROFILE_NAME = "SESSION_PROFILE"
AWS_BUCKET_NAME = "BUCKETNAME"
AWS_BUCKET_ARN = "BUCKETARN"
# MINIO Configuration
MINIO_ACCESS_KEY_ID = "admin"
MINIO_SECRET_ACCESS_KEY = "supersecret"
MINIO_BUCKET_NAME = "scix-TEMPLATE"
MINIO_S3_URL = "http://minio:9000"
