import json
import boto3
from decouple import config
import uuid
# Initialize SQS client
sqs = boto3.client(
    'sqs',
    aws_access_key_id=config('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=config('AWS_SECRET_ACCESS_KEY'),
    region_name=config('AWS_REGION', 'us-east-1')  # Default region if not specified
)

# Define your queue URL (replace 'YOUR_QUEUE_URL' with your actual SQS queue URL)
queue_url = config('AWS_SQS_START_QUEUE_URL')

# Define the message payload
interview_schedule = {

    "id": 94,

    "active": 1,

    "createdDate": "2024-11-05T05:32:37.424+00:00",

    "deleted": 0,

    "interviewPeriodMinutes": 0,

    "lastUpdatedDate": "2024-11-05T05:32:37.424+00:00",

    "scheduleStartDate": "2024-11-06T02:00:00.000+00:00",

    "scheduleStatusId": 1,

    "updatedBy": 0,

    "resume": "null",

    "botJobCandidateQuestions": "null"

}
 
# Convert the dictionary to a JSON string
message_body = json.dumps({"interviewSchedule": interview_schedule})

try:
    # Send the message to the SQS queue
    response = sqs.send_message(
        QueueUrl=queue_url,
        MessageBody=message_body,
        MessageGroupId="aibot",
        MessageDeduplicationId=str(uuid.uuid4())  # Required for FIFO queues
    )
    print("Message sent successfully:", response['MessageId'])

except Exception as e:
    print("Error sending message:", e)
