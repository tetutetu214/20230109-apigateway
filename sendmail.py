import boto3
import json
import os

sqs = boto3.resource('sqs')
s3 = boto3.resource('s3')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('mailaddress')
sns = boto3.client('sns')
snsarn = os.environ['SNSARN']

def lambda_handler(event, context):
  #SQSからメッセージ取得
  for rec in event['Records']:
    email = rec['body']
    bucket = rec['messageAttributes']['bucket']['stringValue']
    filename = rec['messageAttributes']['filename']['stringValue']
    username = rec['messageAttributes']['username']['stringValue']

    #S3 送信メール内容取得
    obj = s3.Object(bucket, filename)
    r = obj.get()
    maildata = r['Body'].read().decode('utf-8')
    data = maildata.split("\n", 3)
    subject =  data[0]
    body = data[2]

    #2重通知防止の仕組み
    #DynamoDB send済みとなるので1をUpdate ただしReturnでUpdate前を返す
    r = table.update_item(
      Key = {
        'email' : email
        },
        UpdateExpression = "set send=:val",
        ExpressionAttributeValues = {
          ':val' : 1
        },
        ReturnValues = 'UPDATED_OLD'
        )
    
    #条件分岐 未送信(Updateする前の UPDATED_OLD が 0) の場合SNS送信 
    if r['Attributes']['send'] == 0:
      params = {
      'TopicArn': snsarn,
      'Subject': subject,
      'Message': body
      }
      sns.publish(**params)
    else:
      print("Resend Skip")
    
