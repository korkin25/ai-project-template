{{/*
Naming and labels.

The names are deliberately NOT prefixed with .Release.Name. One environment == one
namespace == one release of this chart, so the release name adds no uniqueness while it
does break every cross-reference a human writes by hand (Service DNS names, dashboards,
NetworkPolicy selectors, runbooks). The resource is called what the service is called.
*/}}

{{- define "@@PROJECT@@.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "@@PROJECT@@.fullname" -}}
{{- printf "%s" (include "@@PROJECT@@.name" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Full label set for metadata. `helm.sh/chart` carries the chart version, which after
packaging IS the released SemVer — so `kubectl get deploy -o wide --show-labels` answers
"what is running here?" without consulting the platform repo.
*/}}
{{- define "@@PROJECT@@.labels" -}}
app.kubernetes.io/name: {{ include "@@PROJECT@@.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end -}}

{{/*
Selector labels are a STRICT SUBSET of the labels above and must never include a version:
a Deployment's selector is immutable, so a version label here makes every upgrade fail with
"field is immutable" and forces a delete/recreate — an outage per release.
*/}}
{{- define "@@PROJECT@@.selectorLabels" -}}
app.kubernetes.io/name: {{ include "@@PROJECT@@.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}
