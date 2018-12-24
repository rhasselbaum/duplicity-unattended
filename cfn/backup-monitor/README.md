# duplicity-unattended-monitor

This is a Lambda function that checks an S3 bucket for [Duplicity](http://duplicity.nongnu.org/) backup sets. It sends an email if no recent backups are found for any path (prefix) containing at least one backup set. Before using, make sure the sender and recipient addresses/domains are [verified](https://docs.aws.amazon.com/ses/latest/DeveloperGuide/verify-addresses-and-domains.html) in AWS Simple Email Service (SES).

This SAM application is part of the [duplicity-unattended](https://github.com/rhasselbaum/duplicity-unattended) package, but can be used separately. See the home page for details.