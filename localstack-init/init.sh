#!/bin/sh
# Runs automatically when LocalStack is ready.
# Creates the S3 bucket used by the SRE agent for local development.
echo "[localstack-init] Creating S3 bucket: sre-agent-investigations"
awslocal s3 mb s3://sre-agent-investigations
echo "[localstack-init] Done."
