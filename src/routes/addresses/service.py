from uuid import UUID
from sqlalchemy.orm import Session
from fastapi import HTTPException
import logging

from src.models.address import Address
from src.models.order import Order
from . import models

logger = logging.getLogger(__name__)


def list_addresses(db: Session, user_id: UUID) -> list[Address]:
    return db.query(Address).filter(Address.user_id == user_id).order_by(Address.created_at.desc()).all()


def create_address(db: Session, user_id: UUID, data: models.AddressCreate) -> Address:
    try:
        if data.is_default:
            db.query(Address).filter(
                Address.user_id == user_id,
                Address.is_default == True,
            ).update({"is_default": False})

        address = Address(
            user_id=user_id,
            line1=data.line1,
            line2=data.line2,
            city=data.city,
            state=data.state,
            postal_code=data.postal_code,
            country=data.country,
            label=data.label,
            is_default=data.is_default,
        )
        db.add(address)
        db.commit()
        db.refresh(address)
        logger.info(f"Created address {address.id} for user {user_id}")
        return address
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create address for user {user_id}. Error: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create address")


def delete_address(db: Session, address_id: UUID, user_id: UUID) -> None:
    address = db.query(Address).filter(
        Address.id == address_id,
        Address.user_id == user_id,
    ).first()
    if not address:
        raise HTTPException(status_code=404, detail="Address not found")

    referenced = db.query(Order).filter(
        (Order.shipping_address_id == address_id) | (Order.billing_address_id == address_id)
    ).first()
    if referenced:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete an address that is referenced by an order",
        )

    db.delete(address)
    db.commit()
    logger.info(f"Deleted address {address_id}")
