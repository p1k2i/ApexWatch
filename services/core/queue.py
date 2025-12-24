"""
RabbitMQ Queue Manager
Handles event queuing and sequential processing
"""
import pika
import json
import logging
from typing import Dict, Any, Callable
from config import settings
import time

logger = logging.getLogger(__name__)


class QueueManager:
    """Manages RabbitMQ connection and event queuing"""

    def __init__(self):
        self.connection = None
        self.channel = None
        self.queue_name = settings.RABBITMQ_QUEUE

    def connect(self):
        """Establish connection to RabbitMQ"""
        try:
            credentials = pika.PlainCredentials(
                settings.RABBITMQ_USER,
                settings.RABBITMQ_PASSWORD
            )

            parameters = pika.ConnectionParameters(
                host=settings.RABBITMQ_HOST,
                port=settings.RABBITMQ_PORT,
                credentials=credentials,
                heartbeat=600,
                blocked_connection_timeout=300
            )

            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()

            # Declare queue with persistence
            self.channel.queue_declare(
                queue=self.queue_name,
                durable=True
            )

            logger.info(f"Connected to RabbitMQ, queue: {self.queue_name}")

        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise

    def publish_event(self, event: Dict[str, Any]):
        """
        Publish an event to the queue

        Args:
            event: Event dictionary with type and data
        """
        if not self.channel:
            self.connect()

        try:
            message = json.dumps(event)

            self.channel.basic_publish(
                exchange='',
                routing_key=self.queue_name,
                body=message,
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Make message persistent
                    content_type='application/json'
                )
            )

            logger.info(f"Published event: {event.get('type')}")

        except Exception as e:
            logger.error(f"Failed to publish event: {e}")
            # Try to reconnect and retry once
            try:
                self.connect()
                self.channel.basic_publish(
                    exchange='',
                    routing_key=self.queue_name,
                    body=message,
                    properties=pika.BasicProperties(
                        delivery_mode=2,
                        content_type='application/json'
                    )
                )
            except Exception as retry_error:
                logger.error(f"Retry failed: {retry_error}")
                raise

    def start_consuming(self, callback: Callable):
        """
        Start consuming events from the queue

        Args:
            callback: Function to call for each message
        """
        if not self.channel:
            self.connect()

        # Set QoS to process one message at a time (sequential processing)
        self.channel.basic_qos(prefetch_count=1)

        def message_handler(ch, method, properties, body):
            """Handle incoming messages"""
            try:
                event = json.loads(body)
                logger.info(f"Processing event: {event.get('type')}")

                # Call the callback function
                callback(event)

                # Acknowledge the message
                ch.basic_ack(delivery_tag=method.delivery_tag)

            except Exception as e:
                logger.error(f"Error processing message: {e}")
                # Reject and requeue the message
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
                time.sleep(5)  # Wait before reprocessing

        self.channel.basic_consume(
            queue=self.queue_name,
            on_message_callback=message_handler,
            auto_ack=False
        )

        logger.info("Started consuming events from queue")
        self.channel.start_consuming()

    def get_queue_size(self) -> int:
        """Get the current number of messages in the queue"""
        if not self.channel:
            self.connect()

        method = self.channel.queue_declare(
            queue=self.queue_name,
            durable=True,
            passive=True
        )

        return method.method.message_count

    def close(self):
        """Close the connection"""
        if self.connection and not self.connection.is_closed:
            self.connection.close()
            logger.info("RabbitMQ connection closed")


# Global queue manager instance
queue_manager = QueueManager()
