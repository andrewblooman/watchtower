# ECS / Fargate Production Deployment

This document describes how to deploy the SRE Agent to AWS ECS Fargate in production.

## Overview

The SRE Agent is designed as a **short-lived ECS task** — one task is launched per deployment event. The task runs its investigation, stores results to S3, and the container remains up (serving the API + UI) until stopped or replaced.

```
┌─────────────────────────────────────────────────────────────┐
│  GitHub Actions                                              │
│    └─► EventBridge PutEvents (deployment metadata)          │
│          └─► EventBridge Rule                                │
│                └─► ECS RunTask (one task per commit)         │
│                      ├── Reads CloudWatch + ECS APIs         │
│                      ├── Calls Bedrock (Claude)              │
│                      ├── Writes cache to ephemeral storage   │
│                      └── Flushes artifacts to S3             │
└─────────────────────────────────────────────────────────────┘
```

---

## EventBridge Trigger Pattern

### GitHub Actions Workflow

Add a step to your GitHub Actions workflow to fire an EventBridge event on deployment:

```yaml
- name: Notify SRE Agent via EventBridge
  uses: aws-actions/aws-eventbridge-put-events@v1
  with:
    entries: |
      [
        {
          "Source": "github.deployment",
          "DetailType": "DeploymentStarted",
          "Detail": {
            "github_repo": "${{ github.repository }}",
            "commit_sha": "${{ github.sha }}",
            "service_name": "${{ env.SERVICE_NAME }}",
            "environment": "${{ env.DEPLOY_ENV }}"
          },
          "EventBusName": "sre-agent-bus"
        }
      ]
```

### EventBridge Rule → ECS Target

Create an EventBridge rule that matches `DeploymentStarted` events and triggers an ECS `RunTask`:

```json
{
  "Rule": "sre-agent-deployment-trigger",
  "EventPattern": {
    "source": ["github.deployment"],
    "detail-type": ["DeploymentStarted"]
  },
  "Targets": [{
    "Id": "sre-agent-task",
    "Arn": "arn:aws:ecs:us-east-1:ACCOUNT:cluster/sre-cluster",
    "RoleArn": "arn:aws:iam::ACCOUNT:role/eventbridge-ecs-role",
    "EcsParameters": {
      "TaskDefinitionArn": "arn:aws:ecs:us-east-1:ACCOUNT:task-definition/sre-agent",
      "LaunchType": "FARGATE",
      "NetworkConfiguration": { "...": "..." }
    },
    "InputTransformer": {
      "InputPathsMap": {
        "repo":    "$.detail.github_repo",
        "sha":     "$.detail.commit_sha",
        "service": "$.detail.service_name",
        "env":     "$.detail.environment"
      },
      "InputTemplate": "{\"containerOverrides\":[{\"name\":\"sre-agent\",\"environment\":[{\"name\":\"GITHUB_REPO\",\"value\":<repo>},{\"name\":\"COMMIT_SHA\",\"value\":<sha>},{\"name\":\"SERVICE_NAME\",\"value\":<service>},{\"name\":\"ENVIRONMENT\",\"value\":<env>}]}]}"
    }
  }]
}
```

---

## ECS Task Definition

```json
{
  "family": "sre-agent",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "executionRoleArn": "arn:aws:iam::ACCOUNT:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::ACCOUNT:role/sre-agent-task-role",
  "ephemeralStorage": { "sizeInGiB": 21 },
  "containerDefinitions": [{
    "name": "sre-agent",
    "image": "ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/sre-agent:latest",
    "portMappings": [{ "containerPort": 8000 }],
    "environment": [
      { "name": "S3_BUCKET",             "value": "sre-agent-investigations" },
      { "name": "S3_REGION",             "value": "us-east-1" },
      { "name": "BEDROCK_REGION",        "value": "us-east-1" },
      { "name": "BEDROCK_MODEL",         "value": "anthropic.claude-3-5-sonnet-20241022-v2:0" },
      { "name": "CACHE_DIR",             "value": "/data/cache" },
      { "name": "CACHE_TTL_HOURS",       "value": "6" }
    ],
    "logConfiguration": {
      "logDriver": "awslogs",
      "options": {
        "awslogs-group": "/ecs/sre-agent",
        "awslogs-region": "us-east-1",
        "awslogs-stream-prefix": "ecs"
      }
    },
    "healthCheck": {
      "command": ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://localhost:8000/healthz')\" 2>/dev/null || exit 1"],
      "interval": 30,
      "timeout": 5,
      "retries": 3
    }
  }]
}
```

