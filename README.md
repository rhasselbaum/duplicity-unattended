# duplicity-unattended

This is my script for unattended host backups using Duplicity that others might find useful. It is configurable through a YAML file, but opinionated in some ways:

1. Backups go to S3 using Standard-Infrequent Access storage class to save money.
1. Encryption and signing requires a GnuPG keypair with no passphrase. The key should be protected by filesystem permissions anyway so a passphrase just adds unnecessary complexity.
1. Time determines the interval between full backups.
1. Purging old backups happens automatically at the end (unless overridden). The script keeps the last N full backups.

Run `duplicity-unattended --help` to see all options or just look at the code.

## What's inside the box?

1. `duplicity-unattended`: Script that runs unattended backups and purges stale backups.
1. `systemd/`: Directory containing sample systemd unit files you can customize to run the script periodically.
1. `cfn/host-bucket.yaml`: CloudFormation template to set up an S3 bucket and IAM permissions for a new host.
1. `cfn/backup-monitor`: CloudFormation (SAM) template and Lambda function to notify you if backups stop working.

You can use the script without systemd or CloudFormation if you prefer. They all work independently.

## Configuring new hosts

Here are the steps I generally follow to set up backups on a new host. I use separate keys, buckets, and AWS credentials so the compromise of any host doesn't affect others.

### Set up an S3 bucket

First, create an S3 bucket and IAM user/group/policy with read-write access to it. The included `cfn/host-bucket.yaml` CloudFormation template can do this for you automatically. To apply it:

1. Go to CloudFormation in the AWS console and click `Create Stack`.
1. Select the option to upload a template to S3 and pick the `cfn/host-bucket.yaml` template.
1. Fill in the stack name and bucket name. I suggest including the hostname in both for easy identification.
1. Accept remaining defaults and acknowledge the IAM resource creation warning.
1. Wait for stack setup to complete. If it fails, it's likely the S3 bucket name isn't unique. Delete the stack and try again with a different name.
1. Go to IAM in the AWS console and click on the new user. The user name is prefixed with the stack name so you can identify it that way.
1. Go to the `Security credentials` tab and click `Create access key`.
1. Copy the generated access key ID and secret key. You'll need them later.

Alternatively, you can create the S3 bucket and IAM resources manually. Here are the general steps. Modify as you see fit.

1. Create the S3 bucket. Default settings are fine.
1. Create IAM policy with the following permissions:
    ```
    {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": "s3:*",
                "Resource": [
                    "arn:aws:s3:::<bucket>/*",
                    "arn:aws:s3:::<bucket>"
                ]
            }
        ]
    }
    ```
    Replace `<bucket>` with the bucket name.
1. Create IAM group with the same name as the policy and assign the policy to it.
1. Create IAM user for programmatic access. Add the user to the group. Don't forget to copy the access key ID and secret access key at the end of the wizard.

### Set up the host

1. Install dependencies:
   * Duplicity
   * boto2 for Python 2
   * GnuPG
   * Python 3
   * PyYAML for Python 3
1. Create new RSA 4096 keypair as the user who will perform the backups. If you're backing up system directories, this probably needs to be root. Do **NOT** set a passphrase. Leave it blank.
    ```
    gpg --full-generate-key --pinentry loopback
    ```
1. Make an off-host backup of the keypair in a secure location. I use my LastPass vault for this. Don't skip this step or you'll be very sad when you realize the keys perished alongside the rest of your data, rendering your backups useless.
    ```
    gpg --list-keys  # to get the key ID
    gpg --armor --output pubkey.gpg --export <key_id>
    gpg --armor --output privkey.gpg --export-secret-key <key_id>
    ```
1. Delete the exported key files from the filesystem once they're secure.
1. Create a file on the host containing the AWS credentials.
    ```
    [Credentials]
    aws_access_key_id = <access_key_id>
    aws_secret_access_key = <secret_key>
    ```
    Replace `<access_key_id>` and `<secret_key>` with the IAM user credentials. Put it in a location appropriate for the backup user such as `/etc/duplicity-unattended/aws_credentials` or `~/.duplicity-unattended/aws_credentials`.
1. Make sure only the backup user can access the credentials file.
    ```
    chmod 600 aws_credentials
    ```
    Change ownership if needed.
1. Copy the `duplicity-unattended` script to a `bin` directory and make sure it's runnable.
    ```
    chmod +x duplicity-unattended
    ```
    I usually clone the repo to `/usr/local/share` and add a symlink in `usr/local/bin`.
