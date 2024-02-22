from sqlalchemy.orm import relationship

from app import db
from flask_login import UserMixin
from datetime import datetime

# Association table for the many-to-many relationship
transfer_items = db.Table('transfer_items',
                          db.Column('transfer_id', db.Integer, db.ForeignKey('transfer.id'), primary_key=True),
                          db.Column('item_id', db.Integer, db.ForeignKey('item.id'), primary_key=True),
                          db.Column('quantity', db.Integer, nullable=False)
                          )


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(80), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    transfers = db.relationship('Transfer', backref='creator', lazy=True)
    active = db.Column(db.Boolean, default=False, nullable=False)


class Location(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)


class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    transfers = db.relationship('Transfer', secondary=transfer_items, backref=db.backref('items', lazy='dynamic'))


class Transfer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    from_location_id = db.Column(db.Integer, db.ForeignKey('location.id'), nullable=False)
    to_location_id = db.Column(db.Integer, db.ForeignKey('location.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    completed = db.Column(db.Boolean, default=False, nullable=False)

    # Define relationships to Location model
    from_location = relationship('Location', foreign_keys=[from_location_id])
    to_location = relationship('Location', foreign_keys=[to_location_id])
    transfer_items = db.relationship('TransferItem', backref='transfer', cascade='all, delete-orphan')


class TransferItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    transfer_id = db.Column(db.Integer, db.ForeignKey('transfer.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    item = relationship('Item', backref='transfer_items', lazy=True)