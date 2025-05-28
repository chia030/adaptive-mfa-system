# === RabbitMQ client wrapper ===
import pika
import threading
from typing import Callable, Optional

import pika.channel
import pika.spec
from shared_lib.config.settings import settings
from pika import BasicProperties

# singleton wrapper around a pika BlockingConnection
class RabbitBroker:
    _lock = threading.Lock()
    _connection = None

    

    @classmethod
    def get_connection(cls):
        if cls._connection is None:
            with cls._lock:
                if cls._connection is None:
                    # settings.rabbitmq_url includes credentials and host:port
                    params = pika.URLParameters(settings.rabbitmq_url)
                    cls._connection = pika.BlockingConnection(params)
        return cls._connection
    
    @classmethod
    def publish(cls, exchange: str, routing_key: str, body: bytes, durable: bool = True):
        props = BasicProperties(content_type="application/json", content_encoding="utf-8")
        # conn = cls.get_connection()
        # new connection for publishing to avoid conflicts
        params = pika.URLParameters(settings.rabbitmq_url)
        conn = pika.BlockingConnection(params)
        chan = conn.channel()
        chan.exchange_declare(exchange=exchange, exchange_type='topic', durable=durable)
        chan.basic_publish(exchange, routing_key, body, properties=props)

    @classmethod
    def consume(
        cls,
        exchange: str,
        routing_key: str,
        queue: Optional[str],
        on_message: Callable[[pika.channel.Channel, pika.spec.Basic.Deliver, pika.spec.BasicProperties, bytes], None],
        durable: bool = True,
        auto_ack: bool = True,
        prefetch_count: int = 1
    ) -> None:
        conn = cls.get_connection()
        chan = conn.channel()
        chan.exchange_declare(exchange=exchange, exchange_type='topic', durable=durable)
        # declare or reuse a queue
        result = chan.queue_declare(queue=queue or "", durable=durable)
        queue_name = result.method.queue
        
        chan.queue_bind(exchange=exchange, queue=queue_name, routing_key=routing_key)
        # QoS / prefetch
        chan.basic_qos(prefetch_count=prefetch_count)
        # register consumer callback
        chan.basic_consume(
            queue=queue_name,
            on_message_callback=on_message,
            auto_ack=auto_ack,
        )
        print(f"[consumer] Will listen on queue: {queue_name!r}")
        # enter consuming loop
        chan.start_consuming()

    @classmethod
    def stop(cls):
        conn = cls.get_connection()
        chan = conn.channel()
        chan.stop_consuming()
        chan.close()
