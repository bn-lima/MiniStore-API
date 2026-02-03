def get_webhook_headers(request): 
    try:
        x_request_id = request.headers['x-request-id']
    except KeyError:
        x_request_id = None

    try:
        signature_header = request.headers['x-signature']
    except KeyError:
        signature_header = None

    return x_request_id, signature_header