from django.core.mail import EmailMessage

class EmailService:
    def __init__(self, email, order):
        self.order_code = str(order.order_id)[:7]
        self.email = email
        
    def order_created(self):
        email_message = EmailMessage(
            subject = f"Your order #{self.order_code} has been created successfully!",
            body = f"Your order #{self.order_code} has been created. You'll be notified as soon as there are any updates.",
            to = [self.email]
        )
        email_message.send()

    def processing_order(self):
        email_message = EmailMessage(
            subject = f"Your order #{self.order_code} is being processed!",
            body = f"We'd like to inform you that your order #{self.order_code} is being processed. You'll be notified as soon as there are any updates.",
            to = [self.email]
        )
        email_message.send()

    def paid_order(self):
        email_message = EmailMessage(
            subject = f"The payment for your order #{self.order_code} has been approved!",
            body = f"We'd like to inform you that your payment has been approved! As soon as there are updates regarding your order #{self.order_code}, you'll be notified.",
            to = [self.email]
        )
        email_message.send()

    def order_shipped(self):
        email_message = EmailMessage(
            subject = f"Your order #{self.order_code} has been shipped!",
            body = f"We'd like to inform you that your order #{self.order_code} has been shipped. You'll receive further updates about your order.",
            to = [self.email]
        )
        email_message.send()

    def order_out_for_delivery(self):
        email_message = EmailMessage(
            subject = f"Your order #{self.order_code} has left for delivery!",
            body = f"We'd like to inform you that your order #{self.order_code} has left for delivery. It will arrive at your residence soon.",
            to = [self.email]
        )
        email_message.send()

    def order_delivered(self):
        email_message = EmailMessage(
            subject = f"Your order #{self.order_code} has been delivered successfully!",
            body = f"Your order #{self.order_code} has been delivered successfully. Thank you for trusting us. Enjoy your product!",
            to = [self.email]
        )
        email_message.send()
    
    def order_cancelled(self):
        email_message = EmailMessage(
            subject = f'Your order #{self.order_code} has been cancelled successfully!',
            body = f"We'd like to inform you that your order has been cancelled successfully. You'll be notified if any further action is required.",
            to = [self.email]
        )
        email_message.send()

    def refunded_order(self):
        email_message = EmailMessage(
            subject = f"Your order #{self.order_code} has been refunded successfully!",
            body = f"We'd like to inform you that your order #{self.order_code} has been refunded successfully.",
            to = [self.email    ]
        )
        email_message.send()
