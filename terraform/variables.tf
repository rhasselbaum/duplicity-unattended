variable "project_id" {
  type        = string
  description = "Your google project ID."
}

variable "service_account_id" {
  type        = string
  description = "ID of the GCP service account to create for the machine doing backups (no spaces, only - or _ special characters)"
}

variable "service_account_friendly_name" {
  type        = string
  description = "The friendly namd of the GCP service account to create for the machine doing backups."
}

variable "bucket_name" {
  type        = string
  description = "A valid bucket name to use for your backups"
  default     = "duplicity-unattended"
}

variable "bucket_location" {
  type        = string
  description = "A valid location for your GCS bucket"
  default     = "us-central1"
}

variable "storage_class" {
  type        = string
  description = "The GCS storage class to use for backups."
  default     = "STANDARD"
}
