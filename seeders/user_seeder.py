from seeders.base_seeder import BaseSeeder
from src.models.user import User
from src.models.cart import Cart
from src.models.user_role import UserRole
from src.models.role import Role
from pwdlib import PasswordHash
import logging

logger = logging.getLogger(__name__)


class UserSeeder(BaseSeeder):
    """Seed test users with known permissions."""
    
    def __init__(self, db):
        super().__init__(db)
        self.pwd_context = PasswordHash.recommended()
    
    def seed(self):
        """Create or update test users with known passwords and assign super_admin role."""
        
        # Test user 1 - Admin user
        test_email = "amaanmalik0360@gmail.com"
        test_password = "Test@123456"
        
        user = self.db.query(User).filter(User.email == test_email).first()
        
        if user:
            # Update existing user's password
            hashed_password = self.pwd_context.hash(test_password)
            user.password = hashed_password
            user.name = user.name or "Amaan Malik"
            logger.info(f"Updated password for existing user: {test_email}")
        else:
            # Create new user
            hashed_password = self.pwd_context.hash(test_password)
            user = User(
                email=test_email,
                password=hashed_password,
                name="Amaan Malik",
                is_guest=False
            )
            self.db.add(user)
            self.db.flush()
            
            # Create cart for the user
            cart = Cart(user_id=user.id)
            self.db.add(cart)
            logger.info(f"Created new user: {test_email}")
        
        # Assign super_admin role (role_id=1 from migration)
        super_admin_role = self.db.query(Role).filter(Role.name == "super_admin").first()
        if super_admin_role:
            existing_role = self.db.query(UserRole).filter(
                UserRole.user_id == user.id,
                UserRole.role_id == super_admin_role.id
            ).first()
            
            if not existing_role:
                user_role = UserRole(user_id=user.id, role_id=super_admin_role.id)
                self.db.add(user_role)
                logger.info(f"Assigned super_admin role to user: {test_email}")
            else:
                logger.info(f"User already has super_admin role: {test_email}")
        else:
            logger.warning("super_admin role not found in database")
        
        self.db.commit()
        logger.info(f"User seeder completed. Email: {test_email}, Password: {test_password}")
