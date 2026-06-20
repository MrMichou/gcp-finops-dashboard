{{/* Expand the name of the chart. */}}
{{- define "gcp-finops-dashboard.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/* Fully qualified app name. */}}
{{- define "gcp-finops-dashboard.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- $name := default .Chart.Name .Values.nameOverride -}}
{{- if contains $name .Release.Name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}
{{- end -}}

{{- define "gcp-finops-dashboard.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/* Common labels. */}}
{{- define "gcp-finops-dashboard.labels" -}}
helm.sh/chart: {{ include "gcp-finops-dashboard.chart" . }}
{{ include "gcp-finops-dashboard.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{- define "gcp-finops-dashboard.selectorLabels" -}}
app.kubernetes.io/name: {{ include "gcp-finops-dashboard.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{/* ServiceAccount name to use. */}}
{{- define "gcp-finops-dashboard.serviceAccountName" -}}
{{- if .Values.serviceAccount.create -}}
{{- default (include "gcp-finops-dashboard.fullname" .) .Values.serviceAccount.name -}}
{{- else -}}
{{- default "default" .Values.serviceAccount.name -}}
{{- end -}}
{{- end -}}

{{/* Name of the Secret holding the Slack webhook (chart-managed or existing). */}}
{{- define "gcp-finops-dashboard.slackSecretName" -}}
{{- if .Values.slack.existingSecret -}}
{{- .Values.slack.existingSecret -}}
{{- else -}}
{{- printf "%s-slack" (include "gcp-finops-dashboard.fullname" .) -}}
{{- end -}}
{{- end -}}

{{- define "gcp-finops-dashboard.slackSecretKey" -}}
{{- if .Values.slack.existingSecret -}}
{{- .Values.slack.existingSecretKey -}}
{{- else -}}
webhook
{{- end -}}
{{- end -}}

{{/* Whether Slack is enabled at all. */}}
{{- define "gcp-finops-dashboard.slackEnabled" -}}
{{- if or .Values.slack.webhook .Values.slack.existingSecret -}}true{{- end -}}
{{- end -}}
