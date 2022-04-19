# Alternative Setup Instructions For GCP

Here are the steps you can take to set up a new host to backup to GCP.

Much of this is based on https://systemoverlord.com/2019/09/23/backing-up-to-google-cloud-storage-with-duplicity-and-service-accounts.html

## Set Up GCP Account
1. Create a Google Cloud account at [cloud.google.com](https://cloud.google.com)
1. Log into the [web console](https://console.cloud.google.com)
1. Create a project that will house your backups, and make yourself a "Storage Admin" on that project.

## Use Terraform To Set Up Cloud Storage And Service Account
The terraform included in this repository will create everything you need in your GCP project, including the cloud storage bucket, and all the required permissions for your host machine.

You should modify the contents of `terraform.tfvars` to match your needs before running the following:

```
cd ./terraform
terraform init
terraform apply
```

This will output a message from terraform about success/failure, and the path to your service account credentials file. You'll need this path in the next step.

## Set Up The Host
For the most part, you can follow the instructions given in the main [README](../README.md) under "Set up the host." There are a couple additional steps you should take first, though.
1. Install [gcs-oauth2-boto-plugin](https://github.com/GoogleCloudPlatform/gcs-oauth2-boto-plugin)
1. Install the gcloud sdk ([instructions](https://cloud.google.com/sdk/docs/install))
1. Run `gcloud init`
1. You will be prompted to log in to your Google Cloud account, which authenticates your machine so that we can run the Terraform
1. Run `gsutil config -e` (Enter the path to your service account credentials file when prompted)
1. The gsutil command given above will create a boto config file at `~/.boto`
1. Create the file `~/.config/boto/plugins/gcs.py`
1. Put the following contents in that file: `import gcs_oauth2_boto_plugin`
1. Put the following at the bottom of your `~/.boto` file

```
[Plugin]
plugin_directory = /home/{YOUR_USERNAME}/.config/boto/plugins
```

Continue to finish the relevant parts of the "Set up the host" section of the main [README](../README.md)
