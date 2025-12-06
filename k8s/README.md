# Kubernetes Deployment Guide for Notification Service

This guide covers deploying the HRMS Notification Service with a hybrid email system using **Amazon SES as the primary provider** and **Gmail SMTP as the fallback** in a Kubernetes environment.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Prerequisites](#prerequisites)
- [Configuration Options](#configuration-options)
- [Deployment Steps](#deployment-steps)
- [AWS IAM Setup](#aws-iam-setup)
- [Verifying Email Addresses in SES](#verifying-email-addresses-in-ses)
- [Environment Variables](#environment-variables)
- [Health Checks](#health-checks)
- [Monitoring and Troubleshooting](#monitoring-and-troubleshooting)

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    Notification Service                          │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              Hybrid Email Service                        │    │
│  │  ┌─────────────────┐      ┌─────────────────────────┐   │    │
│  │  │   SES Provider  │─────▶│  Amazon SES (Primary)   │   │    │
│  │  │   (Primary)     │      │  - High deliverability  │   │    │
│  │  └────────┬────────┘      │  - Scalable             │   │    │
│  │           │               │  - Cost effective       │   │    │
│  │           │ (on failure)  └─────────────────────────┘   │    │
│  │           ▼                                              │    │
│  │  ┌─────────────────┐      ┌─────────────────────────┐   │    │
│  │  │  SMTP Provider  │─────▶│  Gmail SMTP (Fallback)  │   │    │
│  │  │   (Fallback)    │      │  - Reliable backup      │   │    │
│  │  └─────────────────┘      │  - Easy setup           │   │    │
│  │                           └─────────────────────────┘   │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              Jinja2 Template Service                     │    │
│  │  - system_welcome.html                                   │    │
│  │  - generic_notifications.html                            │    │
│  │  - generic_reminder.html                                 │    │
│  │  - generic_congratulations.html                          │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

### How It Works

1. **Template Rendering**: All email templates are rendered using Jinja2, producing identical HTML regardless of the email provider used.

2. **Primary Provider (SES)**: When an email is sent, the service first attempts to send via Amazon SES.

3. **Automatic Fallback**: If SES fails (after configurable retries), the service automatically falls back to Gmail SMTP.

4. **Unified API**: Your application code doesn't need to change - the same API works with both providers.

## Prerequisites

- Kubernetes cluster (EKS, GKE, AKS, or self-managed)
- `kubectl` configured with cluster access
- AWS account with SES access (for primary provider)
- Gmail account with App Password (for fallback)
- Docker registry access for your container images

## Configuration Options

The `EMAIL_PROVIDER` setting controls the behavior:

| Value    | Description                                      |
|----------|--------------------------------------------------|
| `hybrid` | Use SES as primary with Gmail SMTP as fallback   |
| `ses`    | Use only Amazon SES                              |
| `smtp`   | Use only Gmail SMTP (legacy behavior)            |

## Deployment Steps

### 1. Create the Namespace

```bash
kubectl create namespace hrms
```

### 2. Create Secrets

**Option A: Using kubectl (recommended for initial setup)**

```bash
kubectl create secret generic notification-service-secrets \
  --namespace=hrms \
  --from-literal=aws-access-key-id='YOUR_AWS_ACCESS_KEY' \
  --from-literal=aws-secret-access-key='YOUR_AWS_SECRET_KEY' \
  --from-literal=ses-sender-email='noreply@yourdomain.com' \
  --from-literal=ses-configuration-set='' \
  --from-literal=smtp-user='your-gmail@gmail.com' \
  --from-literal=smtp-app-password='your-app-password' \
  --from-literal=db-user='hrms_user' \
  --from-literal=db-password='your-db-password' \
  --from-literal=asgardeo-org='your-org' \
  --from-literal=asgardeo-client-id='your-client-id'
```

**Option B: Using YAML file (with sealed-secrets or SOPS)**

```bash
kubectl apply -f secrets.yaml
```

### 3. Apply ConfigMap

```bash
kubectl apply -f configmap.yaml
```

### 4. Create ServiceAccount (for IRSA)

If using EKS with IAM Roles for Service Accounts:

```bash
kubectl apply -f secrets.yaml  # Contains ServiceAccount definition
```

### 5. Deploy the Application

```bash
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
```

### 6. Verify Deployment

```bash
# Check deployment status
kubectl get deployments -n hrms

# Check pods
kubectl get pods -n hrms -l app=notification-service

# Check logs
kubectl logs -n hrms -l app=notification-service --tail=100

# Check service
kubectl get svc -n hrms notification-service
```

## AWS IAM Setup

### Option 1: IAM Roles for Service Accounts (IRSA) - Recommended for EKS

1. **Create an IAM policy** using `iam-policy.json`:

```bash
aws iam create-policy \
  --policy-name NotificationServiceSESPolicy \
  --policy-document file://iam-policy.json
```

2. **Create an IAM role** with OIDC trust relationship:

```bash
eksctl create iamserviceaccount \
  --cluster=your-cluster-name \
  --namespace=hrms \
  --name=notification-service-sa \
  --attach-policy-arn=arn:aws:iam::ACCOUNT_ID:policy/NotificationServiceSESPolicy \
  --approve
```

3. **Update the ServiceAccount** in `secrets.yaml` with the role ARN:

```yaml
annotations:
  eks.amazonaws.com/role-arn: arn:aws:iam::ACCOUNT_ID:role/notification-service-ses-role
```

### Option 2: Static Credentials

If not using IRSA, create an IAM user with the policy from `iam-policy.json` and use the access key/secret in the Kubernetes secret.

## Verifying Email Addresses in SES

### Sandbox Mode (Development)

In SES sandbox mode, you must verify both sender and recipient email addresses:

```bash
# Verify sender email
aws ses verify-email-identity --email-address noreply@yourdomain.com

# Verify recipient emails (only needed in sandbox)
aws ses verify-email-identity --email-address recipient@example.com
```

### Production Mode

Request production access to send to any recipient:

1. Go to AWS SES Console → Account Dashboard
2. Click "Request production access"
3. Fill out the request form with your use case

### Verifying a Domain (Recommended)

```bash
aws ses verify-domain-identity --domain yourdomain.com
```

Then add the DKIM records to your DNS.

## Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `EMAIL_PROVIDER` | Email provider mode: `ses`, `smtp`, `hybrid` | `hybrid` | No |
| `AWS_REGION` | AWS region for SES | `us-east-1` | No |
| `AWS_ACCESS_KEY_ID` | AWS access key (if not using IRSA) | - | Conditional |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key (if not using IRSA) | - | Conditional |
| `SES_SENDER_EMAIL` | Verified sender email in SES | - | Yes (for SES) |
| `SES_CONFIGURATION_SET` | SES configuration set name | - | No |
| `SES_ENABLED` | Enable SES provider | `true` | No |
| `SMTP_HOST` | Gmail SMTP host | `smtp.gmail.com` | No |
| `SMTP_PORT` | Gmail SMTP port | `465` | No |
| `SMTP_USER` | Gmail address | - | Yes (for SMTP) |
| `SMTP_APP_PASSWORD` | Gmail app password | - | Yes (for SMTP) |
| `SMTP_ENABLED` | Enable SMTP provider | `true` | No |
| `ENABLE_FALLBACK` | Enable fallback to secondary provider | `true` | No |
| `FALLBACK_RETRY_COUNT` | Retries before fallback | `2` | No |

## Health Checks

The service exposes health endpoints:

### Basic Health Check

```bash
curl http://notification-service.hrms.svc.cluster.local/health
```

### Email Provider Health (via API)

```python
# Example response from health check endpoint
{
  "primary_provider": "ses",
  "fallback_provider": "smtp",
  "fallback_enabled": true,
  "providers": {
    "ses": {
      "status": "healthy",
      "configured": true,
      "quota": {
        "max_24_hour_send": 50000,
        "max_send_rate": 14,
        "sent_last_24_hours": 150
      }
    },
    "smtp": {
      "status": "configured",
      "configured": true,
      "host": "smtp.gmail.com",
      "port": 465
    }
  }
}
```

## Monitoring and Troubleshooting

### Common Issues

#### 1. SES Sending Fails with "Email address not verified"

**Cause**: In sandbox mode, recipient addresses must be verified.

**Solution**: Either verify the recipient or request production access.

#### 2. Gmail SMTP Authentication Failed

**Cause**: Incorrect app password or 2FA not enabled.

**Solution**:
1. Enable 2-Factor Authentication on your Google account
2. Generate an App Password at https://myaccount.google.com/apppasswords
3. Use the 16-character app password (not your regular password)

#### 3. IRSA Not Working

**Cause**: ServiceAccount not properly annotated or OIDC not configured.

**Solution**:
```bash
# Verify ServiceAccount annotation
kubectl get sa notification-service-sa -n hrms -o yaml

# Check if pods can assume the role
kubectl exec -it <pod-name> -n hrms -- env | grep AWS
```

#### 4. Templates Not Rendering

**Cause**: Template files not found or Jinja2 syntax error.

**Solution**:
```bash
# Check if templates are mounted
kubectl exec -it <pod-name> -n hrms -- ls -la /app/app/templates/
```

### Viewing Logs

```bash
# Stream logs from all pods
kubectl logs -n hrms -l app=notification-service -f

# Get logs from a specific pod
kubectl logs -n hrms <pod-name>

# Get previous container logs (if crashed)
kubectl logs -n hrms <pod-name> --previous
```

### Checking SES Metrics

```bash
# Get sending statistics
aws ses get-send-statistics

# Get send quota
aws ses get-send-quota
```

### Testing Email Sending

```bash
# Port-forward to test locally
kubectl port-forward -n hrms svc/notification-service 8000:80

# Send a test email
curl -X POST http://localhost:8000/api/v1/notifications/email/basic \
  -H "Content-Type: application/json" \
  -d '{
    "email_from": "HRMS",
    "recipient_email": "test@example.com",
    "subject": "Test Email",
    "body": "This is a test email from the notification service."
  }'
```

## Scaling Considerations

### Horizontal Pod Autoscaler

The deployment includes an HPA that scales based on CPU and memory:

```yaml
minReplicas: 2
maxReplicas: 10
targetCPUUtilization: 70%
targetMemoryUtilization: 80%
```

### SES Rate Limits

- Sandbox: 1 email/second, 200 emails/day
- Production: Varies by account (typically starts at 14 emails/second)

Monitor your quota:
```bash
aws ses get-send-quota
```

### Gmail SMTP Limits

- 500 emails/day for free accounts
- 2,000 emails/day for Google Workspace

Consider these limits when configuring fallback behavior.

## Security Best Practices

1. **Use IRSA** instead of static credentials when possible
2. **Rotate credentials** regularly
3. **Use Sealed Secrets** or **External Secrets Operator** for secrets management
4. **Enable Network Policies** (included in service.yaml)
5. **Use TLS** for all external communication
6. **Limit SES permissions** to only required actions

## Support

For issues with this deployment:

1. Check the [troubleshooting section](#monitoring-and-troubleshooting)
2. Review pod logs
3. Verify all secrets are correctly configured
4. Check AWS SES console for sending statistics and errors