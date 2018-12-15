# duplicity-unattended

This is my script for unattended host backups using Duplicity that others might find useful. It is configurable through a YAML file, but opinionated in some ways:

1. Backups go to S3 using Standard-Infrequent Access storage class to save money.
1. Encryption and signing requires a GnuPG keypair with no passphrase. The key should be protected by filesystem permissions anyway so a passphrase just adds unnecessary complexity.
1. Time determines the interval between full backups.
1. Purging old backups happens automatically at the end (unless overridden). The script keeps the last N full backups.

## New host configuration

Here are the steps I generally follow to set up backups on a new host. I use separate keys, buckets, and AWS credentials so the compromise of any host doesn't affect others.

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
1. Make an off-host backup of the keypair in a secure location. I use my LastPass vault for this.
```
gpg --list-keys  # to get the key ID
gpg --armor --output pubkey.gpg --export <key_id>
gpg --armor --output privkey.gpg --export-secret-key <key_id>
```
1. Delete the exported key files from the filesystem.
1. Create S3 bucket for the host. Default settings are fine.
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
Replace `<bucket>` with the bucket name. Call the policy `S3Backup<host>` where `<host>` is the hostname.
1. Create IAM group with the same name as the policy and assign the policy to it.
1. Create IAM user for programmatic access. Call it `s3-backup-<host>` where `<host>` is the hostname. Add the user to the group. Don't forget to copy the access key ID and secret access key before completing the wizard.
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
1. Copy the sample `config.yaml` file to the same directory as the AWS credentials file. (Or you can put it somewhere else. Doesn't really matter.)
1. Customize the `config.yaml` file for the host.
1. Copy the `duplicity-unattended` script to a suitable `bin` directory and make sure it's runnable.
```
chmod +x duplicity-unattended
```
I usually clone the repo and add a symlink.
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