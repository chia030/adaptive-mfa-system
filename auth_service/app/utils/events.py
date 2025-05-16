from shared_lib.schemas.events import LoginAttempted
from shared_lib.infrastructure.broker import RabbitBroker

def publish_login_event(data: LoginAttempted):

    data = {**data.model_dump(), "timestamp": data.timestamp.isoformat()}
    body = data.model_dump_json() # I learned a new thing hehe
    
    # body = json.dumps({
    #     "event_id": data.event_id, 
    #     "user_id": data.user_id, 
    #     "email":data.email, 
    #     "ip_address":data.ip_address, 
    #     "user_agent":data.user_agent, 
    #     "country":data.country, 
    #     "region":data.region, 
    #     "city":data.city, 
    #     "timestamp":data.timestamp.isoformat(), 
    #     "success":data.was_successful}) # why is this "success" and not "was_successful"?

    RabbitBroker.publish(exchange="auth_events", routing_key="login.attempted", body=body)