1. Copy the sample `config.yaml` file to the same directory as the AWS credentials file. (Or you can put it somewhere else. Doesn't matter.)
1. Customize the `config.yaml` file for the host.
1. Do a dry-run backup as the backup user to validate most of the configuration:
    ```
    duplicity-unattended --config <config_file> --dry-run
    ```
    Replace `<config_file>` with the path to the YAML config file. Among other things, this will tell you how much would be backed up.
1. Do an initial backup as the backup user to make sure everything really works:
    ```
    duplicity-unattended --config <config_file>
    ```

## Schedule backups

How you schedule backups depends on your OS. I use systemd timers for this. See the `systemd` directory in this repository for sample unit files you can customize. You'll probably need to change `User`, `Group`, and `ExecStart` to match the user who performs the backups and the location of the `duplicity-unattended` script, respectively.

On Arch Linux and similar distros, drop these files into `/etc/systemd/system` and then enable and start the timer with:

```
sudo systemctl enable duplicity-unattended.timer
sudo systemctl start duplicity-unattended.timer
```

Make sure the timer is running:

```
sudo systemctl status duplicity-unattended.timer
```

And then run the backup once manually and check the output:

```
sudo systemctl start duplicity-unattended.service
sudo journalctl -u duplicity-unattended.service
```

You're done! Enjoy your backups.

## Set up monitoring

How do make sure backups keep working  in the future? You can set up systemd to email you if something goes wrong, but I prefer an independent mechanism. The `cfn/backup-monitor` directory contains a CloudFormation template (SAM template, actually) with a Lambda function that monitors a bucket for new backups and emails you if no recent backups have occurred. To set it up for a new host/bucket, follow these steps:

1. If you have not used AWS Simple Email Service (SES) before, follow the instructions to [verify the sender and recipient email addresses](https://docs.aws.amazon.com/ses/latest/DeveloperGuide/verify-email-addresses-procedure.html). See the [overview](https://docs.aws.amazon.com/ses/latest/DeveloperGuide/verify-addresses-and-domains.html) documentation for more information.
1. Go to [duplicity-unattended-monitor](https://serverlessrepo.aws.amazon.com/applications/arn:aws:serverlessrepo:us-east-1:829216590006:applications~duplicity-unattended-monitor) in the AWS Serverless Application Repository and click the `Deploy` button.
1. Review the template. (You wouldn't deploy a CloudFormation template into your AWS account without knowing what it does first, would you?)
1. Change the application/stack name. I suggest a name that includes the host or bucket for easy identification.
1. Fill in the remaining function parameters. Make sure the  email addresses exactly match the ones you verified in SES.
1. Click `Deploy` and wait for AWS to finish creating all the resources.

Now let's test it.

1. Click on the function link under `Resources`. This will take you to the Lambda console for the function.
1. Click the `Test` button in the upper-right.
1. Create a new test event with the following content:
   ```
   {"testEmail": true}
   ```
   Give it a name like `BackupMonitorTest` and click `Create`.
1. Now you should see the new named event next to the `Test` button. Click the `Test` button again.

If all goes well, you will get an email with a summary of the most recent backups found in the bucket.

From now on, the function will run once a day and email you only when there have been no recent backups for the number of days you specified. The function will look for recent backups in any S3 "folder" that contains at least one backup set from any time in the past. You can deploy additional stacks for each bucket you want to monitor.

If you prefer to deploy the CloudFormation template directly from source code instead of from the Serverless Application Repository, you can. The steps are roughly as follows:

1. Install [Pipenv](https://pipenv.readthedocs.io/en/latest/) for Python 3 if you don't already have it.
1. From the source repo directory, install the [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/index.html#lang/en_us) into a virtual environment:
   ```
   pipenv install --dev
   ```
1. Change to the `cfn/backup-monitor` directory.
1. Set up your AWS CLI credentials so SAM can read them (e.g. using `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` environment variables).
1. Run the SAM command to package the CloudFormation template and upload the Lambda function to S3:
   ```
   pipenv run sam package --s3-bucket <code_bucket> --output-template-file packaged.yaml
   ```
   where `<code_bucket>` is an S3 bucket to which the AWS CLI user has write access.
1. You can now use the CloudFormation AWS console or the AWS CLI to deploy the `packaged.yaml` stack template that SAM just created.

## Restoring from backup

Invoke `duplicity` directly to restore from a backup. The general procedure is as follows:

1. If restoring on a new host, import the GPG keypair from its secure backup location:
   ```
   gpg --import privkey.gpg
   ```
1. List the keys to get the key ID:
   ```
   gpg --list-keys
   ```
   Make a note of the ID (long hexadecimal number). You'll need it when you run the `duplicity` command later.
1. If you don't have a copy of the original AWS credentials file (e.g. it perished along with your data), create a new one. You can create a new access key from the IAM console following the same procedure as described above for setting up a new host. Don't forget to deactivate the old access key in the IAM console if you no longer need it.
1. Point Duplicity to the AWS credentials file by setting the `BOTO_CONFIG` environment variable. In `bash`, you'd run:
   ```
   export BOTO_CONFIG=<aws_credentials_file>
   ```
   Replace `<aws_credentials_file>` with the path to the file
1. Run `duplicity` from the command line to restore each source directory. You can browse the source directories by looking inside the S3 bucket in the AWS console. Here's a basic working restore command that restores a source directory to a new target directory called `restored`:
   ```
   mkdir restored
   duplicity --encrypt-sign-key <key_id> s3+http://<bucket>/<source_dir> restored
   ```
   Replace `<key_id>` with the GPG key ID, `<bucket>` with the S3 bucket name, and `<source_dir>` with the source directory name (S3 key prefix). You might be asked to provide a passphrase during the restore. Just hit ENTER.
