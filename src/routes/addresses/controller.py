from fastapi import APIRouter, status
from uuid import UUID

from src.models.db import DbSession
from src.auth.dependencies import CurrentUser
from . import models, service

router = APIRouter(prefix="/addresses", tags=["Addresses"])


@router.get("/", response_model=models.AddressListResponseWrapper)
def list_addresses(db: DbSession, current_user: CurrentUser):
    addresses = service.list_addresses(db, current_user.id)
    return models.AddressListResponseWrapper(
        success=True,
        message="Addresses retrieved successfully",
        data=addresses,
    )


@router.post("/", response_model=models.AddressResponseWrapper, status_code=status.HTTP_201_CREATED)
def create_address(body: models.AddressCreate, db: DbSession, current_user: CurrentUser):
    address = service.create_address(db, current_user.id, body)
    return models.AddressResponseWrapper(
        success=True,
        message="Address created successfully",
        data=address,
    )


@router.delete("/{address_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_address(address_id: UUID, db: DbSession, current_user: CurrentUser):
    service.delete_address(db, address_id, current_user.id)
