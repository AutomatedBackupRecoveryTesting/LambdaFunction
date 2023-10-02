# Revised lambda function code.

import json
import boto3

backup = boto3.client('backup')

def lambda_handler(event, context):
    print('Incoming Event:' + json.dumps(event))

    try:
        if event['Records'][0]['Sns']['Subject'] == 'Restore Test Status':
            print('No action required, DynamoDB table validation completed.')
            return
    except Exception as e:
        print(str(e))
        return

    job_type = event['Records'][0]['Sns']['Message'].split('.')[-1].split(' ')[1]

    try:
        if 'failed' in event['Records'][0]['Sns']['Message']:
            print('Something has failed. Please review the job in the AWS Backup console.')
            return 'Job ID:' + event['Records'][0]['Sns']['Message'].split('.')[-1].split(':')[1].strip()
        elif job_type == 'Backup':
            backup_job_id = event['Records'][0]['Sns']['Message'].split('.')[-1].split(':')[1].strip()
            backup_info = backup.describe_backup_job(
                BackupJobId=backup_job_id
            )
            # Get backup job details
            recovery_point_arn = backup_info['RecoveryPointArn']
            iam_role_arn = backup_info['IamRoleArn']
            backup_vault_name = backup_info['BackupVaultName']
            resource_type = backup_info['ResourceType']

            metadata = backup.get_recovery_point_restore_metadata(
                BackupVaultName=backup_vault_name,
                RecoveryPointArn=recovery_point_arn
            )

            # Determine resource type that was backed up and get corresponding metadata
            if resource_type == 'DynamoDB':
                dynamo_table_name = metadata['RestoreMetadata']['targetTableName']  # Retrieve DynamoDB metadata
                metadata['RestoreMetadata']['targetTableName'] = metadata['RestoreMetadata']['originalTableName'] + '-restore-test'

                # Add DynamoDB validation checks here
                validation_result = validate_dynamodb_table(dynamo_table_name)

                if validation_result:
                    print('DynamoDB table validation succeeded.')
                else:
                    print('DynamoDB table validation failed.')
                    # Customize to handle failure as needed
                    return

            # API call to start the restore job
            print('Starting the restore job')
            restore_request = backup.start_restore_job(
                RecoveryPointArn=recovery_point_arn,
                IamRoleArn=iam_role_arn,
                Metadata=metadata['RestoreMetadata']
            )

            print(json.dumps(restore_request))

            return
        elif job_type == 'Restore':
            restore_job_id = event['Records'][0]['Sns']['Message'].split('.')[-1].split(':')[1].strip()
            topic_arn = event['Records'][0]['Sns']['TopicArn']
            restore_info = backup.describe_restore_job(
                RestoreJobId=restore_job_id
            )
            resource_type = restore_info['CreatedResourceArn'].split(':')[2]

            print('Restore from the backup was successful. Deleting the newly created resource.')

            # Determine resource type that was restored and delete it to save cost
            if resource_type == 'dynamodb':
                dynamo = boto3.client('dynamodb')
                table_name = restore_info['CreatedResourceArn'].split(':')[5].split('/')[1]

                # Include recovery validation checks for DynamoDB here

                print('Deleting: ' + table_name)
                delete_request = dynamo.delete_table(
                    TableName=table_name
                )
            elif resource_type == 'ec2':
                # Include recovery validation checks for EC2 here if needed
                pass  # Replace with your code

            sns = boto3.client('sns')

            print('Sending final confirmation')
            # Send a final notification
            notify = sns.publish(
                TopicArn=topic_arn,
                Message=f'Restore {job_type} job completed successfully for {resource_type}.',
                Subject='Restore Test Status'
            )

            print(json.dumps(notify))

            return
    except Exception as e:
        print(str(e))
        return

def validate_dynamodb_table(table_name):
    dynamodb = boto3.client('dynamodb')

    try:
        response = dynamodb.describe_table(
            TableName=table_name
        )

        table_status = response['Table']['TableStatus']

        # Check if the table is in an active state
        if table_status == 'ACTIVE':
            return True
        else:
            print(f'DynamoDB table {table_name} is not in an active state. Status: {table_status}')
            return False

    except dynamodb.exceptions.ResourceNotFoundException:
        print(f'DynamoDB table {table_name} not found.')
        return False