> **Note:** `GITHUB_REPO`, `COMMIT_SHA`, `SERVICE_NAME`, and `ENVIRONMENT` are injected at runtime via the EventBridge `InputTransformer` container overrides — they are not hardcoded in the task definition.

---

## IAM Roles

### Task Role (`sre-agent-task-role`)

The task role grants the running container access to AWS services:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "S3Artifacts",
      "Effect": "Allow",
      "Action": ["s3:PutObject", "s3:GetObject", "s3:ListBucket"],
      "Resource": [
        "arn:aws:s3:::sre-agent-investigations",
        "arn:aws:s3:::sre-agent-investigations/*"
      ]
    },
    {
      "Sid": "BedrockInvoke",
      "Effect": "Allow",
      "Action": ["bedrock:InvokeModel"],
      "Resource": "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-5-sonnet-20241022-v2:0"
    },
    {
      "Sid": "CloudWatchLogs",
      "Effect": "Allow",
      "Action": [
        "logs:DescribeLogGroups",
        "logs:FilterLogEvents",
        "logs:GetLogEvents"
      ],
      "Resource": "*"
    },
    {
      "Sid": "CloudWatchMetrics",
      "Effect": "Allow",
      "Action": ["cloudwatch:GetMetricStatistics", "cloudwatch:GetMetricData"],
      "Resource": "*"
    },
    {
      "Sid": "ECSDescribe",
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeServices",
        "ecs:ListTasks",
        "ecs:DescribeTasks"
      ],
      "Resource": "*"
    }
  ]
}
```

### EventBridge → ECS Role (`eventbridge-ecs-role`)

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["ecs:RunTask"],
    "Resource": "arn:aws:ecs:us-east-1:ACCOUNT:task-definition/sre-agent:*"
  }, {
    "Effect": "Allow",
    "Action": ["iam:PassRole"],
    "Resource": [
      "arn:aws:iam::ACCOUNT:role/ecsTaskExecutionRole",
      "arn:aws:iam::ACCOUNT:role/sre-agent-task-role"
    ]
  }]
}
```

---

## Networking

- **VPC**: Place the ECS task in private subnets (no direct internet exposure).
- **NAT Gateway**: Required for the task to reach Bedrock, S3, CloudWatch, and ECR from private subnets.
- **Security Group**: Allow inbound port `8000` from your ALB or VPN only.
- **ALB (optional)**: If you want the dashboard UI accessible, put an ALB in front of port `8000`. Because the task is short-lived, the ALB target group should use IP target type and deregister on task stop.

---

## S3 Bucket Setup

```bash
aws s3api create-bucket \
  --bucket sre-agent-investigations \
  --region us-east-1

# Enable versioning (recommended for audit trail)
aws s3api put-bucket-versioning \
  --bucket sre-agent-investigations \
  --versioning-configuration Status=Enabled

# Lifecycle: expire investigation data after 90 days
aws s3api put-bucket-lifecycle-configuration \
  --bucket sre-agent-investigations \
  --lifecycle-configuration '{
    "Rules": [{
      "ID": "expire-investigations",
      "Status": "Enabled",
      "Filter": {"Prefix": "investigations/"},
      "Expiration": {"Days": 90}
    }]
  }'
```

---

## Secrets Management

Do **not** set `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` in the task definition. The task role provides credentials automatically via the ECS container agent (IMDSv2).

For any additional secrets (e.g. third-party API keys), use AWS Secrets Manager and reference them in the task definition `secrets` field:

```json
"secrets": [
  {
    "name": "MY_SECRET",
    "valueFrom": "arn:aws:secretsmanager:us-east-1:ACCOUNT:secret:sre-agent/my-secret"
  }
]
```

---

## Local Development

For local development, `docker-compose.yml` substitutes:
- **S3** → LocalStack (`http://localstack:4566`)
- **Bedrock** → Not mocked by default; set `BEDROCK_ENDPOINT_URL` to a local mock if needed
- **EventBridge** → Env vars are set directly in `docker-compose.yml`

```bash
docker compose up --build
# Dashboard: http://localhost:8000
# LocalStack S3: http://localhost:4566
```
