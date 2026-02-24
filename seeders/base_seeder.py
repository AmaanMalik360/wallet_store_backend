from sqlalchemy.orm import Session

class BaseSeeder:
    """Base class for all seeders"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def seed(self):
        """Override this method in child classes"""
        raise NotImplementedError(f"seed() method not implemented in {self.__class__.__name__}")
    
    def clear(self):
        """Optional: Override to clear data before seeding"""
        pass
    
    @classmethod
    def get_name(cls):
        """Get seeder name from class name"""
        return cls.__name__.replace('Seeder', '').lower()