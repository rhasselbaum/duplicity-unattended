import os
import re
from datetime import datetime, date, timedelta
import boto3


def _find_last_dates_by_prefix(bucket_name):
    """Find the most recent backup set dates for each key prefix.

    :param bucket_name: Name of the bucket to be searched.
    :return: A dict of key prefixes (paths) to date objects representing the most recent backup dates.
    """
    # Pattern that matches a manifest key and captures the end date.
    manifest_pattern = re.compile(r'.*\.(\d{8})T\d{6}Z\.manifest.gpg')
    result = dict()
    for obj in boto3.resource('s3').Bucket(bucket_name).objects.all():
        prefix, basename = os.path.split(obj.key)
        match = manifest_pattern.fullmatch(basename)
        if match:
            # The object appears to be a Duplicity manifest.
            end_date = datetime.strptime(match.group(1), '%Y%m%d').date()
            if end_date > result.get(prefix, date(1970, 1, 1)):
                result[prefix] = end_date
    return result


def _send_mail(sender, recipient, subject, body):
    """Send an email.

    :param sender: The sender address.
    :param recipient: The recipient address.
    :param subject: Subject.
    :param body: Plain text body.
    :return: The sent message ID.
    """
    ses = boto3.client('ses')
    charset = 'utf-8'
    response = ses.send_email(
        Destination={
            'ToAddresses': [recipient],
        },
        Message={
            'Body': {
                'Text': {
                    'Charset': charset,
                    'Data': body,
                },
            },
            'Subject': {
                'Charset': charset,
                'Data': subject,
            },
        },
        Source=sender,
    )
    return response['MessageId']


def _format_dates_by_prefix(bucket_name, dates_by_prefix):
    """Return a string containing backup date for each prefix separated by newlines.

    Example:
        2018-01-01: bucket_name/some/prefix
        2018-02-01: bucket_name/another/prefix

    :param bucket_name: Name of the bucket.
    :param dates_by_prefix: Dict of prefixes mapped to dates.
    :return: Formatted string.
    """
    lines = [f'* {backup_date.isoformat()}: {bucket_name}/{prefix}' for prefix, backup_date in dates_by_prefix.items()]
    return '\n'.join(lines) + '\n'


def lambda_handler(event, context):
    """Send email if any backups have grown stale.

    Find all backups sets in a bucket. For each unique path (prefix) containing at least one backup set, find the most
    recent manifest. If it is older than than today - MAX_AGE_DAYS, the backup is considered stale. This function sends
    an email notification if there are any stale backups found at the end of this process.

    Required env variables:
        MAX_AGE_DAYS: Maximum age in days of a backup set in a set before the backup is considered stale.
        BUCKET_NAME: The bucket name to check for backups.
        SENDER_ADDR: Sender email address.
        RECIPIENT_ADDR: Recipient email address.

    :param event: If the event key 'testEmail' exists, an email is sent even if no stale backups are found.
      Otherwise, the event is not used.
    :param context: Not used.
    :return: Message ID if an email was sent. Otherwise, None.
    """
    # Check inputs.
    bucket_name = os.environ['BUCKET_NAME']
    sender = os.environ['SENDER_ADDR']
    recipient = os.environ['RECIPIENT_ADDR']
    if not (bucket_name and sender and recipient and os.environ['MAX_AGE_DAYS']):
        raise ValueError('Missing required env variable.')
    max_age_days = int(os.environ['MAX_AGE_DAYS'])
    if max_age_days < 1:
        raise ValueError('MAX_AGE_DAYS must be positive.')

    # Find latest backup dates for all prefixes.
    latest_date_by_prefix = _find_last_dates_by_prefix(bucket_name)
    if 'testEmail' in event:
        subject = f'Backup monitor results: {bucket_name}'
        msg = f'Most recent backups in S3 bucket {repr(bucket_name)}:\n' \
              + (_format_dates_by_prefix(bucket_name, latest_date_by_prefix)
                 if latest_date_by_prefix else 'There are no backups!')
        return _send_mail(sender, recipient, subject, msg)

    # Find all stale backups.
    max_age_delta = timedelta(days=max_age_days)
    today = date.today()
    stale_date_by_prefix = {prefix: end_date for prefix, end_date in latest_date_by_prefix.items()
                            if today - end_date > max_age_delta}

    if stale_date_by_prefix:
        # Missing recent backups for at least one prefix.
        subject = f'Missing recent backups: {bucket_name}'
        msg = f'The following locations have not been backed up in in over {max_age_days} day(s):\n' \
              + _format_dates_by_prefix(bucket_name, latest_date_by_prefix) \
              + '\nPlease check to make sure backups are working properly.'
        return _send_mail(sender, recipient, subject, msg)
