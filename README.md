# LambdaFunction
Code for AWS Lambda function. 

lambda_function00.py contains the original code for the lambda function taken from AWS Well-Architectured Labs. lambda_function01.py contains the revised code, updating the instructions for how the lambda function should operate to include a validation check for the dynamoDB table, namely to make sure the status of the backup table is "ACTIVE" before it can be restored to the working AWS environment.
