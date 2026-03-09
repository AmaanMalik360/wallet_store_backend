```markdown
# SQLAlchemy `mapped_column` vs `Column`

## Overview

In SQLAlchemy, `mapped_column` is the modern standard introduced in version 2.0 to replace the legacy use of `Column` within Declarative ORM models. While `Column` is still required for Core-level table definitions, `mapped_column` is now the preferred way to map database columns to class attributes.

## Key Differences

| Feature | `mapped_column` (New Standard) | `Column` (Legacy/Core) |
|---------|--------------------------------|------------------------|
| **Typing Support** | Specifically designed to work with Python's type annotations (`Mapped[str]`). | Does not natively support static analysis or type-checking tools. |
| **Nullability** | Can automatically derive `nullable` status from `Optional` annotations. | Requires explicit `nullable=True/False` arguments. |
| **Usage Context** | Valid only within Declarative ORM mappings. | Used in both ORM (legacy) and SQLAlchemy Core table objects. |
| **Dataclass Integration** | Supports modern Python Dataclass features like `init`, `default_factory`, and `repr`. | Lacks built-in integration with the modern `MappedAsDataclass` features. |

## Why Use `mapped_column`?

- **Static Analysis**: It enables IDEs and tools like MyPy to provide better autocompletion and error checking for your models.
- **Reduced Redundancy**: By using `Mapped[int] = mapped_column()`, you often don't need to specify the SQLAlchemy type (`Integer`) because it's inferred from the Python type.
- **Modern API**: It aligns with the "Unified Tutorial" style of SQLAlchemy 2.0, making your code future-proof.

## Examples

### New Standard (v2.0+)

```python
from typing import Optional
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "user"
    
    # Type and NOT NULL inferred from Mapped[int]
    id: Mapped[int] = mapped_column(primary_key=True)
    
    # Type and NULL inferred from Mapped[Optional[str]]
    name: Mapped[Optional[str]] = mapped_column()
```

### Legacy Style

```python
from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = "user"
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=True)
```

## Considerations

Are you migrating an existing project to SQLAlchemy 2.0, or starting a new one from scratch?
```