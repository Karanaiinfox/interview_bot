import threading
import logging
import boto3
import time
import json
from django.apps import AppConfig
from decouple import config

logger = logging.getLogger(__name__)

class AppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'questions'

    def ready(self):
        logger.info("Starting SQS polling thread...")
        sqs_thread = threading.Thread(target=self.start_sqs_polling)
        sqs_thread.daemon = True
        sqs_thread.start()

    def start_sqs_polling(self):
        sqs = boto3.client(
            'sqs',
            aws_access_key_id=config('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=config('AWS_SECRET_ACCESS_KEY'),
            region_name=config('AWS_REGION', 'us-east-1')
        )
        queue_url = config('AWS_SQS_START_QUEUE_URL')
        processed_ids = set()  

        while True:
            try:
                response = sqs.receive_message(
                    QueueUrl=queue_url,
                    MaxNumberOfMessages=10,  
                    WaitTimeSeconds=10
                )

                if 'Messages' in response:
                    for message in response['Messages']:
                        message_body = message['Body']
                        receipt_handle = message['ReceiptHandle']
                        
                        logger.info(f"Received message: {message_body}")

                        try:
                            message_data = json.loads(message_body)
                            schedule_id = message_data.get('id')
                            # schedule_id = message_data.get('interviewSchedule', {}).get('id')
                            # Deduplication check
                            if schedule_id in processed_ids:
                                logger.info(f"Duplicate message with id {schedule_id} skipped.")
                                sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt_handle)
                                continue
                            processed_ids.add(schedule_id)
                            logger.info("Processing schedule_id: %s", schedule_id)


                        except json.JSONDecodeError as e:
                            logger.error(f"Failed to decode message body: {message_body}")
                            logger.exception("JSONDecodeError: %s", str(e))
                            sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt_handle)
                            logger.info("Invalid message deleted from SQS.")
                            continue

                        if schedule_id:
                            from .views import QuestionsView
                            result = QuestionsView().generate_questions_helper(schedule_id)
                            logger.info(f"Questions generation result for schedule_id {schedule_id}: {result}")
                            
                            # Delete message after processing
                            sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt_handle)
                            logger.info("Message deleted from SQS.")

                else:
                    logger.info("No messages to process. Waiting for new messages...")

            except Exception as e:
                logger.exception("Error receiving message from SQS: %s", str(e))
            
            time.sleep(2)
