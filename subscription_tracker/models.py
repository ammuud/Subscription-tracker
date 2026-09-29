from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Subscription(db.Model):
    __tablename__ = "subscriptions"

    id = db.Column(db.Integer, primary_key=True)
    user_email = db.Column(db.String(255), nullable=False, index=True)

    service_name = db.Column(db.String(120), nullable=False)
    status = db.Column(db.String(30), default="active")  # active / expired / unknown
    payment_amount = db.Column(db.String(50))
    currency = db.Column(db.String(10))
    renewal_date = db.Column(db.String(50))
    category = db.Column(db.String(50))  # entertainment / cloud / education / other

    source_email_subject = db.Column(db.String(255))
    source_email_from = db.Column(db.String(255))
    source_email_date = db.Column(db.String(50))
    source_email_id = db.Column(db.String(120))  # Gmail message id, for dedup

    detection_method = db.Column(db.String(30), default="keyword")  # keyword / ai
    confidence = db.Column(db.Float, default=1.0)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "service_name": self.service_name,
            "status": self.status,
            "payment_amount": self.payment_amount,
            "currency": self.currency,
            "renewal_date": self.renewal_date,
            "category": self.category,
            "source_email_subject": self.source_email_subject,
            "source_email_from": self.source_email_from,
            "source_email_date": self.source_email_date,
            "detection_method": self.detection_method,
            "confidence": self.confidence,
        }
