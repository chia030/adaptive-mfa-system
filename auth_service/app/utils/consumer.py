# from shared_lib.infrastructure.broker import RabbitBroker
# from shared_lib.schemas.events import MFACompleted
# from shared_lib.utils.security import create_access_token
# from app.core.auth_logic import get_user_by_email

# callback
# def on_mfa_completed(chan, method, props, body):
#     try:
#         # parse incoming evt
#         evt = MFACompleted.model_validate_json(body)
#         #  if MFA success, issue JWT
#         if evt.was_successful:
#             user = get_user_by_email(evt.email)
#             token = create_access_token(subject=user.id)
#             # notify o.g. requester ("TokenIssued" event or similar)
#             print(f"Issued token for {evt.email}: {token}")
        
#         # acknowledge the message
#         chan.basic_ack(delivery_tag=method.delivery_tag)
#     except Exception as e:
#         # log error and optionally reject/nack
#         print(f"Error processing MFACompleted: {e}")
#         chan.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

# def start_mfa_consumer():
#     # init consumer to listen for MFACompleted events
#     RabbitBroker.consume(
#         exchange='mfa_events',
#         routing_key='mfa.completed',
#         queue=None, # rabbitMQ generates a unique, exclusive queue
#         on_message=on_mfa_completed,
#         durable=True,
#         auto_ack=False, # manual ack to handle failures
#         prefetch_count=1
#     )
