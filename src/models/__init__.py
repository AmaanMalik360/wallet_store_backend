# Import all models for easy access
from .db import Base, db_manager, get_db
from .user import User
from .category import Category
from .product import Product
from .attribute import Attribute, AttributeValue, ProductAttributeValue
from .category_attribute import CategoryAttribute
from .cart import Cart, CartItem
from .order import Order, OrderItem, OrderStatus
from .payment import Payment, PaymentStatus
from .shipment import Shipment

# Add missing relationships to User model
from sqlalchemy.orm import relationship

# Add relationships to User model
User.cart = relationship("Cart", back_populates="user", uselist=False)
User.orders = relationship("Order", back_populates="user")

# Add relationships to Category model
Category.products = relationship("Product", back_populates="category")

# Export all models
__all__ = [
    "Base",
    "db_manager", 
    "get_db",
    "User",
    "Category",
    "Product",
    "Attribute",
    "AttributeValue", 
    "ProductAttributeValue",
    "CategoryAttribute",
    "Cart",
    "CartItem",
    "Order",
    "OrderItem",
    "OrderStatus",
    "Payment",
    "PaymentStatus",
    "Shipment"
]