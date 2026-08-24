# Import all models for easy access
from .db import Base, db_manager, get_db
from .user import User
from .category import Category
from .currency import Currency
from .product import Product
from .product_price import ProductPrice
from .attribute import Attribute, AttributeValue, ProductAttributeValue
from .category_attribute import CategoryAttribute
from .cart import Cart, CartItem
from .address import Address
from .order import Order, OrderItem, OrderStatus
from .payment import Payment, PaymentStatus
from .shipment import Shipment
from .role import Role, RolePermission
from .permission import Permission
from .user_role import UserRole

# Add missing relationships to User model
from sqlalchemy.orm import relationship

# Add relationships to User model
User.cart = relationship("Cart", back_populates="user", uselist=False)
User.orders = relationship("Order", back_populates="user")
User.addresses = relationship("Address", back_populates="user", cascade="all, delete-orphan")
User.user_roles = relationship("UserRole", back_populates="user", cascade="all, delete-orphan")

# Add relationships to Category model
Category.products = relationship("Product", back_populates="category")

# Export all models
__all__ = [
    "Base",
    "db_manager", 
    "get_db",
    "User",
    "Category",
    "Currency",
    "Product",
    "ProductPrice",
    "Attribute",
    "AttributeValue", 
    "ProductAttributeValue",
    "CategoryAttribute",
    "Cart",
    "CartItem",
    "Order",
    "OrderItem",
    "OrderStatus",
    "Address",
    "Payment",
    "PaymentStatus",
    "Shipment",
    "Role",
    "RolePermission",
    "Permission",
    "UserRole",
]