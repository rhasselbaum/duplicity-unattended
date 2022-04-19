provider "google" {
  project = "home-server-347301"
}

resource "google_service_account" "my_service_account" {
  account_id   = var.service_account_id
  display_name = var.service_account_friendly_name
}

resource "google_service_account_key" "my_key" {
  service_account_id = google_service_account.my_service_account.name
}

resource "google_storage_bucket" "backups-bucket" {
  name                        = var.bucket_name
  location                    = var.bucket_location
  force_destroy               = true
  uniform_bucket_level_access = true
  storage_class = var.storage_class
}

data "google_iam_policy" "duplicity" {
  binding {
    role = "roles/storage.objectCreator"
    members = [
      "serviceAccount:${google_service_account.my_service_account.email}"
    ]
  }
  binding {
    role = "roles/storage.objectViewer"
    members = [
      "serviceAccount:${google_service_account.my_service_account.email}"
    ]
  }
}

resource "google_storage_bucket_iam_policy" "duplicity" {
  depends_on = [
    google_service_account.my_service_account
  ]
  bucket      = google_storage_bucket.backups-bucket.name
  policy_data = data.google_iam_policy.duplicity.policy_data
}

resource "local_file" "my_key_json" {
  content  = base64decode(google_service_account_key.my_key.private_key)
  filename = "${path.module}/${google_service_account.my_service_account.name}.json"
}

output "key_file" {
  value = local_file.my_key_json.filename
}
